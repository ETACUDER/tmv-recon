"""Shared extractor helpers."""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

from tmv_recon.config import ROOT

CANONICAL_DIR = ROOT / "data" / "recon" / "canonical"


def canonicalize_header(s: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation. For tolerant header matching."""
    if s is None:
        return ""
    t = re.sub(r"[\s\W_]+", " ", str(s).strip().lower())
    return t.strip()


def alias_match(col: str, aliases: list[str]) -> bool:
    """True if a canonicalized col matches any of canonicalized aliases."""
    c = canonicalize_header(col)
    return any(c == canonicalize_header(a) for a in aliases)


def find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Return the actual column name in df matching any alias, or None."""
    for c in df.columns:
        if alias_match(c, aliases):
            return c
    return None


def strip_excel_quoted(v):
    """Strip leading and trailing single-quotes that Excel adds around text-stored values."""
    if not isinstance(v, str):
        return v
    s = v
    if s.startswith("'"): s = s[1:]
    if s.endswith("'"):   s = s[:-1]
    return s


def normalize_invoice_no(s) -> str | None:
    """Map `2025/2026/126` → `25-26/126`. Pass through `25-26/126`. Handle floats."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    txt = str(s).strip()
    if not txt or txt.lower() in {"cancel", "nan"}:
        return None
    # already short form
    if re.match(r"^\d{2}-\d{2}/\d+$", txt):
        return txt
    # 2025/2026/126 or 2025-2026/126
    m = re.match(r"^(\d{4})[/\-](\d{4})/(\d+(?:\.\d+)?)$", txt)
    if m:
        y1, y2, n = m.group(1), m.group(2), m.group(3)
        n = n.split(".")[0]
        return f"{y1[2:]}-{y2[2:]}/{n}"
    # plain integer (likely a folio number passed in)
    if re.match(r"^\d+(?:\.\d+)?$", txt):
        return f"25-26/{txt.split('.')[0]}"
    return txt


def write_canonical(df: pd.DataFrame, name: str) -> Path:
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    csv = CANONICAL_DIR / f"{name}.csv"
    df.to_csv(csv, index=False)
    return csv
