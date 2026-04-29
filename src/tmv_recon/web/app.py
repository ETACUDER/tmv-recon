"""tmv-recon web UI: file buckets, column mapping viewer, recon preview, export."""
from __future__ import annotations
import math
from pathlib import Path
from typing import Any
from dataclasses import asdict
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tmv_recon.config import ROOT, INPUT_DIR, OUTPUT_DIR, TALLY_COMPANY
from tmv_recon.parsers import excel as xls
from tmv_recon.integration import (
    load_preset, from_dict, build, validate, Issue,
)
from tmv_recon.integration.mapping import ColumnMap, Field
from tmv_recon.tally.xml import vouchers_envelope
from tmv_recon.tally.csv_export import write as write_csv
from tmv_recon.tally.http import post_xml
from .buckets import scan, BUCKETS, BUCKET_BY_KEY

app = FastAPI(title="tmv-recon UI")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# Configurable scan root via query param; defaults to data/input + meet-recording
DEFAULT_ROOTS = [INPUT_DIR, ROOT / "meet-recording"]


def _safe_jsonable(v: Any) -> Any:
    """Make a value JSON-safe (handle NaN, Timestamps, etc.)."""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, "isoformat"):
        try: return v.isoformat()
        except Exception: pass
    return v


def _df_preview(df: pd.DataFrame, limit: int = 30) -> dict:
    cols = [str(c) for c in df.columns]
    head = df.head(limit)
    rows = [[_safe_jsonable(v) for v in row] for row in head.itertuples(index=False, name=None)]
    return {"columns": cols, "rows": rows, "total_rows": int(len(df))}


@app.get("/")
def root() -> FileResponse:
    """Unified dashboard with tabs: Dashboard, Pipeline, Files, Reconciliation."""
    return FileResponse(STATIC / "unified.html")


@app.get("/api/config")
def api_config() -> dict:
    return {
        "root": str(ROOT),
        "input_dir": str(INPUT_DIR),
        "meet_recording": str(ROOT / "meet-recording"),
        "tally_company": TALLY_COMPANY,
        "buckets": [asdict(b) for b in BUCKETS],
    }


@app.get("/api/sources")
def api_sources(roots: list[str] | None = Query(default=None)) -> dict:
    """List all spreadsheet files grouped by bucket. Scans configured roots."""
    paths: list[Path] = [Path(r) for r in roots] if roots else DEFAULT_ROOTS
    merged: dict[str, list[dict]] = {b.key: [] for b in BUCKETS}
    for p in paths:
        if not p.exists():
            continue
        for k, files in scan(p).items():
            for f in files:
                f["root"] = str(p)
            merged[k].extend(files)
    counts = {k: len(v) for k, v in merged.items()}
    return {"buckets": merged, "counts": counts}


@app.get("/api/file")
def api_file(path: str, sheet: str | int = 0, limit: int = 30) -> dict:
    p = Path(path)
    if not p.exists():
        raise HTTPException(404, f"file not found: {path}")

    # Handle CSV files
    if p.suffix.lower() == ".csv":
        try:
            df = pd.read_csv(p)
            return {
                "path": str(p),
                "sheet": None,
                "sheets": [],
                "preview": _df_preview(df, limit=limit),
            }
        except Exception as e:
            raise HTTPException(400, f"cannot read CSV: {e}")

    # Handle Excel files
    if p.suffix.lower() not in {".xlsx", ".xls"}:
        raise HTTPException(400, f"unsupported file type: {p.suffix}")

    try:
        sheets_dict = xls.sheets(p)
    except Exception as e:
        raise HTTPException(400, f"cannot read: {e}")
    sheet_names = list(sheets_dict.keys())
    sel = sheet if isinstance(sheet, str) and sheet in sheets_dict else sheet_names[0]
    if isinstance(sel, int):
        sel = sheet_names[min(sel, len(sheet_names)-1)]
    df = sheets_dict[sel]
    return {
        "path": str(p), "sheet": sel, "sheets": sheet_names,
        "preview": _df_preview(df, limit=limit),
    }


@app.get("/api/presets")
def api_presets() -> dict:
    """List bundled presets and their column mappings."""
    out = []
    presets_dir = Path(__file__).parent.parent / "integration" / "presets"
    for f in sorted(presets_dir.glob("*.yaml")):
        try:
            cmap = load_preset(f.stem)
            out.append({
                "name": f.stem,
                "mode": cmap.mode,
                "fields": _mapping_summary(cmap),
            })
        except Exception as e:
            out.append({"name": f.stem, "error": str(e)})
    return {"presets": out}


def _field_summary(f: Field | None) -> dict | None:
    if f is None: return None
    return {
        "column": f.column, "value": f.value,
        "transform": f.transform, "required": f.required,
    }


