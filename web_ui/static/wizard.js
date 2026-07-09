"use strict";

const state = { uploadPath: null, month: null, runId: null };

const fmtINR = n => "₹" + Number(n||0).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
const fmtInt = n => Number(n||0).toLocaleString("en-IN");
const fmtBytes = b => b < 1024 ? b + " B" : b < 1024*1024 ? (b/1024).toFixed(1) + " KB" : (b/1024/1024).toFixed(1) + " MB";

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }
function setResult(elId, ok, text) {
  const el = document.getElementById(elId);
  el.className = "result " + (ok ? "success" : "error");
  el.textContent = text;
}
function runFileUrl(name) { return `/api/runs/${state.month}/${state.runId}/file/${encodeURIComponent(name)}`; }

// ---- A. Upload ----
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fi = document.getElementById("file-input");
  if (!fi.files.length) return;
  const fd = new FormData(); fd.append("file", fi.files[0]);
  setResult("upload-result", true, "Uploading & parsing…");
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok) { setResult("upload-result", false, j.error || "upload failed"); return; }
    state.uploadPath = j.upload_path;
    setResult("upload-result", true, `Uploaded · ${fmtInt(j.rows)} rows · ${j.months.length} month(s)`);
    renderMonths(j.months);
  } catch (err) { setResult("upload-result", false, err.message); }
});

function renderMonths(months) {
  const tbody = document.querySelector("#month-table tbody");
  tbody.innerHTML = "";
  months.forEach(m => {
    const tr = document.createElement("tr");
    tr.className = "selectable";
    tr.innerHTML = `
      <td><input type="radio" name="mo" value="${m.month}"></td>
      <td>${m.month}</td><td class="num">${fmtInt(m.invoices)}</td>
      <td class="num">${fmtInt(m.rows)}</td><td class="num">${fmtINR(m.gross)}</td>`;
    tr.addEventListener("click", () => {
      tr.querySelector("input").checked = true;
      document.querySelectorAll("#month-table tr.selected").forEach(x => x.classList.remove("selected"));
      tr.classList.add("selected");
      state.month = m.month;
      show("sec-process");
      window.scrollTo({ top: document.getElementById("sec-process").offsetTop - 20, behavior: "smooth" });
    });
    tbody.appendChild(tr);
  });
  show("month-picker");
}

// ---- B. Process (single button drives all) ----
const progressTpl = [
  { id: "p-start",   label: "Start run folder" },
  { id: "p-agg",     label: "Aggregate invoices" },
  { id: "p-sales",   label: "Render Sales XML" },
  { id: "p-pay",     label: "Extract payments" },
  { id: "p-journal", label: "Render Journal XML" },
  { id: "p-combo",   label: "Combined XML + bundle.zip" },
];

function renderProgress() {
  const ol = document.getElementById("progress");
  ol.innerHTML = progressTpl.map(s => `<li id="${s.id}" class="pending">${s.label}</li>`).join("");
}
function setProgress(id, status, note) {
  const li = document.getElementById(id);
  li.className = status;
  if (note) li.innerHTML = li.firstChild.textContent + ` <span class="muted">— ${note}</span>`;
}

