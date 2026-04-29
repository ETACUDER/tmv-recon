"""Cell-value transforms. Designed for messy real-world Excel input."""
from __future__ import annotations
import re
from datetime import date, datetime
from typing import Any
import pandas as pd

_AMOUNT_STRIP = re.compile(r"[₹$,\s]|(?:Rs\.?|INR|USD|EUR)", re.IGNORECASE)


def to_date(v: Any) -> date | None:
    """Accept datetime, date, pandas Timestamp, str (many formats), Excel serial."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, pd.Timestamp):
        return v.date()
    if isinstance(v, (int, float)):
        # Treat as Excel serial date (days since 1899-12-30)
        return (pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))).date()
    s = str(v).strip()
    if not s:
        return None
    # Try common Indian + ISO formats first, then pandas fallback
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y",
                "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except (ValueError, TypeError):
        return None


def to_amount(v: Any) -> float | None:
    """Strip currency symbols, commas, parentheses (= negative)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = _AMOUNT_STRIP.sub("", s)
    if not s:
        return None
    try:
        x = float(s)
        return -x if neg else x
    except ValueError:
        return None


def to_str(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


TRANSFORMS = {
    "date": to_date,
    "amount": to_amount,
    "string": to_str,
}
