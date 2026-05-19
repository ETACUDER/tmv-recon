"use strict";

const state = {
  uploadPath: null,
  month: null,
  runId: null,
};

const fmtINR = n => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
const fmtInt = n => Number(n).toLocaleString("en-IN");
const fmtBytes = b => b < 1024 ? b + " B" : b < 1024*1024 ? (b/1024).toFixed(1) + " KB" : (b/1024/1024).toFixed(1) + " MB";

function showStep(n) {
  for (let i = 1; i <= 5; i++) {
    document.getElementById(`step-${i}`).classList.toggle("active", i === n);
    document.getElementById(`step-tab-${i}`).classList.toggle("active", i === n);
    if (i < n) document.getElementById(`step-tab-${i}`).classList.add("done");
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setResult(elId, ok, text) {
  const el = document.getElementById(elId);
  el.className = "result " + (ok ? "success" : "error");
  el.textContent = text;
}

function runFileUrl(name) {
  return `/api/runs/${state.month}/${state.runId}/file/${encodeURIComponent(name)}`;
}

// ---- STEP 1: Upload ----
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fi = document.getElementById("file-input");
  if (!fi.files.length) return;
  const fd = new FormData();
  fd.append("file", fi.files[0]);
  setResult("upload-result", true, "Uploading & parsing…");
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok) { setResult("upload-result", false, j.error || "upload failed"); return; }
    state.uploadPath = j.upload_path;
    setResult("upload-result", true, `Uploaded · ${fmtInt(j.rows)} rows · ${j.months.length} month(s) detected`);
    renderMonths(j.months);
  } catch (err) {
    setResult("upload-result", false, err.message);
  }
});

function renderMonths(months) {
  const tbody = document.querySelector("#month-table tbody");
  tbody.innerHTML = "";
  months.forEach(m => {
    const tr = document.createElement("tr");
    tr.className = "selectable";
    tr.innerHTML = `
      <td><input type="radio" name="mo" value="${m.month}"></td>
      <td>${m.month}</td>
      <td class="num">${fmtInt(m.invoices)}</td>
      <td class="num">${fmtInt(m.rows)}</td>
      <td class="num">${fmtINR(m.gross)}</td>
    `;
    tr.addEventListener("click", () => {
      tr.querySelector("input").checked = true;
      document.querySelectorAll("#month-table tr.selected").forEach(x => x.classList.remove("selected"));
      tr.classList.add("selected");
      state.month = m.month;
      document.getElementById("next-1").disabled = false;
    });
    tbody.appendChild(tr);
  });
  document.getElementById("month-picker").classList.remove("hidden");
}

document.getElementById("next-1").addEventListener("click", async () => {
  if (!state.month) return;
  const btn = document.getElementById("next-1");
  btn.disabled = true; btn.textContent = "Starting run…";
  try {
    const r = await fetch("/api/start-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_path: state.uploadPath, month: state.month }),
    });
    const j = await r.json();
    if (!r.ok) {
      setResult("upload-result", false, j.error);
      btn.disabled = false; btn.textContent = "Next: Aggregate →"; return;
    }
    state.runId = j.run_id;
    showStep(2);
    btn.textContent = "Next: Aggregate →";
    await runAggregate();
  } catch (err) {
    setResult("upload-result", false, err.message);
    btn.disabled = false; btn.textContent = "Next: Aggregate →";
  }
});

// ---- STEP 2: Aggregate ----
async function runAggregate() {
  const sum = document.getElementById("agg-summary");
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/aggregate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      return;
    }
    sum.innerHTML = `
      <div class="kv"><span class="k">Run</span><span class="v" style="font-size:12px">${state.runId}</span></div>
      <div class="kv"><span class="k">Month</span><span class="v">${state.month}</span></div>
      <div class="kv"><span class="k">Invoices</span><span class="v">${fmtInt(j.invoice_count)}</span></div>
      <div class="kv"><span class="k">Sum Gross</span><span class="v">${fmtINR(j.gross_total)}</span></div>
      <div class="kv"><span class="k">Total Payable</span><span class="v">${fmtINR(j.total_payable || 0)}</span></div>
    `;
    renderBySource(j.by_source);
    renderCanonPreview(j.columns, j.preview);
    const dl = document.getElementById("download-csv");
    dl.href = runFileUrl("invoice.csv");
    dl.classList.remove("hidden");
    dl.textContent = "Download invoice.csv";
    document.getElementById("next-2").disabled = false;
  } catch (err) {
    sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${err.message}</span></div>`;
  }
}

function renderBySource(rows) {
  const wrap = document.getElementById("agg-by-source");
  let html = `<h3>By Business Source</h3>
    <table class="data" style="max-width:600px"><thead><tr>
      <th>Business Source</th><th class="num">Count</th><th class="num">Sum Gross (₹)</th>
    </tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.business_source}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.gross)}</td></tr>`;
  });
  const total = rows.reduce((a, r) => a + r.gross, 0);
  const totalC = rows.reduce((a, r) => a + r.count, 0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(totalC)}</td><td class="num">${fmtINR(total)}</td></tr></tbody></table>`;
  wrap.innerHTML = html;
}