document.getElementById("run-process").addEventListener("click", async () => {
  const btn = document.getElementById("run-process");
  btn.disabled = true; btn.textContent = "Processing…";
  renderProgress();
  const salesBase = parseInt(document.getElementById("sales-alter-id").value, 10) || 70000;
  const journalBase = parseInt(document.getElementById("journal-alter-id").value, 10) || 80000;

  try {
    // 1. Start run
    setProgress("p-start", "active");
    let r = await fetch("/api/start-run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_path: state.uploadPath, month: state.month }),
    });
    let j = await r.json();
    if (!r.ok) throw new Error(j.error);
    state.runId = j.run_id;
    setProgress("p-start", "done", state.runId);

    // 2. Aggregate
    setProgress("p-agg", "active");
    r = await fetch("/api/aggregate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId }) });
    const agg = await r.json();
    if (!r.ok) throw new Error(agg.error);
    setProgress("p-agg", "done", `${fmtInt(agg.invoice_count)} invoices · ${fmtINR(agg.total_payable || agg.gross_total)} payable`);

    // 3. Sales
    setProgress("p-sales", "active");
    r = await fetch("/api/generate-sales", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId, alter_id_base: salesBase }) });
    const sales = await r.json();
    if (!r.ok) throw new Error(sales.error);
    setProgress("p-sales", "done", `${fmtInt(sales.voucher_count)} vouchers`);

    // 4. Payments
    setProgress("p-pay", "active");
    r = await fetch("/api/extract-payments", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId }) });
    const pay = await r.json();
    if (!r.ok) throw new Error(pay.error);
    setProgress("p-pay", "done", `${fmtInt(pay.payment_rows)} rows · ${fmtINR(pay.settlement_total)}`);

    // 5. Journal (auto-generates combined)
    setProgress("p-journal", "active");
    r = await fetch("/api/generate-journal", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId, alter_id_base: journalBase }) });
    const journal = await r.json();
    if (!r.ok) throw new Error(journal.error);
    setProgress("p-journal", "done", `${fmtInt(journal.voucher_count)} vouchers`);
    setProgress("p-combo", "done", journal.combined_xml ? "combined.xml ready" : "combined skipped");

    showResult({ agg, sales, pay, journal });
    btn.disabled = false; btn.textContent = "Re-process";
  } catch (err) {
    const active = document.querySelector("#progress li.active");
    if (active) setProgress(active.id, "fail", err.message);
    btn.disabled = false; btn.textContent = "Retry";
    alert("Failed: " + err.message);
  }
});

// ---- C. Result ----
let lastResult = null;
function showResult(ctx) {
  const { agg, sales, pay, journal } = ctx;
  lastResult = ctx;
  show("sec-result");

  // Summary tiles
  const co = journal.closeout || {};
  const okClass = co.balanced ? "var(--good)" : "var(--bad)";
  document.getElementById("result-summary").innerHTML = `
    <div class="kv"><span class="k">Month</span><span class="v">${state.month}</span></div>
    <div class="kv"><span class="k">Run</span><span class="v" style="font-size:12px">${state.runId}</span></div>
    <div class="kv"><span class="k">Sales vouchers</span><span class="v">${fmtInt(sales.voucher_count)}</span></div>
    <div class="kv"><span class="k">Journal vouchers</span><span class="v">${fmtInt(journal.voucher_count)}</span></div>
    <div class="kv"><span class="k">Gross billed</span><span class="v">${fmtINR(agg.gross_total)}</span></div>
    <div class="kv"><span class="k">Total Payable</span><span class="v">${fmtINR(agg.total_payable || 0)}</span></div>
    <div class="kv"><span class="k">Settlement</span><span class="v">${fmtINR(pay.settlement_total)}</span></div>
    <div class="kv"><span class="k">Round Off (net)</span><span class="v">${fmtINR((sales.round_off || 0) + (journal.round_off || 0))}</span></div>
    <div class="kv"><span class="k">Sundry Debtors net</span><span class="v" style="color:${okClass}">${fmtINR(co.net || 0)} ${co.balanced ? '✓' : '✗'}</span></div>
  `;

  // Closeout strip (+ self-service ledger mapping when it doesn't close)
  renderCloseout(journal);

  // Downloads
  const dl = document.getElementById("downloads");
  dl.innerHTML = "";
  if (journal.combined_xml) addBtn(dl, "★ Combined XML (gz, 3-4 MB)", runFileUrl("combined.xml.gz"), true);
  addBtn(dl, "Sales XML (gz)", runFileUrl("sales.xml.gz"));
  addBtn(dl, "Journal XML (gz)", runFileUrl("journal.xml.gz"));
  addBtn(dl, "Bundle (zip)", runFileUrl("bundle.zip"));
  addBtn(dl, "Invoice CSV", runFileUrl("invoice.csv"));
  addBtn(dl, "Payment CSV", runFileUrl("payment.csv"));

  // Detail panels
  document.getElementById("d-agg").innerHTML = renderBySource(agg.by_source) + previewTable(agg.columns, agg.preview);
  document.getElementById("d-sales").innerHTML = renderLedger(sales.breakdown);
  document.getElementById("d-pay").innerHTML = renderByMode(pay.by_mode) + previewTable(pay.columns, pay.preview);
  document.getElementById("d-journal").innerHTML = renderLedger(journal.breakdown);

  window.scrollTo({ top: document.getElementById("sec-result").offsetTop - 20, behavior: "smooth" });
}

