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
sys.path.insert(0, str(ROOT / "src"))
from tmv_recon.restaurant import generate as rooftop_generate  # type: ignore  # noqa: E402

# Writable/runtime data (runs, uploads, saved mappings) lives under TMV_DATA_DIR
# so it survives restarts/redeploys (on Azure set TMV_DATA_DIR=/home/data — the
# persistent share; the app package in wwwroot is replaced on every deploy).
DATA = Path(os.environ.get("TMV_DATA_DIR") or (ROOT / "data"))
UPLOADS = DATA / "uploads"
RUNS_BASE = DATA / "recon" / "runs"
ROOFTOP_RUNS = DATA / "recon" / "rooftop" / "runs"
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
    # Landing: pick entity (hotel vs rooftop restaurant) — kept separate.
    return render_template("landing.html", auth_enabled=AUTH_ENABLED)


@app.route("/hotel")
def hotel():
    return render_template("wizard.html", auth_enabled=AUTH_ENABLED, nav="wizard")


@app.route("/rooftop")
def rooftop():
    # Restaurant (GST Composition): upload settlement + bank statement -> Tally XML.
    return render_template("rooftop.html", auth_enabled=AUTH_ENABLED, nav="rooftop")


@app.route("/api/rooftop/generate", methods=["POST"])
def api_rooftop_generate():
    sales = request.files.get("sales")            # EZee Sales Detail .html
    settle = request.files.get("settlement")      # EZee Settlement Detail .html (payment channels)
    bank = request.files.get("bank")              # Indian Bank statement .xlsx (OPTIONAL)
    month = (request.form.get("month") or "").strip()
    if not sales or not sales.filename:
        return jsonify(error="EZee Sales Detail (.html) required"), 400
    if not settle or not settle.filename:
        return jsonify(error="EZee Settlement Detail (.html) required"), 400
    if not re.match(r"^\d{4}-\d{2}$", month):
        return jsonify(error="month must be YYYY-MM"), 400

    run_id = str(int(time.time()))
    rd = ROOFTOP_RUNS / month / run_id
    rd.mkdir(parents=True, exist_ok=True)
    sh, sd = rd / "sales_detail.html", rd / "settlement_detail.html"
    sales.save(sh)
    settle.save(sd)
    bp = None
    if bank and bank.filename:
        bp = rd / "bank_statement.xlsx"
        bank.save(bp)
    out = rd / f"combined_rooftop_{month}.xml"
    try:
        summary = rooftop_generate(str(sh), str(sd), str(out), month=month,
                                   bank_path=str(bp) if bp else None)
    except Exception as e:  # noqa: BLE001
        return jsonify(error=f"generation failed: {e}"), 500

    slim = {k: v for k, v in summary.items() if k != "events"}
    slim["download"] = f"/api/rooftop/file/{month}/{run_id}/{out.name}"
    slim["report"] = f"/rooftop/report/{month}/{run_id}"
    slim["exceptions_csv"] = f"/api/rooftop/file/{month}/{run_id}/exceptions.csv"
    import csv as _csv
    import json as _json
    (rd / "summary.json").write_text(_json.dumps(slim, indent=2))
    with open(rd / "exceptions.csv", "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["category", "severity", "date", "amount", "ledger", "ref", "action"])
        for e in summary["exceptions"]:
            w.writerow([e["category"], e["severity"], e["date"], f'{e["amount"]:.2f}',
                        e["ledger"], e["ref"], e["action"]])
    return jsonify(slim)


@app.route("/rooftop/report/<month>/<run_id>")
def rooftop_report(month: str, run_id: str):
    import json as _json
    sj = (ROOFTOP_RUNS / month / run_id / "summary.json")
    if not sj.exists():
        abort(404)
    data = _json.loads(sj.read_text())
    return render_template("rooftop_report.html", d=data, month=month,
                           run_id=run_id, auth_enabled=AUTH_ENABLED)

# Note: system-verification (ReconSystem vs the accountant's Tally export) is a
# one-off QA, NOT a web-app feature — it needs the accountant's Transactions.xml
# which the app never has during the monthly run. Generate it standalone via
# scripts/verify_rooftop_vs_tally.py.


@app.route("/api/rooftop/file/<month>/<run_id>/<path:fname>")
def api_rooftop_file(month: str, run_id: str, fname: str):
    base = ROOFTOP_RUNS.resolve()
    cand = (base / month / run_id / fname).resolve()
    if not str(cand).startswith(str(base)) or not cand.exists():
        abort(404)
    return send_file(cand, as_attachment=True, download_name=cand.name)


@app.route("/rooftop/history")
def rooftop_history():
    return render_template("rooftop_history.html", auth_enabled=AUTH_ENABLED, nav="rooftop")


@app.route("/api/rooftop/runs")
def api_rooftop_runs():
    import json as _json
    months = []
    if ROOFTOP_RUNS.exists():
        for mdir in sorted((d for d in ROOFTOP_RUNS.iterdir() if d.is_dir()),
                           key=lambda d: d.name, reverse=True):
            run_dirs = sorted((d for d in mdir.iterdir() if d.is_dir()),
                              key=lambda d: d.name, reverse=True)
            latest = run_dirs[0].name if run_dirs else None
            runs = []
            for rd in run_dirs:
                sj = rd / "summary.json"
                data = _json.loads(sj.read_text()) if sj.exists() else {}
                xmls = [p.name for p in rd.glob("*.xml")]
                runs.append({
                    "run_id": rd.name,
                    "is_latest": rd.name == latest,
                    "total_vouchers": data.get("total_vouchers"),
                    "sales_count": data.get("sales_count"),
                    "sales_total": data.get("sales_total"),
                    "receipts": data.get("receipts"),
                    "payments": data.get("payments"),
                    "receipt_total": data.get("receipt_total"),
                    "payment_total": data.get("payment_total"),
                    "unmapped_count": data.get("unmapped_count"),
                    "xml": xmls[0] if xmls else None,
                })
            months.append({"month": mdir.name, "run_count": len(run_dirs),
                           "latest_run_id": latest, "runs": runs})
    return jsonify(months=months)


@app.route("/config")
def config_page():
    return render_template("config.html", auth_enabled=AUTH_ENABLED, nav="config")


@app.route("/api/config/mappings")
def api_config_mappings():
    """Current channel/mode → ledger mappings (built-in + saved overrides) for both entities."""
    import json as _json
    from tmv_recon.restaurant import pipeline as rp
    from tmv_recon.vouchers.ledgers import (
        PAYMENT_LEDGER_BY_MODE, PAYMENT_LEDGER_OVERRIDES, NEW_REF_LEDGERS, reload_payment_overrides)

    # Rooftop — validate against the restaurant Tally master ledger list.
    master = set()
    try:
        master = {l["name"] for l in _json.loads(
            (ROOT / "data" / "recon" / "rooftop" / "ledgers.json").read_text())}
    except OSError:
        pass
    rf_ov = {}
    try:
        rf_ov = {k.upper() for k in _json.loads(rp.CHANNEL_OVERRIDES_PATH.read_text())}
    except (OSError, ValueError):
        pass
    cmap = rp.channel_map()
    rooftop = {"ledgers": sorted(master),
               "mappings": [{"channel": ch, "ledger": ci["ledger"], "journal": ci["journal"],
                             "source": "override" if ch in rf_ov else "built-in",
                             "in_master": (ci["ledger"] in master) if master else None}
                            for ch, ci in sorted(cmap.items())]}

    # Hotel — built-in + accountant overrides (no master list to validate against).
    reload_payment_overrides()
    hmap = dict(PAYMENT_LEDGER_BY_MODE)
    for k, v in PAYMENT_LEDGER_OVERRIDES.items():
        hmap[k] = v["ledger"]
    hotel = {"mappings": [{"mode": m, "ledger": led,
                           "new_ref": PAYMENT_LEDGER_OVERRIDES.get(m, {}).get("new_ref", led in NEW_REF_LEDGERS),
                           "source": "override" if m in PAYMENT_LEDGER_OVERRIDES else "built-in"}
                          for m, led in sorted(hmap.items())]}
    return jsonify(rooftop=rooftop, hotel=hotel)


@app.route("/api/config/mapping", methods=["POST"])
def api_config_mapping():
    """Save/override one mapping (rooftop channel or hotel mode) → Tally ledger."""
    import json as _json
    d = request.get_json(force=True)
    system = d.get("system")
    key = (d.get("key") or "").strip()
    ledger = (d.get("ledger") or "").strip()
    new_ref = bool(d.get("new_ref", True))
    if system not in ("rooftop", "hotel") or not key or not ledger:
        return jsonify(error="system (rooftop|hotel), key and ledger are required"), 400

    if system == "rooftop":
        from tmv_recon.restaurant import pipeline as rp
        path = rp.CHANNEL_OVERRIDES_PATH
        data = _json.loads(path.read_text()) if path.exists() else {}
        k = key.upper()
        if "journal" in d:
            journal = bool(d.get("journal"))
        else:  # keep the channel's current journal flag if none was sent
            journal = rp.channel_map().get(k, {}).get("journal", k not in rp.DIRECT_CHANNELS)
        data[k] = {"ledger": ledger, "journal": journal}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps(data, indent=2))
    else:
        from tmv_recon.vouchers.ledgers import OVERRIDES_PATH, reload_payment_overrides
        norm = (re.sub(r"[-\s]+\w*\d+\w*$", "", key).strip() or key).upper()
        data = _json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}
        data[norm] = {"ledger": ledger, "new_ref": new_ref}
        OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDES_PATH.write_text(_json.dumps(data, indent=2))
        reload_payment_overrides()
        key = norm
    return jsonify(ok=True, system=system, key=key, ledger=ledger)


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


