"""Source bucket auto-detection from filenames + folder paths.

Mangal View Residency context (per meet-recording/.../context.md):
- EZ Sales:       transaction_detail*.xlsx (Front Office sales)
- PTM Front Office: PTM*FRONT OFFICE*.xlsx
- PTM Rooftop:    TMV ROOFTOP*.xlsx, JKP*.xlsx
- Agoda OTA:      AGODA*.xlsx
- GoMT OTA:       GOMT*.xlsx, MMT*.xlsx, *MakeMyTrip*.xlsx
- Bank statement: *bank*statement*.xlsx, BANK*.xlsx
- Processed (target Excel): mangal all data sheet/**.xlsx
- Tally export:   tallyData/**
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

XLSX_EXTS = {".xlsx", ".xls"}


@dataclass
class Bucket:
    key: str
    label: str
    icon: str
    preset: str | None      # default mapping preset for this bucket
    description: str


BUCKETS: list[Bucket] = [
    Bucket("ez_sales",      "EZ Sales (Front Office)",  "•", None,
           "Front-office invoice raw export → Tally Sales (custom mapping needed: invoice grouping + GST split)"),
    Bucket("ptm_front",     "PTM Front Office",         "•", "ptm_payment",
           "Paytm card/UPI settlement, hotel rooms"),
    Bucket("ptm_rooftop",   "PTM Rooftop / JKP",        "•", "ptm_payment",
           "Paytm card/UPI settlement, rooftop bar"),
    Bucket("agoda",         "Agoda OTA",                "•", None,
           "Agoda processed (custom mapping needed: rate-change credit notes)"),
    Bucket("gomt",          "GoMT / MMT OTA",           "•", None,
           "GoMT/MakeMyTrip processed (custom mapping needed: TCS/TDS handling)"),
    Bucket("bank",          "Bank Statement",           "•", "bank_statement",
           "Bank account statement"),
    Bucket("processed",     "Processed / Target",       "•",  None,
           "Urvashi's processed Excels — ground truth for matcher validation"),
    Bucket("tally_export",  "Tally Export",             "•", None,
           "Tally Day Book / voucher export for cross-check"),
    Bucket("other",         "Other / Unclassified",     "•", None, ""),
]
BUCKET_BY_KEY = {b.key: b for b in BUCKETS}


# Content-type patterns first (most specific). Location-based fallbacks last.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ez_sales",      re.compile(r"transaction_detail|ez[\s_-]?sheet", re.I)),
    ("agoda",         re.compile(r"agoda", re.I)),
    ("gomt",          re.compile(r"\bgomt\b|\bmmt\b|makemytrip|gomakemytrip", re.I)),
    ("ptm_rooftop",   re.compile(r"tmv\s*rooftop|jkp|(?:ptm|upi).*rooftop|rooftop.*(?:ptm|upi)", re.I)),
    ("ptm_front",     re.compile(r"ptm.*front\s*office|front\s*office.*ptm|ptm.*\(f&b|f&b.*ptm|^ptm[\s_-]", re.I)),
    ("bank",          re.compile(r"bank[\s_-]?statement|statement\s+of\s+account|hdfc|sbi|icici|axis|indian\s+bank", re.I)),
    # location fallbacks (only matched if no content pattern hit)
    ("processed",     re.compile(r"data_sheets_historical|mangal\s+all\s+data\s+sheet", re.I)),
    ("tally_export",  re.compile(r"(?:^|/)tallyData/", re.I)),
]


def classify(path: Path, root: Path) -> str:
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    name = path.name
    for key, pat in _PATTERNS:
        if pat.search(rel) or pat.search(name):
            return key
    return "other"


def scan(root: Path) -> dict[str, list[dict]]:
    """Walk root, group spreadsheet files by bucket. Returns
    {bucket_key: [{"name", "path", "size", "rel"}, ...]}."""
    out: dict[str, list[dict]] = {b.key: [] for b in BUCKETS}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in XLSX_EXTS:
            continue
        if any(part.startswith(".") for part in p.parts):
            continue
        bucket = classify(p, root)
        out[bucket].append({
            "name": p.name,
            "path": str(p),
            "rel": str(p.relative_to(root)) if p.is_relative_to(root) else str(p),
            "size": p.stat().st_size,
            "mtime": p.stat().st_mtime,
        })
    return out