// Close-out strip + self-service mapping when Sundry Debtors doesn't close
function renderCloseout(journal) {
  const co = journal.closeout || {};
  const el = document.getElementById("result-closeout");
  const mr = co.manual_review || [];

  // Manual-review sheet (reversal/refund invoices — excluded from import, enter in Tally)
  let reviewHtml = "";
  if (mr.length) {
    reviewHtml = `<div class="unmapped-box"><p><b>${mr.length} invoice(s) need manual entry in Tally</b> — they have a reversal/refund and are <b>excluded</b> from the import XML (the rest imports clean). Enter these by hand:</p>
      <table class="data" style="max-width:100%"><thead><tr><th>Invoice</th><th class="num">Billed</th><th class="num">Net paid</th><th>Suggested treatment</th></tr></thead><tbody>`;
    mr.forEach(r => {
      reviewHtml += `<tr><td><b>${r.invoice}</b></td><td class="num">${fmtINR(r.billed)}</td><td class="num">${fmtINR(r.net)}</td><td style="font-size:12px">${r.treatment}</td></tr>`;
    });
    reviewHtml += `</tbody></table></div>`;
  }

  if (co.balanced) {
    el.innerHTML = `<div class="result success">All vouchers balance. Sundry Debtors closes to ₹0 per invoice after import.</div>` + reviewHtml;
    return;
  }
  const um = co.unmapped_modes || [];
  let html = `<div class="result error">Sundry Debtors does NOT close. Net = ${fmtINR(co.net || 0)} — investigate before importing.</div>`;
  if (um.length) {
    html += `<div class="unmapped-box">
      <p><b>${um.length} payment mode(s) have no Tally ledger</b>, so no Journal settles them — that is the ₹${fmtINR(co.net||0).replace('₹','')} gap. Map each to its exact Tally ledger (it must already exist in the company master), then re-run:</p>
      <table class="data" style="max-width:720px"><thead><tr><th>Mode</th><th class="num">Count</th><th class="num">Amount</th><th>Map to Tally ledger</th><th></th></tr></thead><tbody>`;
    um.forEach(u => {
      html += `<tr class="um-row" data-mode="${escAttr(u.mode)}">
        <td><b>${u.mode}</b></td><td class="num">${u.count}</td><td class="num">${fmtINR(u.amount)}</td>
        <td><input type="text" class="um-ledger" placeholder="e.g. CLEAR TRIP SDR" style="width:210px">
            <label class="um-nr" title="bill-wise: opens a New Ref receivable (like AGODA SDR)"><input type="checkbox" class="um-newref" checked> bill-wise</label></td>
        <td><button type="button" class="um-add">Add</button></td></tr>`;
    });
    html += `</tbody></table>
      <div class="actions" style="margin-top:8px"><button type="button" id="um-rerun" disabled>↻ Re-run Journal</button>
      <span id="um-status" class="muted"></span></div></div>`;
  }
  el.innerHTML = html + reviewHtml;
  el.querySelectorAll(".um-add").forEach(b => b.addEventListener("click", onAddMapping));
  const rr = document.getElementById("um-rerun");
  if (rr) rr.addEventListener("click", rerunJournal);
}