def _mapping_summary(c: ColumnMap) -> dict:
    return {
        "voucher_type":   _field_summary(c.voucher_type),
        "date":           _field_summary(c.date),
        "voucher_number": _field_summary(c.voucher_number),
        "narration":      _field_summary(c.narration),
        "reference":      _field_summary(c.reference),
        "party":          _field_summary(c.party),
        "group_by":       _field_summary(c.group_by),
        "entries": [
            {
                "ledger": _field_summary(e.ledger if hasattr(e.ledger, "transform") else Field(value=e.ledger)),
                "amount": _field_summary(e.amount),
                "is_deemed_positive": _field_summary(e.is_deemed_positive) if isinstance(e.is_deemed_positive, Field) else e.is_deemed_positive,
                "is_party_ledger": e.is_party_ledger,
            } for e in c.entries
        ],
        "bank_ledger": c.bank_ledger,
        "debit_amount": _field_summary(c.debit_amount),
        "credit_amount": _field_summary(c.credit_amount),
        "signed_amount": _field_summary(c.signed_amount),
        "contra_ledger": _field_summary(c.contra_ledger),
        "default_contra_ledger": c.default_contra_ledger,
        "payment_voucher_type": c.payment_voucher_type,
        "receipt_voucher_type": c.receipt_voucher_type,
    }


class PreviewReq(BaseModel):
    path: str
    sheet: str | int | None = None
    preset: str | None = None
    mapping: dict | None = None       # raw mapping dict if no preset


@app.post("/api/preview")
def api_preview(req: PreviewReq) -> dict:
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(404, f"missing: {req.path}")
    df = xls.sheet(p, req.sheet if req.sheet is not None else 0)
    if req.preset:
        cmap = load_preset(req.preset)
    elif req.mapping:
        cmap = from_dict(req.mapping)
    else:
        raise HTTPException(400, "preset or mapping required")
    try:
        vouchers = build(df, cmap)
    except Exception as e:
        return {"ok": False, "error": str(e), "vouchers": [], "issues": []}
    issues = validate(vouchers)
    return {
        "ok": True,
        "mode": cmap.mode,
        "vouchers": [_voucher_to_dict(v) for v in vouchers],
        "issues": [
            {"severity": i.severity, "voucher_index": i.voucher_index, "message": i.message}
            for i in issues
        ],
        "totals": {
            "vouchers": len(vouchers),
            "entries": sum(len(v.entries) for v in vouchers),
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
        },
    }


def _voucher_to_dict(v) -> dict:
    return {
        "date": v.date.isoformat() if v.date else None,
        "voucher_type": v.voucher_type,
        "voucher_number": v.voucher_number,
        "narration": v.narration,
        "reference": v.reference,
        "party_ledger": v.party_ledger,
        "entries": [
            {
                "ledger": e.ledger,
                "amount": e.amount,
                "dr_cr": "Dr" if e.is_deemed_positive else "Cr",
                "is_party_ledger": e.is_party_ledger,
            } for e in v.entries
        ],
        "total": sum(abs(e.amount) for e in v.entries) / 2 if v.entries else 0.0,
    }


class ExportReq(BaseModel):
    path: str
    sheet: str | int | None = None
    preset: str | None = None
    mapping: dict | None = None
    format: str = "xml"          # "xml" | "csv" | "tally"
    company: str | None = None


@app.post("/api/export")
def api_export(req: ExportReq) -> dict:
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(404, f"missing: {req.path}")
    df = xls.sheet(p, req.sheet if req.sheet is not None else 0)
    if req.preset:
        cmap = load_preset(req.preset)
    elif req.mapping:
        cmap = from_dict(req.mapping)
    else:
        raise HTTPException(400, "preset or mapping required")
    vouchers = build(df, cmap)
    issues = validate(vouchers)
    company = req.company or TALLY_COMPANY

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{p.stem}.{req.preset or 'custom'}"

    if req.format == "xml":
        xml = vouchers_envelope(vouchers, company=company)
        out = OUTPUT_DIR / f"{stem}.xml"
        out.write_text(xml, encoding="utf-8")
        return {"format": "xml", "path": str(out), "size": out.stat().st_size,
                "vouchers": len(vouchers), "issues": len(issues)}
    if req.format == "csv":
        out = OUTPUT_DIR / f"{stem}.csv"
        write_csv(vouchers, out)
        return {"format": "csv", "path": str(out), "size": out.stat().st_size,
                "vouchers": len(vouchers), "issues": len(issues)}
    if req.format == "tally":
        if any(i.severity == "error" for i in issues):
            raise HTTPException(400, "validation errors — fix before pushing to Tally")
        xml = vouchers_envelope(vouchers, company=company)
        try:
            resp = post_xml(xml, timeout=120)
        except Exception as e:
            raise HTTPException(502, f"Tally POST failed: {e}")
        return {"format": "tally", "vouchers": len(vouchers),
                "tally_response": resp[:8000]}
    raise HTTPException(400, f"unknown format: {req.format}")