def _hotel_validate(rd: Path) -> dict:
    """Single source of truth for a hotel run's checks: Sundry-Debtors close-out,
    manual-review invoices (reversal/refund) and unmapped payment modes."""
    import csv as _csv
    from tmv_recon.vouchers.review import find_manual_review
    from tmv_recon.vouchers.ledgers import pick_payment_ledger, reload_payment_overrides
    reload_payment_overrides()

    payment_csv, invoice_csv = rd / "payment.csv", rd / "invoice.csv"
    sales_xml, journal_xml = rd / "sales.xml", rd / "journal.xml"
    pay_rows = list(_csv.DictReader(payment_csv.open(newline=""))) if payment_csv.exists() else []
    inv_payable: dict[str, float] = {}
    if invoice_csv.exists():
        for r in _csv.DictReader(invoice_csv.open(newline="")):
            try:
                inv_payable[(r.get("Invoice #") or "").strip()] = float(r.get("Total Payable") or 0)
            except (TypeError, ValueError):
                pass
    manual_review = find_manual_review(pay_rows, inv_payable)
    review_set = {r["invoice"] for r in manual_review}

    sales_sd_dr = journal_sd_cr = 0.0
    if sales_xml.exists():
        for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", sales_xml.read_bytes().decode("utf-16"), re.S):
            vno = re.search(r"<VOUCHERNUMBER>([^<]*)", vm.group(0))
            if vno and vno.group(1) in review_set:
                continue
            for em in re.finditer(r"<LEDGERENTRIES\.LIST>(.*?)</LEDGERENTRIES\.LIST>", vm.group(0), re.S):
                if "<LEDGERNAME>Sundry Debtors</LEDGERNAME>" in em.group(1):
                    sales_sd_dr += -float(re.search(r"<AMOUNT>([^<]+)", em.group(1)).group(1))
    if journal_xml.exists():
        for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", journal_xml.read_bytes().decode("utf-16"), re.S):
            for em in re.finditer(r"<ALLLEDGERENTRIES\.LIST>(.*?)</ALLLEDGERENTRIES\.LIST>", vm.group(0), re.S):
                if "<LEDGERNAME>Sundry Debtors</LEDGERNAME>" in em.group(1):
                    journal_sd_cr += float(re.search(r"<AMOUNT>([^<]+)", em.group(1)).group(1))

    unmapped: dict[str, dict] = {}
    for row in pay_rows:
        mode = (row.get("Settlement/Particular") or "").strip()
        if mode and pick_payment_ledger(mode) is None:
            try:
                amt = abs(float(row.get("Settlement Amount") or 0))
            except (TypeError, ValueError):
                amt = 0.0
            e = unmapped.setdefault(mode, {"mode": mode, "count": 0, "amount": 0.0})
            e["count"] += 1
            e["amount"] = round(e["amount"] + amt, 2)
    return {
        "sales_sundry_debtors_dr": sales_sd_dr,
        "journal_sundry_debtors_cr": journal_sd_cr,
        "net": sales_sd_dr - journal_sd_cr,
        "balanced": abs(sales_sd_dr - journal_sd_cr) < 0.01,
        "manual_review": manual_review,
        "unmapped_modes": sorted((u for u in unmapped.values() if u["amount"] > 0.005),
                                 key=lambda x: -x["amount"]),
    }


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

    # Invoices flagged for manual review (reversal/refund) — quarantined from the
    # import, so they must also be excluded from the close-out (their sale is booked
    # but their journal isn't, by design).
    import csv as _csv
    from tmv_recon.vouchers.review import find_manual_review
    pay_rows = list(_csv.DictReader(open(payment_csv, newline="")))
    inv_payable: dict[str, float] = {}
    try:
        for r in _csv.DictReader(open(invoice_csv, newline="")):
            try:
                inv_payable[(r.get("Invoice #") or "").strip()] = float(r.get("Total Payable") or 0)
            except (TypeError, ValueError):
                pass
    except OSError:
        pass
    manual_review = find_manual_review(pay_rows, inv_payable)
    review_set = {r["invoice"] for r in manual_review}

    # Close-out: Sales Dr vs Journal Cr on Sundry Debtors (excluding review invoices)
    sales_xml = rd / "sales.xml"
    sales_sd_dr = journal_sd_cr = 0.0
    if sales_xml.exists():
        c = sales_xml.read_bytes().decode("utf-16")
        for vm in re.finditer(r"<VOUCHER\b.*?</VOUCHER>", c, re.S):
            vno = re.search(r"<VOUCHERNUMBER>([^<]*)", vm.group(0))
            if vno and vno.group(1) in review_set:
                continue
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
        "manual_review": manual_review,
    }

    # Which settlement modes have no ledger mapping? (they leave the debtor open)
    from tmv_recon.vouchers.ledgers import pick_payment_ledger, reload_payment_overrides
    reload_payment_overrides()
    unmapped: dict[str, dict] = {}
    try:
        import csv as _csv
        with open(payment_csv, newline="") as fh:
            for row in _csv.DictReader(fh):
                mode = (row.get("Settlement/Particular") or "").strip()
                if mode and pick_payment_ledger(mode) is None:
                    try:
                        amt = abs(float(row.get("Settlement Amount") or 0))
                    except (TypeError, ValueError):
                        amt = 0.0
                    e = unmapped.setdefault(mode, {"mode": mode, "count": 0, "amount": 0.0})
                    e["count"] += 1
                    e["amount"] = round(e["amount"] + amt, 2)
    except OSError:
        pass
    # ignore zero-amount noise (e.g. "Flat", "Round Off")
    closeout["unmapped_modes"] = sorted(
        (u for u in unmapped.values() if u["amount"] > 0.005), key=lambda x: -x["amount"])

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


@app.route("/api/payment-ledger-map", methods=["POST"])
def api_payment_ledger_map():
    """Accountant self-service: map an unmapped EZee settlement mode to a Tally ledger."""
    d = request.get_json(force=True)
    mode = (d.get("mode") or "").strip()
    ledger = (d.get("ledger") or "").strip()
    new_ref = bool(d.get("new_ref", True))
    if not mode or not ledger:
        return jsonify(error="mode and ledger are both required"), 400
    # strip a trailing booking id so "Cleartrip-425340" maps as "CLEARTRIP" (prefix)
    key = (re.sub(r"[-\s]+\w*\d+\w*$", "", mode).strip() or mode).upper()
    import json as _json
    path = ROOT / "data" / "recon" / "hotel_payment_ledgers.json"
    data = {}
    if path.exists():
        try:
            data = _json.loads(path.read_text())
        except ValueError:
            data = {}
    data[key] = {"ledger": ledger, "new_ref": new_ref}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2))
    from tmv_recon.vouchers.ledgers import reload_payment_overrides
    reload_payment_overrides()
    return jsonify(ok=True, key=key, ledger=ledger, new_ref=new_ref, mappings=data)


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
