"""Classify source files (Excel/CSV/PDF) under meet-recording/ and symlink
them into data/{booking,invoices,payments,tally}/{raw,processed}/ buckets.

Re-runnable: idempotent. Prints a manifest of what landed where. The script
also writes a manifest CSV so downstream ETL can iterate by bucket.
"""
from __future__ import annotations
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tmv_recon.config import ROOT

DATA = ROOT / "data"
SRC_DIRS = [ROOT / "meet-recording"]
TALLY_DIR = ROOT / "meet-recording" / "tallyData"

BUCKETS = [
    "booking/raw", "booking/processed",
    "invoices/raw", "invoices/processed",
    "payments/raw", "payments/processed",
    "tally/raw",
    "recon/canonical", "recon/matches", "recon/reports",
    "_quarantine",
]

DATA_EXTS = {".xlsx", ".xls", ".csv", ".pdf"}


def _path_lc(p: Path, root: Path) -> str:
    """Lower-case POSIX path relative to root for matching."""
    rel = p.relative_to(root) if p.is_relative_to(root) else p
    return str(rel).replace("\\", "/").lower()


@dataclass
class Rule:
    bucket: str
    test: Callable[[Path, str], bool]
    reason: str


_AGODA = re.compile(r"agoda", re.I)
_GOMT = re.compile(r"\bgomt\b|\bmmt\b|\bgommt\b|makemytrip", re.I)
_PTM = re.compile(r"\bptm[\s_\-(]|paytm", re.I)
_BANK_STMT = re.compile(r"statement\s+of\s+account|indian\s+bank|bank\s+statement|bank\s+rooftop|hdfc|sbi|icici|axis", re.I)
_EZ = re.compile(r"transaction_detail|ez[\s_\-]?sheet|front[\s_\-]?office\s+sale", re.I)
_PRM_RECEIPT = re.compile(r"prmpayrcpt|payreceipt|payment\s*receipt", re.I)


def _is_tally_dump(p: Path, lc: str) -> bool:
    return "tallydata/" in lc


def _is_processed(lc: str) -> bool:
    return "data_sheets_historical/" in lc or "mangal all data sheet/" in lc


# Rules evaluated in order — first match wins.
RULES: list[Rule] = [
    Rule("tally/raw",          lambda p, lc: _is_tally_dump(p, lc),
         "lives under tallyData/ — treated as Tally signal/reference"),
    Rule("invoices/raw",       lambda p, lc: bool(_EZ.search(lc)),
         "EZ sheet / front-office invoice raw export"),
    # CONFIRMED 2026-04-28: PrmPayRcpt PDFs are LIC of India insurance receipts,
    # not TMV hotel — quarantine, do not include in payments/raw.
    Rule("_quarantine",        lambda p, lc: bool(_PRM_RECEIPT.search(lc)),
         "LIC insurance receipts (mistakenly bundled — see _discovery_payments.md)"),
    Rule("payments/raw",       lambda p, lc: "raw_upi_payments/" in lc,
         "lives in raw_upi_payments/"),
    # processed bucket — files under data_sheets_historical/
    Rule("booking/processed",  lambda p, lc: _is_processed(lc) and bool(_AGODA.search(lc)),
         "Agoda processed (booking)"),
    Rule("booking/processed",  lambda p, lc: _is_processed(lc) and bool(_GOMT.search(lc)),
         "GoMT/MMT processed (booking)"),
    Rule("payments/processed", lambda p, lc: _is_processed(lc) and bool(_PTM.search(lc)),
         "PTM aggregator processed (payment)"),
    Rule("payments/processed", lambda p, lc: _is_processed(lc) and bool(_BANK_STMT.search(lc)),
         "Bank statement processed (payment)"),
    Rule("booking/processed",  lambda p, lc: _is_processed(lc) and "guest" in lc,
         "Processed guest registry (booking)"),
]


def classify(p: Path) -> tuple[str, str] | None:
    """Returns (bucket, reason) or None if file not relevant."""
    if p.suffix.lower() not in DATA_EXTS:
        return None
    if any(part.startswith(".") for part in p.parts):
        return None
    for src in SRC_DIRS:
        if p.is_relative_to(src):
            lc = _path_lc(p, src)
            for r in RULES:
                if r.test(p, lc):
                    return r.bucket, r.reason
            return None
    return None


def setup_dirs() -> None:
    for b in BUCKETS:
        (DATA / b).mkdir(parents=True, exist_ok=True)


def _safe_link_name(src: Path, src_root: Path) -> str:
    """Flatten the relative path into a single filename, preserving signal."""
    rel = src.relative_to(src_root) if src.is_relative_to(src_root) else src
    parts = list(rel.parts)
    # drop noise prefixes
    while parts and parts[0] in {"data_sheets_historical", "mangal all data sheet", "raw_upi_payments", "tallyData", "New folder"}:
        parts.pop(0)
    flat = "__".join(parts)
    return flat


def link(src: Path, bucket: str, src_root: Path, dry_run: bool = False) -> Path | None:
    name = _safe_link_name(src, src_root)
    target = DATA / bucket / name
    if target.exists() or target.is_symlink():
        if target.is_symlink() and target.readlink().resolve() == src.resolve():
            return target           # already linked correctly
        target.unlink()
    if dry_run:
        return target
    target.symlink_to(src.resolve())
    return target


def write_manifest(records: list[dict], path: Path) -> None:
    fields = ["bucket", "name", "source", "size", "ext", "reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow(r)


def run(dry_run: bool = False) -> dict:
    setup_dirs()
    records: list[dict] = []
    counts: dict[str, int] = {b: 0 for b in BUCKETS}
    skipped: list[str] = []

    for src_root in SRC_DIRS:
        if not src_root.exists():
            continue
        for p in sorted(src_root.rglob("*")):
            if not p.is_file():
                continue
            cls = classify(p)
            if cls is None:
                if p.suffix.lower() in DATA_EXTS:
                    skipped.append(str(p.relative_to(ROOT)))
                continue
            bucket, reason = cls
            target = link(p, bucket, src_root, dry_run=dry_run)
            counts[bucket] = counts.get(bucket, 0) + 1
            records.append({
                "bucket": bucket,
                "name": target.name if target else "(dry-run)",
                "source": str(p.relative_to(ROOT)),
                "size": p.stat().st_size,
                "ext": p.suffix.lower(),
                "reason": reason,
            })

    if not dry_run:
        write_manifest(records, DATA / "recon" / "_manifest.csv")
    return {"counts": counts, "records": records, "skipped": skipped}


def main() -> None:
    import json, sys
    dry = "--dry-run" in sys.argv
    out = run(dry_run=dry)
    print(f"buckets ({'dry-run' if dry else 'linked'}):")
    for b, n in out["counts"].items():
        print(f"  {b:30s} {n}")
    print(f"skipped (not classified): {len(out['skipped'])}")
    for s in out["skipped"][:10]:
        print(f"  {s}")
    if len(out['skipped']) > 10:
        print(f"  ... +{len(out['skipped']) - 10} more")
    if not dry:
        print(f"\nmanifest: data/recon/_manifest.csv ({len(out['records'])} rows)")


if __name__ == "__main__":
    main()
