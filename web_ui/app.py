"""Standalone Flask UI for monthly Sales voucher generation.

3-step wizard:
  1. Upload raw EZee Transaction Detail Report xlsx, pick month
  2. Aggregate -> canonical invoice CSV; preview + counts by Business Source
  3. Generate verbose Tally Sales XML; party-ledger breakdown; download

Reuses CLI scripts in ../scripts via subprocess.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from flask import (
    Flask, jsonify, render_template, request, send_file, abort, Response,
)

ROOT = Path(__file__).resolve().parent.parent
UPLOADS = ROOT / "data" / "uploads"
CANON = ROOT / "data" / "recon" / "canonical"
OUT = ROOT / "data" / "recon" / "output"
SCRIPTS = ROOT / "scripts"
PY = ROOT / ".venv" / "bin" / "python"

for d in (UPLOADS, CANON, OUT):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


def _read_raw_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _month_summary(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return per-month counts of invoices in the file."""
    if "Invoice date" not in df.columns or "Invoice #" not in df.columns:
        return []
    sub = df.dropna(subset=["Invoice #"]).copy()
    sub["_d"] = pd.to_datetime(sub["Invoice date"], errors="coerce")
    sub = sub.dropna(subset=["_d"])
    sub["_m"] = sub["_d"].dt.strftime("%Y-%m")
    grouped = (
        sub.groupby("_m")
        .agg(
            invoices=("Invoice #", "nunique"),
            rows=("Invoice #", "size"),
            gross=("Gross Amount", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
        )
        .reset_index()
        .rename(columns={"_m": "month"})
        .sort_values("month")
    )
    return grouped.to_dict(orient="records")


@app.route("/")
def index():
    return render_template("wizard.html")


@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="no file"), 400
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", f.filename)
    ts = int(time.time())
    dest = UPLOADS / f"{ts}_{name}"
    f.save(dest)
    try:
        df = _read_raw_excel(dest)
    except Exception as e:
        return jsonify(error=f"could not read xlsx: {e}"), 400
    months = _month_summary(df)
    return jsonify(
        ok=True,
        upload_path=str(dest.relative_to(ROOT)),
        rows=int(len(df)),
        months=months,
    )


def _canon_csv_path(month: str) -> Path:
    # month is YYYY-MM
    mon_short = {
        "01": "jan", "02": "feb", "03": "mar", "04": "apr",
        "05": "may", "06": "jun", "07": "jul", "08": "aug",
        "09": "sep", "10": "oct", "11": "nov", "12": "dec",
    }
    y, m = month.split("-")
    return CANON / f"invoice_{mon_short[m]}{y}.csv"


def _xml_path(month: str) -> Path:
    y, m = month.split("-")
    mon_short = {
        "01": "jan", "02": "feb", "03": "mar", "04": "apr",
        "05": "may", "06": "jun", "07": "jul", "08": "aug",
        "09": "sep", "10": "oct", "11": "nov", "12": "dec",
    }
    return OUT / f"sales_vouchers_{mon_short[m]}{y}_verbose.xml"


@app.route("/api/aggregate", methods=["POST"])
def api_aggregate():
    data = request.get_json(force=True)
    upload_rel = data.get("upload_path")
    month = data.get("month")
    if not upload_rel or not month or not re.fullmatch(r"\d{4}-\d{2}", month):
        return jsonify(error="upload_path and month (YYYY-MM) required"), 400
    raw = ROOT / upload_rel
    if not raw.exists():
        return jsonify(error=f"upload not found: {upload_rel}"), 404
    out_csv = _canon_csv_path(month)
    cmd = [
        str(PY), str(SCRIPTS / "aggregate_invoices_monthly.py"),
        "--raw", str(raw), "--month", month, "--out", str(out_csv),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return jsonify(error=proc.stderr or proc.stdout), 500

    df = pd.read_csv(out_csv)
    valid = df[df["Gross Amount"] > 0]
    by_source = (
        valid.assign(_bs=valid["Business Source"].fillna("(blank)").replace("", "(blank)"))
        .groupby("_bs")
        .agg(count=("Invoice #", "count"), gross=("Gross Amount", "sum"))
        .reset_index()
        .rename(columns={"_bs": "business_source"})
        .sort_values("gross", ascending=False)
    )
    preview = df.head(25).fillna("").to_dict(orient="records")
    return jsonify(
        ok=True,
        canonical_path=str(out_csv.relative_to(ROOT)),
        invoices=int(len(df)),
        valid=int(len(valid)),
        gross_total=float(valid["Gross Amount"].sum()),
        by_source=by_source.to_dict(orient="records"),
        preview=preview,
        columns=list(df.columns),
        log=proc.stdout.strip(),
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True)
    canon_rel = data.get("canonical_path")
    month = data.get("month")
    alter_id_base = int(data.get("alter_id_base") or 70000)
    if not canon_rel or not month:
        return jsonify(error="canonical_path and month required"), 400
    canon = ROOT / canon_rel
    if not canon.exists():
        return jsonify(error=f"canonical not found: {canon_rel}"), 404
    out_xml = _xml_path(month)
    cmd = [
        str(PY), str(SCRIPTS / "generate_sales_vouchers_verbose.py"),
        "--input", str(canon), "--output", str(out_xml),
        "--alter-id-base", str(alter_id_base),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return jsonify(error=proc.stderr or proc.stdout), 500

    # Parse XML to compute party-ledger breakdown
    content = out_xml.read_bytes().decode("utf-16")
    counts: dict[str, int] = {}
    totals: dict[str, float] = {}
    for m in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", content, re.S):
        body = m.group(0)
        le = re.search(r"<LEDGERENTRIES\.LIST>(.*?)</LEDGERENTRIES\.LIST>", body, re.S)
        if not le:
            continue
        name = re.search(r"<LEDGERNAME>([^<]+)", le.group(1)).group(1)
        amt = -float(re.search(r"<AMOUNT>([^<]+)", le.group(1)).group(1))
        counts[name] = counts.get(name, 0) + 1
        totals[name] = totals.get(name, 0.0) + amt
    breakdown = [
        {"party_ledger": k, "count": v, "gross": totals[k]}
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return jsonify(
        ok=True,
        xml_path=str(out_xml.relative_to(ROOT)),
        xml_size=int(out_xml.stat().st_size),
        voucher_count=sum(counts.values()),
        total_gross=sum(totals.values()),
        breakdown=breakdown,
        log=proc.stdout.strip(),
    )


def _safe_download(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if not str(p).startswith(str(ROOT.resolve())) or not p.exists():
        abort(404)
    return p


@app.route("/api/download")
def api_download():
    rel = request.args.get("path", "")
    p = _safe_download(rel)
    return send_file(p, as_attachment=True, download_name=p.name)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5005)
    args = ap.parse_args()
    app.run(host=args.host, port=args.port, debug=False)