function renderCanonPreview(cols, rows) {
  const t = document.getElementById("canon-preview");
  let html = "<thead><tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
  rows.forEach(r => {
    html += "<tr>" + cols.map(c => {
      const v = r[c] ?? "";
      const isNum = typeof v === "number";
      return `<td class="${isNum ? "num" : ""}">${isNum ? v.toLocaleString("en-IN") : v}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody>";
  t.innerHTML = html;
}

document.getElementById("next-2").addEventListener("click", () => showStep(3));

// ---- STEP 3: Generate Sales ----
document.getElementById("run-sales").addEventListener("click", async () => {
  const btn = document.getElementById("run-sales");
  const sum = document.getElementById("sales-summary");
  btn.disabled = true; btn.textContent = "Generating…";
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/generate-sales", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        month: state.month, run_id: state.runId,
        alter_id_base: parseInt(document.getElementById("sales-alter-id").value, 10) || 70000,
      }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      btn.disabled = false; btn.textContent = "Generate Sales XML"; return;
    }
    sum.innerHTML = `
      <div class="kv"><span class="k">Vouchers</span><span class="v">${fmtInt(j.voucher_count)}</span></div>
      <div class="kv"><span class="k">Dr Sundry Debtors</span><span class="v">${fmtINR(j.total)}</span></div>
      <div class="kv"><span class="k">Round Off (Dr)</span><span class="v">${fmtINR(j.round_off || 0)}</span></div>
    `;
    renderLedgerBreakdown("sales-breakdown", "sales-bd-h", j.breakdown);
    const dl = document.getElementById("download-sales-xml");
    dl.href = runFileUrl("sales.xml.gz");
    dl.classList.remove("hidden");
    dl.textContent = "Download Sales XML (gz)";
    btn.disabled = false; btn.textContent = "Re-generate Sales XML";
    document.getElementById("next-3").disabled = false;
  } catch (err) {
    sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${err.message}</span></div>`;
    btn.disabled = false; btn.textContent = "Generate Sales XML";
  }
});

document.getElementById("next-3").addEventListener("click", () => showStep(4));

// ---- STEP 4: Extract Payments ----
document.getElementById("run-payments").addEventListener("click", async () => {
  const btn = document.getElementById("run-payments");
  const sum = document.getElementById("pay-summary");
  btn.disabled = true; btn.textContent = "Extracting…";
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/extract-payments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ month: state.month, run_id: state.runId }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      btn.disabled = false; btn.textContent = "Extract payments"; return;
    }
    sum.innerHTML = `
      <div class="kv"><span class="k">Payment rows</span><span class="v">${fmtInt(j.payment_rows)}</span></div>
      <div class="kv"><span class="k">Unique invoices</span><span class="v">${fmtInt(j.unique_invoices)}</span></div>
      <div class="kv"><span class="k">Sum Settlement</span><span class="v">${fmtINR(j.settlement_total)}</span></div>
    `;
    renderByMode(j.by_mode);
    const dl = document.getElementById("download-pay-csv");
    dl.href = runFileUrl("payment.csv");
    dl.classList.remove("hidden");
    dl.textContent = "Download payment.csv";
    btn.disabled = false; btn.textContent = "Re-run extract";
    document.getElementById("next-4").disabled = false;
  } catch (err) {
    sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${err.message}</span></div>`;
    btn.disabled = false; btn.textContent = "Extract payments";
  }
});

function renderByMode(rows) {
  document.getElementById("pay-bd-h").classList.remove("hidden");
  const t = document.getElementById("pay-by-mode");
  let html = `<thead><tr><th>Mode</th><th class="num">Count</th><th class="num">Amount (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.mode}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.amount)}</td></tr>`;
  });
  const tc = rows.reduce((a,r)=>a+r.count,0);
  const ta = rows.reduce((a,r)=>a+r.amount,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(ta)}</td></tr></tbody>`;
  t.innerHTML = html;
}

