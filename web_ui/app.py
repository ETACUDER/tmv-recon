"""Flask UI for monthly EZee -> Tally voucher generation.

5-step wizard with versioned per-month history:
  1. Upload raw EZee xlsx, pick month  -> starts a new RUN
  2. Aggregate -> canonical invoice CSV (lives in run folder)
  3. Generate Sales XML (gzipped, lives in run folder)
  4. Extract payments -> canonical payment CSV
  5. Generate Journal XML + close-out check; finalize run; bundle.zip built

Storage layout managed by web_ui/runs.py — every run preserved indefinitely.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from flask import (
    Flask, jsonify, render_template, request, send_file, abort,
    redirect, url_for, session,
)

from runs import RunStore  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "data" / "uploads"
RUNS_BASE = ROOT / "data" / "recon" / "runs"
SCRIPTS = ROOT / "scripts"
# PY resolves to: TMV_PY env override, else local .venv (dev), else current interpreter (prod)
_default_py = ROOT / ".venv" / "bin" / "python"
PY = Path(
    os.environ.get("TMV_PY")
    or (str(_default_py) if _default_py.exists() else sys.executable)
)

UPLOADS.mkdir(parents=True, exist_ok=True)
store = RunStore(RUNS_BASE)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
app.secret_key = os.environ.get("TMV_SECRET_KEY", "dev-only-change-in-prod")

# ----- Auth (single shared login via env vars) -----
AUTH_USER = os.environ.get("TMV_USER")
AUTH_PASS = os.environ.get("TMV_PASS")
AUTH_ENABLED = bool(AUTH_USER and AUTH_PASS)


@app.before_request
def _require_login():
    if not AUTH_ENABLED:
        return None
    if request.endpoint in {"login", "static"} or request.path.startswith("/static/"):
        return None
    if session.get("authed"):
        return None
    if request.path.startswith("/api/"):
        return jsonify(error="not authenticated"), 401
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if not AUTH_ENABLED:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        u = request.form.get("u", "")
        p = request.form.get("p", "")
        if u == AUTH_USER and p == AUTH_PASS:
            session["authed"] = True
            session["operator"] = u
            return redirect(request.args.get("next") or url_for("index"))
        error = "invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login") if AUTH_ENABLED else url_for("index"))


def _operator() -> str:
    return session.get("operator") or "anonymous"


def _journal_xml_path(rd: Path) -> Path:
    return rd / "journal.xml"


# ----- Helpers -----
def _read_raw_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _month_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    if "Invoice date" not in df.columns or "Invoice #" not in df.columns:
        return []
    sub = df.dropna(subset=["Invoice #"]).copy()
    sub["_d"] = pd.to_datetime(sub["Invoice date"], errors="coerce")
    sub = sub.dropna(subset=["_d"])
    sub["_m"] = sub["_d"].dt.strftime("%Y-%m")
    return (
        sub.groupby("_m")
        .agg(
            invoices=("Invoice #", "nunique"),
            rows=("Invoice #", "size"),
            gross=("Gross Amount", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
        )
        .reset_index()
        .rename(columns={"_m": "month"})
        .sort_values("month")
        .to_dict(orient="records")
    )


def _run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip()
    return True, proc.stdout.strip()


def _xml_breakdown(xml_path: Path, container_tag: str) -> dict[str, Any]:
    """Parse generated XML, return per-party-ledger counts + Round Off sum + voucher count."""
    content = xml_path.read_bytes().decode("utf-16")
    counts: dict[str, int] = {}
    totals: dict[str, float] = {}
    round_off = 0.0
    vch_count = 0
    for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", content, re.S):
        vch_count += 1
        first = re.search(rf"<{container_tag}>(.*?)</{container_tag}>", vm.group(0), re.S)
        if first:
            name = re.search(r"<LEDGERNAME>([^<]+)", first.group(1)).group(1)
            amt = -float(re.search(r"<AMOUNT>([^<]+)", first.group(1)).group(1))
            counts[name] = counts.get(name, 0) + 1
            totals[name] = totals.get(name, 0.0) + amt
        for em in re.finditer(rf"<{container_tag}>(.*?)</{container_tag}>", vm.group(0), re.S):
            ln = re.search(r"<LEDGERNAME>([^<]+)", em.group(1)).group(1)
            if ln == "ROUND OFF":
                round_off += float(re.search(r"<AMOUNT>([^<]+)", em.group(1)).group(1))
    breakdown = [
        {"ledger": k, "count": v, "amount": totals[k]}
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return {
        "voucher_count": vch_count,
        "breakdown": breakdown,
        "total": sum(totals.values()),
        "round_off": round_off,
    }


# ----- Routes -----
@app.route("/")
def index():
    return render_template("wizard.html", auth_enabled=AUTH_ENABLED, nav="wizard")


@app.route("/flow")
def flow():
    return render_template("flow.html", auth_enabled=AUTH_ENABLED, nav="flow")


@app.route("/history")
def history():
    return render_template("history.html", auth_enabled=AUTH_ENABLED, nav="history")


@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="no file"), 400
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f.filename)
    dest = UPLOADS / f"{int(time.time())}_{name}"
    f.save(dest)
    try:
        df = _read_raw_excel(dest)
    except Exception as e:
        return jsonify(error=f"could not read xlsx: {e}"), 400
    return jsonify(
        ok=True,
        upload_path=str(dest.relative_to(ROOT)),
        rows=int(len(df)),
        months=_month_summary(df),
    )


@app.route("/api/start-run", methods=["POST"])
def api_start_run():
    """Open a new run folder for (upload, month). Returns run_id + paths."""
    data = request.get_json(force=True)
    upload_rel = data.get("upload_path")
    month = data.get("month")
    if not upload_rel or not month or not re.fullmatch(r"\d{4}-\d{2}", month):
        return jsonify(error="upload_path and month (YYYY-MM) required"), 400
    raw = ROOT / upload_rel
    if not raw.exists():
        return jsonify(error=f"upload not found: {upload_rel}"), 404
    run_id, run_dir = store.new_run(month, operator=_operator())
    raw_info = store.stash_raw(month, run_id, raw)
    return jsonify(
        ok=True,
        run_id=run_id,
        run_dir=str(run_dir.relative_to(ROOT)),
        raw=raw_info,
    )


def _require_run(month: str | None, run_id: str | None) -> Path | None:
    if not month or not run_id:
        return None
    rd = store.run_dir(month, run_id)
    return rd if rd.exists() else None


@app.route("/api/aggregate", methods=["POST"])
def api_aggregate():
    data = request.get_json(force=True)
    month, run_id = data.get("month"), data.get("run_id")
    rd = _require_run(month, run_id)
    if rd is None:
        return jsonify(error="run not found"), 404
    raw_path = rd / "raw.xlsx"
    invoice_csv = rd / "invoice.csv"
    ok, log = _run([
        str(PY), str(SCRIPTS / "aggregate_invoices_monthly.py"),
        "--raw", str(raw_path), "--month", month, "--out", str(invoice_csv),
    ])
    if not ok:
        return jsonify(error=log), 500
    store.record_csv(month, run_id, "invoice_csv", invoice_csv)

    df = pd.read_csv(invoice_csv)
    valid = df[df["Gross Amount"] > 0]
    by_source = (
        valid.assign(_bs=valid["Business Source"].fillna("(blank)").replace("", "(blank)"))
        .groupby("_bs")
        .agg(count=("Invoice #", "count"), gross=("Gross Amount", "sum"))
        .reset_index()
        .rename(columns={"_bs": "business_source"})
        .sort_values("gross", ascending=False)
    )
    totals = {
        "gross_total": float(valid["Gross Amount"].sum()),
        "total_payable": float(valid["Total Payable"].sum()) if "Total Payable" in valid.columns else None,
        "invoice_count": int(len(valid)),
    }
    store.update_meta(month, run_id, totals=totals)
    return jsonify(
        ok=True,
        invoice_csv=str(invoice_csv.relative_to(ROOT)),
        by_source=by_source.to_dict(orient="records"),
        preview=df.head(25).fillna("").to_dict(orient="records"),
        columns=list(df.columns),
        **totals,
        log=log,
    )


@app.route("/api/generate-sales", methods=["POST"])
def api_generate_sales():
    data = request.get_json(force=True)
    month, run_id = data.get("month"), data.get("run_id")
    alter_id_base = int(data.get("alter_id_base") or 70000)
    rd = _require_run(month, run_id)
    if rd is None:
        return jsonify(error="run not found"), 404
    invoice_csv = rd / "invoice.csv"
    sales_xml = rd / "sales.xml"
    ok, log = _run([
        str(PY), str(SCRIPTS / "generate_sales_vouchers_verbose.py"),
        "--input", str(invoice_csv), "--output", str(sales_xml),
        "--alter-id-base", str(alter_id_base),
    ])
    if not ok:
        return jsonify(error=log), 500
    summary = _xml_breakdown(sales_xml, "LEDGERENTRIES.LIST")
    store.compress_xml(month, run_id, "sales_xml", sales_xml, summary["voucher_count"])
    store.update_meta(month, run_id, totals={"sales_voucher_count": summary["voucher_count"],
                                              "sales_round_off": summary["round_off"]})
    return jsonify(
        ok=True,
        sales_xml=str(sales_xml.relative_to(ROOT)),
        log=log, **summary,
    )


@app.route("/api/extract-payments", methods=["POST"])
def api_extract_payments():
    data = request.get_json(force=True)
    month, run_id = data.get("month"), data.get("run_id")
    rd = _require_run(month, run_id)
    if rd is None:
        return jsonify(error="run not found"), 404
    raw_path = rd / "raw.xlsx"
    payment_csv = rd / "payment.csv"
    ok, log = _run([
        str(PY), str(SCRIPTS / "extract_payments_monthly.py"),
        "--raw", str(raw_path), "--month", month, "--out", str(payment_csv),
    ])
    if not ok:
        return jsonify(error=log), 500
    store.record_csv(month, run_id, "payment_csv", payment_csv)

    df = pd.read_csv(payment_csv)
    by_mode = (
        df.groupby("Settlement/Particular")
        .agg(count=("Invoice #", "count"), amount=("Settlement Amount", "sum"))
        .reset_index()
        .rename(columns={"Settlement/Particular": "mode"})
        .sort_values("amount", ascending=False)
    )
    totals = {
        "settlement_total": float(df["Settlement Amount"].sum()),
        "payment_rows": int(len(df)),
    }
    store.update_meta(month, run_id, totals=totals)
    return jsonify(
        ok=True,
        payment_csv=str(payment_csv.relative_to(ROOT)),
        unique_invoices=int(df["Invoice #"].nunique()),
        by_mode=by_mode.to_dict(orient="records"),
        preview=df.head(25).fillna("").to_dict(orient="records"),
        columns=list(df.columns),
        **totals,
        log=log,
    )


@app.route("/api/generate-journal", methods=["POST"])
def api_generate_journal():
    data = request.get_json(force=True)
    month, run_id = data.get("month"), data.get("run_id")
    alter_id_base = int(data.get("alter_id_base") or 80000)
    notes = (data.get("notes") or "").strip()
    rd = _require_run(month, run_id)
    if rd is None:
        return jsonify(error="run not found"), 404
    invoice_csv = rd / "invoice.csv"
    payment_csv = rd / "payment.csv"
    journal_xml = rd / "journal.xml"
    ok, log = _run([
        str(PY), str(SCRIPTS / "generate_journal_vouchers_verbose.py"),
        "--input", str(payment_csv), "--invoices", str(invoice_csv),
        "--output", str(journal_xml), "--alter-id-base", str(alter_id_base),
    ])
    if not ok:
        return jsonify(error=log), 500
    summary = _xml_breakdown(journal_xml, "ALLLEDGERENTRIES.LIST")
    store.compress_xml(month, run_id, "journal_xml", journal_xml, summary["voucher_count"])

    # Compute close-out: Sales Dr vs Journal Cr on Sundry Debtors
    sales_xml = rd / "sales.xml"
    sales_sd_dr = journal_sd_cr = 0.0
    if sales_xml.exists():
        c = sales_xml.read_bytes().decode("utf-16")
        for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", c, re.S):
            for em in re.finditer(r"<LEDGERENTRIES\.LIST>(.*?)</LEDGERENTRIES\.LIST>", vm.group(0), re.S):
                if re.search(r"<LEDGERNAME>Sundry Debtors</LEDGERNAME>", em.group(1)):
                    sales_sd_dr += -float(re.search(r"<AMOUNT>([^<]+)", em.group(1)).group(1))
    cj = journal_xml.read_bytes().decode("utf-16")
    for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", cj, re.S):
        for em in re.finditer(r"<ALLLEDGERENTRIES\.LIST>(.*?)</ALLLEDGERENTRIES\.LIST>", vm.group(0), re.S):
            if re.search(r"<LEDGERNAME>Sundry Debtors</LEDGERNAME>", em.group(1)):
                journal_sd_cr += float(re.search(r"<AMOUNT>([^<]+)", em.group(1)).group(1))
    closeout = {
        "sales_sundry_debtors_dr": sales_sd_dr,
        "journal_sundry_debtors_cr": journal_sd_cr,
        "net": sales_sd_dr - journal_sd_cr,
        "balanced": abs(sales_sd_dr - journal_sd_cr) < 0.01,
    }

    totals_patch = {
        "journal_voucher_count": summary["voucher_count"],
        "journal_round_off": summary["round_off"],
        "closeout": closeout,
    }
    store.update_meta(month, run_id, totals=totals_patch, notes=notes)

    # Auto-generate combined XML (vouchers ordered per-invoice so Tally imports
    # both with bill-allocation chain intact in a single operation).
    combined_xml = rd / "combined.xml"
    ok2, log2 = _run([
        str(PY), str(SCRIPTS / "generate_combined_vouchers_verbose.py"),
        "--invoices", str(invoice_csv), "--payments", str(payment_csv),
        "--output", str(combined_xml),
        "--sales-alter-id-base", str(alter_id_base - 10000),
        "--journal-alter-id-base", str(alter_id_base),
    ])
    if ok2:
        # Count combined vouchers + gzip
        import gzip, hashlib, shutil
        with combined_xml.open("rb") as src, gzip.open(str(combined_xml) + ".gz", "wb", compresslevel=9) as out:
            shutil.copyfileobj(src, out)
        h = hashlib.sha256(combined_xml.read_bytes()).hexdigest()
        store.update_meta(month, run_id, files={"combined_xml": {
            "path": str(combined_xml),
            "gz_path": str(combined_xml) + ".gz",
            "size": combined_xml.stat().st_size,
            "gz_size": Path(str(combined_xml) + ".gz").stat().st_size,
            "sha256": h,
        }})

    store.finalize(month, run_id, totals=totals_patch, notes=notes, status="complete")
    return jsonify(
        ok=True,
        journal_xml=str(journal_xml.relative_to(ROOT)),
        combined_xml=str(combined_xml.relative_to(ROOT)) if combined_xml.exists() else None,
        log=log + ("\n\n[combined]\n" + log2 if ok2 else ""),
        closeout=closeout,
        **summary,
    )


# ----- History -----
@app.route("/api/runs")
def api_runs_list():
    month = request.args.get("month")
    if month:
        return jsonify(month=month, runs=store.list_runs(month))
    return jsonify(months=store.list_months())


@app.route("/api/runs/<month>/<run_id>")
def api_run_detail(month: str, run_id: str):
    rd = store.run_dir(month, run_id)
    if not rd.exists():
        abort(404)
    meta = store.read_meta(month, run_id)
    return jsonify(meta)


# ----- Downloads -----
def _safe_run_file(month: str, run_id: str, fname: str) -> Path:
    rd = store.run_dir(month, run_id).resolve()
    if not rd.exists():
        abort(404)
    candidate = (rd / fname).resolve()
    if not str(candidate).startswith(str(rd)) or not candidate.exists():
        abort(404)
    return candidate


@app.route("/api/runs/<month>/<run_id>/file/<path:fname>")
def api_run_file(month: str, run_id: str, fname: str):
    p = _safe_run_file(month, run_id, fname)
    return send_file(p, as_attachment=True, download_name=p.name)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5005)
    args = ap.parse_args()
    app.run(host=args.host, port=args.port, debug=False)
