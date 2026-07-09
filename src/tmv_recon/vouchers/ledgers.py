"""All Tally ledger names + mappings used by the voucher pipeline.

Single source of truth — if you rename a ledger in Tally Master, update
the corresponding string here once and re-run the emitters.

Ledger names MUST match Tally Master byte-for-byte (whitespace and
punctuation included). Tally's import error log strips whitespace when
displaying mismatches, so the byte content matters but the displayed
error may not.
"""
from __future__ import annotations

import json
from pathlib import Path

# ----- Default party ledger (receivables) -----
SUNDRY_DEBTORS = "Sundry Debtors"

# ----- Sales income ledgers, keyed by GST rate (0-100) -----
# Note quirky spacing: only the 5% variant has spaces both sides of '%'.
SALES_LEDGER_BY_GST_RATE: dict[int, str] = {
    5: "SALE ACCOMODATION GST @ 5 %",
    12: "SALE ACCOMODATION GST @ 12%",
    18: "SALE ACCOMODATION GST @ 18%",
}
DEFAULT_SALES_LEDGER = "SALE ACCOMODATION GST @ 12%"

# ----- GST output tax ledgers -----
CGST = "CGST"
SGST = "SGST"

# ----- Round Off (gain or loss on bill rounding) -----
ROUND_OFF = "ROUND OFF"

# ----- Payment ledgers (mode -> ledger), keyed by uppercased trimmed EZee mode -----
PAYMENT_LEDGER_BY_MODE: dict[str, str] = {
    "CASH": "SANDEEP SHARMA IMP A/C.",
    "UPI": "CARD / UPI / PAYTM / G PAY",
    "CREDIT CARD": "CARD / UPI / PAYTM / G PAY",
    "DEBIT CARD": "CARD / UPI / PAYTM / G PAY",
    "AGODA": "AGODA SDR",
    "BOOKING.COM": "BOOKING.COM SDR",
    "GOIBIBO": "GOIBIBO / MAKE MY TRIP",
}

# Ledgers that need a "New Ref" bill allocation on the Dr side of a
# Journal voucher. These are bill-wise tracked control accounts where a
# fresh receivable opens against the platform.
# (Cash → SANDEEP SHARMA IMP A/C. is deliberately excluded: its master
# has bill-wise off, so any bill allocation would be ignored anyway.)
NEW_REF_LEDGERS: set[str] = {
    "AGODA SDR",
    "BOOKING.COM SDR",
    "GOIBIBO / MAKE MY TRIP",
    "CARD / UPI / PAYTM / G PAY",
}


def pick_sales_ledger(net: float, cgst: float, sgst: float) -> str:
    """Pick the right SALE ACCOMODATION GST ledger by inferred rate."""
    if net <= 0:
        return DEFAULT_SALES_LEDGER
    rate = round(((cgst + sgst) / net) * 100)
    if rate >= 17:
        return SALES_LEDGER_BY_GST_RATE[18]
    if rate >= 11:
        return SALES_LEDGER_BY_GST_RATE[12]
    return SALES_LEDGER_BY_GST_RATE[5]


# ----- Accountant-added overrides (self-service; extends the built-in map) -----
# JSON at data/recon/hotel_payment_ledgers.json, e.g.
#   {"CLEARTRIP": {"ledger": "CLEAR TRIP SDR", "new_ref": true},
#    "BANK TRANSFER": {"ledger": "INDIAN BANK CARD", "new_ref": true}}
# so a new EZee settlement mode can be mapped from the wizard, no code change.
import os as _os
_DATA_BASE = _os.environ.get("TMV_DATA_DIR") or str(Path(__file__).resolve().parents[3] / "data")
OVERRIDES_PATH = Path(_DATA_BASE) / "recon" / "hotel_payment_ledgers.json"
PAYMENT_LEDGER_OVERRIDES: dict[str, dict] = {}


def reload_payment_overrides() -> dict:
    """Reload accountant overrides from disk (called at import + after an add)."""
    global PAYMENT_LEDGER_OVERRIDES
    try:
        raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
        PAYMENT_LEDGER_OVERRIDES = {k.strip().upper(): v for k, v in raw.items()}
    except (OSError, ValueError):
        PAYMENT_LEDGER_OVERRIDES = {}
    for v in PAYMENT_LEDGER_OVERRIDES.values():
        if v.get("new_ref", True):
            NEW_REF_LEDGERS.add(v["ledger"])
    return PAYMENT_LEDGER_OVERRIDES


reload_payment_overrides()


def _prefix_match(key: str, table: dict) -> str | None:
    """Match a mode against table keys as a prefix, at a clean boundary.
    Handles EZee modes with a booking-id suffix like 'CLEARTRIP-425340'."""
    for k, v in table.items():
        if key.startswith(k) and (len(key) == len(k) or not key[len(k)].isalnum()):
            return v["ledger"] if isinstance(v, dict) else v
    return None


def pick_payment_ledger(mode: str) -> str | None:
    """Return target Tally ledger for an EZee settlement mode; None if unmapped.
    Order: exact override → exact built-in → prefix override → prefix built-in."""
    key = (mode or "").strip().upper()
    if not key:
        return None
    if key in PAYMENT_LEDGER_OVERRIDES:
        return PAYMENT_LEDGER_OVERRIDES[key]["ledger"]
    if key in PAYMENT_LEDGER_BY_MODE:
        return PAYMENT_LEDGER_BY_MODE[key]
    return _prefix_match(key, PAYMENT_LEDGER_OVERRIDES) or _prefix_match(key, PAYMENT_LEDGER_BY_MODE)