document.getElementById("next-4").addEventListener("click", () => showStep(5));

// ---- STEP 5: Generate Journal + close-out ----
document.getElementById("run-journal").addEventListener("click", async () => {
  const btn = document.getElementById("run-journal");
  const sum = document.getElementById("journal-summary");
  btn.disabled = true; btn.textContent = "Generating…";
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/generate-journal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        month: state.month, run_id: state.runId,
        alter_id_base: parseInt(document.getElementById("journal-alter-id").value, 10) || 80000,
      }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      btn.disabled = false; btn.textContent = "Generate Journal XML"; return;
    }
    sum.innerHTML = `
      <div class="kv"><span class="k">Vouchers</span><span class="v">${fmtInt(j.voucher_count)}</span></div>
      <div class="kv"><span class="k">Dr payment ledgers</span><span class="v">${fmtINR(j.total)}</span></div>
      <div class="kv"><span class="k">Round Off (Cr=gain)</span><span class="v">${fmtINR(j.round_off || 0)}</span></div>
    `;
    renderLedgerBreakdown("journal-breakdown", "journal-bd-h", j.breakdown);
    const dl = document.getElementById("download-journal-xml");
    dl.href = runFileUrl("journal.xml.gz");
    dl.classList.remove("hidden");
    dl.textContent = "Download Journal XML (gz)";
    renderCloseout(j.closeout);
    addBundleLink();
    if (j.combined_xml) addCombinedLink();
    btn.disabled = false; btn.textContent = "Re-generate Journal XML";
  } catch (err) {
    sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${err.message}</span></div>`;
    btn.disabled = false; btn.textContent = "Generate Journal XML";
  }
});

function renderLedgerBreakdown(tableId, hId, rows) {
  document.getElementById(hId).classList.remove("hidden");
  const t = document.getElementById(tableId);
  let html = `<thead><tr><th>Ledger</th><th class="num">Count</th><th class="num">Amount (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.ledger}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.amount)}</td></tr>`;
  });
  const tc = rows.reduce((a,r)=>a+r.count,0);
  const ta = rows.reduce((a,r)=>a+r.amount,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)"><td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(ta)}</td></tr></tbody>`;
  t.innerHTML = html;
}

function renderCloseout(co) {
  document.getElementById("closeout-h").classList.remove("hidden");
  const el = document.getElementById("closeout");
  el.innerHTML = `
    <div class="kv"><span class="k">Sales Dr Sundry Debtors</span><span class="v">${fmtINR(co.sales_sundry_debtors_dr)}</span></div>
    <div class="kv"><span class="k">Journal Cr Sundry Debtors</span><span class="v">${fmtINR(co.journal_sundry_debtors_cr)}</span></div>
    <div class="kv"><span class="k">Net (should be ₹0)</span><span class="v" style="color:${co.balanced ? 'var(--good)' : 'var(--bad)'}">${fmtINR(co.net)} ${co.balanced ? '✓' : '✗'}</span></div>
  `;
}

function addBundleLink() {
  const actions = document.querySelector("#step-5 .actions");
  if (document.getElementById("download-bundle")) return;
  const a = document.createElement("a");
  a.id = "download-bundle";
  a.className = "btn-link";
  a.target = "_blank";
  a.href = runFileUrl("bundle.zip");
  a.textContent = "Download full run bundle (zip)";
  actions.appendChild(a);
}

function addCombinedLink() {
  const actions = document.querySelector("#step-5 .actions");
  if (document.getElementById("download-combined")) return;
  const a = document.createElement("a");
  a.id = "download-combined";
  a.className = "btn-link active";
  a.target = "_blank";
  a.href = runFileUrl("combined.xml.gz");
  a.textContent = "★ Download Combined XML (gz) — single import, advance-receipt ordered";
  a.style.fontWeight = "600";
  actions.insertBefore(a, actions.firstChild);
}