async function onAddMapping(e) {
  const row = e.target.closest(".um-row");
  const mode = row.dataset.mode;
  const ledger = row.querySelector(".um-ledger").value.trim();
  const newRef = row.querySelector(".um-newref").checked;
  if (!ledger) { alert("Enter the exact Tally ledger name"); return; }
  e.target.disabled = true; e.target.textContent = "…";
  try {
    const r = await fetch("/api/payment-ledger-map", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, ledger, new_ref: newRef }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "failed");
    e.target.textContent = "✓ mapped"; row.style.opacity = ".55";
    row.querySelector(".um-ledger").disabled = true;
    document.getElementById("um-rerun").disabled = false;
    document.getElementById("um-status").textContent = `mapped ${d.key} → ${ledger}. Add the rest, then re-run.`;
  } catch (err) { alert("Failed: " + err.message); e.target.disabled = false; e.target.textContent = "Add"; }
}

async function rerunJournal() {
  const st = document.getElementById("um-status");
  const btn = document.getElementById("um-rerun");
  btn.disabled = true; st.textContent = "re-generating Journal with the new mapping(s)…";
  const base = parseInt(document.getElementById("journal-alter-id").value) || 80000;
  try {
    const r = await fetch("/api/generate-journal", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId, alter_id_base: base }) });
    const journal = await r.json();
    if (!r.ok) throw new Error(journal.error);
    lastResult.journal = journal;
    showResult(lastResult);   // re-renders; closes cleanly if all modes now mapped
  } catch (err) { st.textContent = "❌ " + err.message; btn.disabled = false; }
}

function escAttr(s) { return String(s).replace(/"/g, "&quot;"); }

function addBtn(parent, label, href, primary=false) {
  const a = document.createElement("a");
  a.className = "btn-link" + (primary ? " active" : "");
  a.target = "_blank"; a.href = href; a.textContent = label;
  if (primary) a.style.fontWeight = "600";
  parent.appendChild(a);
}

function renderBySource(rows) {
  let html = `<h4>By Business Source</h4>
    <table class="data" style="max-width:600px"><thead><tr><th>Source</th><th class="num">Count</th><th class="num">Gross (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => html += `<tr><td>${r.business_source}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.gross)}</td></tr>`);
  const tc = rows.reduce((a,r)=>a+r.count,0), ta = rows.reduce((a,r)=>a+r.gross,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(ta)}</td></tr></tbody></table>`;
  return html;
}

function renderByMode(rows) {
  let html = `<h4>By Mode</h4>
    <table class="data" style="max-width:600px"><thead><tr><th>Mode</th><th class="num">Count</th><th class="num">Amount (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => html += `<tr><td>${r.mode}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.amount)}</td></tr>`);
  const tc = rows.reduce((a,r)=>a+r.count,0), ta = rows.reduce((a,r)=>a+r.amount,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(ta)}</td></tr></tbody></table>`;
  return html;
}

function renderLedger(rows) {
  if (!rows) return "";
  let html = `<table class="data" style="max-width:600px"><thead><tr><th>Ledger</th><th class="num">Count</th><th class="num">Amount (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => html += `<tr><td>${r.ledger}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.amount)}</td></tr>`);
  const tc = rows.reduce((a,r)=>a+r.count,0), ta = rows.reduce((a,r)=>a+r.amount,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(ta)}</td></tr></tbody></table>`;
  return html;
}

function previewTable(cols, rows) {
  let html = `<h4>Preview (first 25 rows)</h4><div class="tablewrap"><table class="data">`;
  html += "<thead><tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
  rows.forEach(r => {
    html += "<tr>" + cols.map(c => {
      const v = r[c] ?? "";
      const isNum = typeof v === "number";
      return `<td class="${isNum ? "num" : ""}">${isNum ? v.toLocaleString("en-IN") : v}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody></table></div>";
  return html;
}