@app.get("/api/download")
def api_download(path: str) -> FileResponse:
    p = Path(path)
    if not p.is_relative_to(OUTPUT_DIR):
        raise HTTPException(403, "outside output dir")
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, filename=p.name)


@app.get("/api/recon")
def api_recon() -> dict:
    """Return current state of the ETL canonical + match + tally-signal outputs."""
    canon = ROOT / "data" / "recon" / "canonical"
    matches = ROOT / "data" / "recon" / "matches"
    reports = ROOT / "data" / "recon" / "reports"

    def _nrows(p: Path) -> int:
        if not p.exists(): return 0
        try:
            with p.open() as f: return sum(1 for _ in f) - 1
        except Exception: return 0

    canonical = {n: _nrows(canon / f"{n}.csv") for n in ("invoice","booking","payment","bank")}
    match_counts = {n: _nrows(matches / f"{n}.csv") for n in ("ptm_bank","ptm_invoice","booking_invoice")}
    unmatched = {n: _nrows(matches / f"{n}.csv") for n in ("unmatched_ptm","unmatched_ptm_invoice","unmatched_booking")}

    # Tally signal: parse the file-level CSV
    tally_signal = {}
    sig_csv = reports / "tally_signal.csv"
    if sig_csv.exists():
        df = pd.read_csv(sig_csv)
        tally_signal = {
            "files_total": int(len(df)),
            "files_booked": int(df["in_tally"].sum()),
            "rows_total": int(df["row_count"].sum()),
            "rows_booked": int(df.loc[df["in_tally"], "row_count"].sum()),
            "by_stream": [
                {
                    "stream": s,
                    "booked": int(g.loc[g["in_tally"], "row_count"].sum()),
                    "pending": int(g.loc[~g["in_tally"], "row_count"].sum()),
                    "files_booked": int(g["in_tally"].sum()),
                    "files_total": int(len(g)),
                } for s, g in df.groupby("stream")
            ],
            "pending_by_month": (
                df[~df["in_tally"]].groupby(["stream", "month"])["row_count"].sum()
                .reset_index().rename(columns={"row_count": "pending_rows"})
                .to_dict("records")
            ),
        }

    summary_txt = ""
    if (reports / "summary.txt").exists():
        summary_txt = (reports / "summary.txt").read_text()

    return {
        "canonical": canonical,
        "matches": match_counts,
        "unmatched": unmatched,
        "tally_signal": tally_signal,
        "summary_text": summary_txt,
    }


