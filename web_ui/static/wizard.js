"use strict";

const state = {
  uploadPath: null,
  month: null,
  canonicalPath: null,
  xmlPath: null,
};

const fmtINR = n => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
const fmtInt = n => Number(n).toLocaleString("en-IN");
const fmtBytes = b => b < 1024 ? b + " B" : b < 1024*1024 ? (b/1024).toFixed(1) + " KB" : (b/1024/1024).toFixed(1) + " MB";

function showStep(n) {
  for (let i = 1; i <= 3; i++) {
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
  btn.disabled = true; btn.textContent = "Aggregating…";
  showStep(2);
  await runAggregate();
  btn.textContent = "Next: Aggregate →";
});

// ---- STEP 2: Aggregate ----
async function runAggregate() {
  const sum = document.getElementById("agg-summary");
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/aggregate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_path: state.uploadPath, month: state.month }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      return;
    }
    state.canonicalPath = j.canonical_path;
    sum.innerHTML = `
      <div class="kv"><span class="k">Month</span><span class="v">${state.month}</span></div>
      <div class="kv"><span class="k">Invoices</span><span class="v">${fmtInt(j.invoices)}</span></div>
      <div class="kv"><span class="k">Valid (Gross > 0)</span><span class="v">${fmtInt(j.valid)}</span></div>
      <div class="kv"><span class="k">Sum Gross</span><span class="v">${fmtINR(j.gross_total)}</span></div>
      <div class="kv"><span class="k">Canonical CSV</span><span class="v" style="font-size:11px">${j.canonical_path}</span></div>
    `;
    renderBySource(j.by_source);
    renderCanonPreview(j.columns, j.preview);
    const dl = document.getElementById("download-csv");
    dl.href = "/api/download?path=" + encodeURIComponent(j.canonical_path);
    dl.classList.remove("hidden");
    dl.textContent = "Download canonical CSV";
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
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)">
    <td>TOTAL</td><td class="num">${fmtInt(totalC)}</td><td class="num">${fmtINR(total)}</td></tr>`;
  html += `</tbody></table>`;
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

// ---- STEP 3: Generate ----
document.getElementById("run-generate").addEventListener("click", async () => {
  const btn = document.getElementById("run-generate");
  const sum = document.getElementById("gen-summary");
  btn.disabled = true; btn.textContent = "Generating…";
  sum.innerHTML = `<div class="kv"><span class="k">Status</span><span class="v">Running…</span></div>`;
  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        canonical_path: state.canonicalPath,
        month: state.month,
        alter_id_base: parseInt(document.getElementById("alter-id").value, 10) || 70000,
      }),
    });
    const j = await r.json();
    if (!r.ok) {
      sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${j.error}</span></div>`;
      btn.disabled = false; btn.textContent = "Generate XML"; return;
    }
    state.xmlPath = j.xml_path;
    sum.innerHTML = `
      <div class="kv"><span class="k">Vouchers</span><span class="v">${fmtInt(j.voucher_count)}</span></div>
      <div class="kv"><span class="k">Sum Gross</span><span class="v">${fmtINR(j.total_gross)}</span></div>
      <div class="kv"><span class="k">XML size</span><span class="v">${fmtBytes(j.xml_size)}</span></div>
      <div class="kv"><span class="k">Path</span><span class="v" style="font-size:11px">${j.xml_path}</span></div>
    `;
    renderBreakdown(j.breakdown);
    const dl = document.getElementById("download-xml");
    dl.href = "/api/download?path=" + encodeURIComponent(j.xml_path);
    dl.classList.remove("hidden");
    dl.textContent = "Download Tally XML";
    btn.disabled = false; btn.textContent = "Re-generate XML";
  } catch (err) {
    sum.innerHTML = `<div class="kv"><span class="k">Error</span><span class="v" style="color:var(--bad)">${err.message}</span></div>`;
    btn.disabled = false; btn.textContent = "Generate XML";
  }
});

function renderBreakdown(rows) {
  document.getElementById("bd-h").classList.remove("hidden");
  const t = document.getElementById("ledger-breakdown");
  let html = `<thead><tr><th>Party Ledger</th><th class="num">Count</th><th class="num">Gross (₹)</th></tr></thead><tbody>`;
  rows.forEach(r => {
    html += `<tr><td>${r.party_ledger}</td><td class="num">${fmtInt(r.count)}</td><td class="num">${fmtINR(r.gross)}</td></tr>`;
  });
  const tc = rows.reduce((a,r)=>a+r.count,0);
  const tg = rows.reduce((a,r)=>a+r.gross,0);
  html += `<tr style="font-weight:600;border-top:2px solid var(--border)">
    <td>TOTAL</td><td class="num">${fmtInt(tc)}</td><td class="num">${fmtINR(tg)}</td></tr></tbody>`;
  t.innerHTML = html;
}
