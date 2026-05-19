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
function showResult({ agg, sales, pay, journal }) {
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

  // Closeout strip
  document.getElementById("result-closeout").innerHTML = co.balanced
    ? `<div class="result success">All vouchers balance. Sundry Debtors closes to ₹0 per invoice after both XMLs import.</div>`
    : `<div class="result error">Sundry Debtors does NOT close. Net = ${fmtINR(co.net || 0)} — investigate before importing.</div>`;

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