@app.get("/api/tally-ping")
def api_tally_ping() -> dict:
    """Quick health check on the configured Tally endpoint."""
    try:
        resp = post_xml(
            "<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
            "<TYPE>Data</TYPE><ID>Trial Balance</ID></HEADER><BODY><DESC>"
            "<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
            "</STATICVARIABLES></DESC></BODY></ENVELOPE>",
            timeout=10,
        )
        return {"ok": True, "response_excerpt": resp[:600]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main() -> None:
    import uvicorn
    uvicorn.run("tmv_recon.web.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()


# ============== NEW DASHBOARD APIs ==============

@app.get("/api/stats")
def api_stats() -> dict:
    """Get pipeline statistics for dashboard."""
    import pandas as pd
    from pathlib import Path

    canonical = ROOT / "data/recon/canonical"
    stats = {
        "bookings": 0,
        "booking_invoices": 0,
        "payments": 0,
        "payment_utrs": 0,
        "invoices": 0,
        "match_rate": 0,
        "matched": 0,
        "total": 0
    }

    try:
        # Bookings
        if (canonical / "bookings.csv").exists():
            df = pd.read_csv(canonical / "bookings.csv")
            stats["bookings"] = int(len(df))
            stats["booking_invoices"] = int(df["invoice_no"].notna().sum())

        # Payments
        if (canonical / "upi_payments.csv").exists():
            df = pd.read_csv(canonical / "upi_payments.csv")
            stats["payments"] = int(len(df))
            stats["payment_utrs"] = int(df["utr"].notna().sum())

        # Invoices
        if (canonical / "invoice.csv").exists():
            df = pd.read_csv(canonical / "invoice.csv")
            stats["invoices"] = int(len(df))
            stats["total"] = int(len(df))

        # Match rate
        matches_dir = ROOT / "data/recon/matches"
        if (matches_dir / "exact_matches.csv").exists():
            df = pd.read_csv(matches_dir / "exact_matches.csv")
            stats["matched"] = int(len(df))

        if stats["total"] > 0:
            stats["match_rate"] = float(round((stats["matched"] / stats["total"]) * 100, 1))

    except Exception as e:
        print(f"Stats error: {e}")

    return stats


@app.get("/api/master-table")
def api_master_table() -> list:
    """Get master reconciliation table."""
    import pandas as pd
    
    records = []
    canonical = ROOT / "data/recon/canonical"
    
    try:
        if not (canonical / "invoice.csv").exists():
            return []
        
        # Load invoices as base
        invoices = pd.read_csv(canonical / "invoice.csv")
        
        # Load matches if exist
        booking_matches = {}
        payment_matches = {}
        
        matches_dir = ROOT / "data/recon/matches"
        if (matches_dir / "exact_matches.csv").exists():
            matches = pd.read_csv(matches_dir / "exact_matches.csv")
            for _, row in matches.iterrows():
                if "invoice_no" in row and pd.notna(row.get("invoice_no")):
                    booking_matches[row["invoice_no"]] = True
        
        # Build master table
        for _, inv in invoices.head(50).iterrows():  # Limit to 50 for performance
            invoice_no = inv.get("invoice_no", "")
            records.append({
                "invoice_no": invoice_no,
                "guest_name": str(inv.get("guest_name", ""))[:30],
                "invoice_date": str(inv.get("invoice_date", ""))[:10],
                "amount": float(inv.get("gross_amount", 0)),
                "booking_matched": invoice_no in booking_matches,
                "payment_matched": False,  # TODO: implement
                "status": "complete" if invoice_no in booking_matches else "pending",
                "voucher_generated": False  # TODO: check output dir
            })
    
    except Exception as e:
        print(f"Master table error: {e}")
    
    return records


@app.post("/api/pipeline/extract")
def api_pipeline_extract() -> dict:
    """Run extract pipeline."""
    import subprocess
    try:
        result = subprocess.run(
            [".venv/bin/python", "-m", "tmv_recon.etl.extract.booking"],
            cwd=ROOT,
            capture_output=True,
            timeout=120
        )
        return {"success": result.returncode == 0, "output": result.stdout.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/pipeline/match")
def api_pipeline_match() -> dict:
    """Run match pipeline."""
    # TODO: implement matcher CLI
    return {"success": True, "message": "Matcher not yet implemented"}


@app.post("/api/pipeline/generate")
def api_pipeline_generate() -> dict:
    """Run voucher generation."""
    import subprocess
    try:
        result = subprocess.run(
            [".venv/bin/python", "scripts/generate_sales_vouchers.py"],
            cwd=ROOT,
            capture_output=True,
            timeout=60
        )
        return {"success": result.returncode == 0, "output": result.stdout.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/files")
def api_files() -> dict:
    """Get actual file listings organized by pipeline stage."""
    import os

    def scan_dir(path: Path, pattern: str = "*") -> list:
        if not path.exists():
            return []
        files = []
        for f in sorted(path.glob(pattern)):
            if f.is_file():
                stat = f.stat()
                size_kb = round(stat.st_size / 1024, 1)
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size_kb": size_kb,
                    "size_human": f"{size_kb}KB" if size_kb < 1024 else f"{round(size_kb/1024, 1)}MB"
                })
        return files

    # Count rows in CSV
    def count_rows(path: Path) -> int:
        if not path.exists():
            return 0
        try:
            with path.open() as f:
                return sum(1 for _ in f) - 1  # exclude header
        except:
            return 0

    # Input files
    raw_booking = ROOT / "meet-recording" / "data_sheets_historical"
    raw_payments = ROOT / "meet-recording" / "raw_upi_payments"
    raw_bank = ROOT / "meet-recording" / "data_sheets_historical"

    # Canonical files
    canonical = ROOT / "data" / "recon" / "canonical"
    canonical_files = scan_dir(canonical, "*.csv")
    for f in canonical_files:
        f["rows"] = count_rows(Path(f["path"]))

    # Match files
    matches = ROOT / "data" / "recon" / "matches"
    match_files = scan_dir(matches, "*.csv")
    for f in match_files:
        f["rows"] = count_rows(Path(f["path"]))

    # Output files
    output = ROOT / "data" / "recon" / "output"
    output_files = scan_dir(output, "*.xml")
    output_csv = scan_dir(output, "*.csv")

    # Reports
    reports = ROOT / "data" / "recon" / "reports"
    report_files = scan_dir(reports, "*.txt") + scan_dir(reports, "*.csv")

    return {
        "input": {
            "booking": scan_dir(raw_booking, "AGODA*.xlsx")[:5],  # sample
            "payment": scan_dir(raw_payments, "PTM*.xlsx")[:5],
            "bank": scan_dir(raw_bank, "INDIAN*.xls")[:5],
            "invoice": [{"name": "transaction_detail20250428.xlsx", "path": str(ROOT / "meet-recording" / "transaction_detail20250428.xlsx")}]
        },
        "canonical": canonical_files,
        "matches": match_files,
        "output": {
            "xml": output_files,
            "csv": output_csv
        },
        "reports": report_files
    }

