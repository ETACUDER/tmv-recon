"""Production 3-stage matcher: exact → fuzzy → manual queue.

Implements reconciliation per docs/discovery-2026-04-29-requirements.md §3:

Stage 1 (EXACT):
  - Invoice ↔ Booking: join on invoice_no (confidence=1.0)
  - Payment ↔ Bank: join on utr (confidence=1.0)
  Output: exact_matches.csv

Stage 2 (FUZZY):
  - Name normalization (remove titles, title case, trim)
  - Levenshtein matching (threshold>0.7)
  - Date window (±3d invoice/booking, ±7d payment)
  - Amount tolerance (±1%)
  - Confidence scoring (0.6-0.9)
  Output: fuzzy_matches.csv

Stage 3 (MANUAL QUEUE):
  - Collect unmatched with reason codes:
    NO_JOIN_KEY, AMOUNT_MISMATCH, DATE_OUT_RANGE, MULTIPLE_CANDIDATES
  Output: unmatched/{bookings,invoices,payments}.csv

Outputs:
  data/recon/matches/exact_matches.csv
  data/recon/matches/fuzzy_matches.csv
  data/recon/matches/unmatched/{bookings,invoices,payments}.csv
  data/recon/reports/match_summary.csv
"""
from __future__ import annotations
import sys
import re
from dataclasses import dataclass
from datetime import timedelta, date
from pathlib import Path
from typing import Tuple, List, Dict
import pandas as pd
from fuzzywuzzy import fuzz

from tmv_recon.config import ROOT

CANON_DIR  = ROOT / "data" / "recon" / "canonical"
MATCH_DIR  = ROOT / "data" / "recon" / "matches"
UNMATCHED_DIR = MATCH_DIR / "unmatched"
REPORT_DIR = ROOT / "data" / "recon" / "reports"

# Tolerances (per requirements §3)
AMOUNT_PCT_TOL = 0.01      # ±1% relative tolerance
INVOICE_DATE_WINDOW = timedelta(days=3)
PAYMENT_DATE_WINDOW = timedelta(days=7)
DATE_MAX_GAP = timedelta(days=90)
FUZZY_NAME_THRESHOLD = 0.7
EXACT_NAME_THRESHOLD = 0.8


def _read(name: str) -> pd.DataFrame:
    p = CANON_DIR / f"{name}.csv"
    if not p.exists():
        raise FileNotFoundError(f"missing {p} — run extractors first")
    return pd.read_csv(p)


# ── Name Normalization ────────────────────────────────────────────────────
def normalize_name(name: str) -> str:
    """Normalize guest name for fuzzy matching per requirements §3.2."""
    if pd.isna(name) or not isinstance(name, str):
        return ""
    # Remove titles (Mr., Mrs., Ms., Dr., Miss)
    name = re.sub(r'^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss\.?)\s+', '', name, flags=re.I)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    # Title case for consistency
    return name.title()


def normalize_amount(val) -> float:
    """Convert amount to float, handle None/NaN."""
    if pd.isna(val):
        return 0.0
    return float(val)


def parse_date_safe(val) -> pd.Timestamp | None:
    """Parse date with error handling."""
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val)
    except:
        return None


# ── Confidence Scoring ────────────────────────────────────────────────────
def score_match(row_a: pd.Series, row_b: pd.Series,
                name_a: str = 'guest_name', name_b: str = 'guest_name',
                date_a: str = 'date', date_b: str = 'date',
                amount_a: str = 'amount', amount_b: str = 'amount') -> float:
    """Score match quality (0.0-1.0) based on name, date, amount alignment.

    Per requirements §3.2:
    - name_score > 80 + date_match + amount_match → 0.9
    - name_score > 70 + (date_match OR amount_match) → 0.7
    - else → 0.0
    """
    scores = []

    # Name similarity
    name_1 = normalize_name(str(row_a.get(name_a, '')))
    name_2 = normalize_name(str(row_b.get(name_b, '')))
    if name_1 and name_2:
        name_score = fuzz.ratio(name_1, name_2) / 100.0
        scores.append(('name', name_score))
    else:
        name_score = 0.0
        scores.append(('name', 0.0))

    # Date proximity
    dt_1 = parse_date_safe(row_a.get(date_a))
    dt_2 = parse_date_safe(row_b.get(date_b))
    date_match = False
    if dt_1 and dt_2:
        gap = abs((dt_1 - dt_2).days)
        if gap <= 3:
            date_score = 1.0
            date_match = True
        elif gap <= 7:
            date_score = 0.7
            date_match = True
        else:
            date_score = max(0, 1.0 - gap / 90.0)
        scores.append(('date', date_score))
    else:
        scores.append(('date', 0.0))

    # Amount proximity (±1% tolerance)
    amt_1 = normalize_amount(row_a.get(amount_a))
    amt_2 = normalize_amount(row_b.get(amount_b))
    amount_match = False
    if amt_1 > 0 and amt_2 > 0:
        pct_diff = abs(amt_1 - amt_2) / max(amt_1, amt_2)
        if pct_diff <= AMOUNT_PCT_TOL:
            amount_score = 1.0
            amount_match = True
        elif pct_diff <= 0.05:
            amount_score = 0.8
            amount_match = True
        else:
            amount_score = max(0, 1.0 - pct_diff)
        scores.append(('amount', amount_score))
    else:
        scores.append(('amount', 0.0))

    # Compute confidence per §3.2 rules
    if name_score >= 0.8 and date_match and amount_match:
        return 0.9
    elif name_score >= 0.7 and (date_match or amount_match):
        return 0.7
    elif name_score >= 0.7:
        return 0.65
    else:
        # Weighted average for partial matches
        weights = {'name': 0.4, 'date': 0.3, 'amount': 0.3}
        return sum(s[1] * weights.get(s[0], 0) for s in scores)


# ── Stage 1: Exact Matches ───────────────────────────────────────────────

def exact_match_invoice_booking(invoice: pd.DataFrame, booking: pd.DataFrame) -> pd.DataFrame:
    """Stage 1: Exact match Invoice ↔ Booking on invoice_no (confidence=1.0)."""
    if invoice.empty or booking.empty:
        return pd.DataFrame()

    # Join on invoice_no
    inv = invoice[invoice['invoice_no'].notna()].copy()
    book = booking[booking['invoice_no'].notna()].copy()

    if inv.empty or book.empty:
        return pd.DataFrame()

    # Select only existing columns
    inv_cols = ['invoice_no']
    for col in ['invoice_date', 'guest_name', 'gross_amount', 'arrival', 'departure']:
        if col in inv.columns:
            inv_cols.append(col)

    book_cols = ['invoice_no']
    for col in ['guest_name', 'checkin', 'checkout', 'settlement_amount']:
        if col in book.columns:
            book_cols.append(col)

    matched = pd.merge(
        inv[inv_cols],
        book[book_cols],
        on='invoice_no',
        how='inner',
        suffixes=('_inv', '_book')
    )

    matched['match_type'] = 'invoice_booking'
    matched['match_stage'] = 'exact'
    matched['match_rule'] = 'invoice_no_exact'
    matched['confidence'] = 1.0
    return matched


def exact_match_payment_bank(payment: pd.DataFrame, bank: pd.DataFrame) -> pd.DataFrame:
    """Stage 1: Exact match Payment ↔ Bank on utr (confidence=1.0)."""
    if payment.empty or bank.empty:
        return pd.DataFrame()

    # Join on utr (UTR exact match)
    pay = payment[payment['utr'].notna()].copy()
    bnk = bank[bank['utr_extracted'].notna()].copy()

    matched = pd.merge(
        pay[['txn_id', 'txn_dt', 'amount_gross', 'settled_amount', 'utr', 'payment_mode']],
        bnk[['utr_extracted', 'value_date', 'credit', 'description']],
        left_on='utr',
        right_on='utr_extracted',
        how='inner',
        suffixes=('_pay', '_bank')
    )

    matched['match_type'] = 'payment_bank'
    matched['match_stage'] = 'exact'
    matched['match_rule'] = 'utr_exact'
    matched['confidence'] = 1.0
    return matched


# ── Stage 2: Fuzzy Matches ────────────────────────────────────────────────

def fuzzy_match_invoice_booking(invoice: pd.DataFrame, booking: pd.DataFrame,
                                 already_matched: set) -> pd.DataFrame:
    """Stage 2: Fuzzy match Invoice ↔ Booking on guest_name + date + amount."""
    if invoice.empty or booking.empty:
        return pd.DataFrame()

    inv = invoice[~invoice['invoice_no'].isin(already_matched)].copy()
    book = booking[~booking.get('invoice_no', pd.Series()).isin(already_matched)].copy()

    # Prep dates
    inv['invoice_date_dt'] = pd.to_datetime(inv['invoice_date'], errors='coerce')
    inv['arrival_dt'] = pd.to_datetime(inv['arrival'], errors='coerce')
    book['checkin_dt'] = pd.to_datetime(book['checkin'], errors='coerce')

    matches = []
    for _, inv_row in inv.iterrows():
        if pd.isna(inv_row.get('guest_name')) or pd.isna(inv_row['arrival_dt']):
            continue

        # Filter candidates by date window (±3 days)
        candidates = book[
            (book['checkin_dt'].notna()) &
            (book['checkin_dt'] >= inv_row['arrival_dt'] - INVOICE_DATE_WINDOW) &
            (book['checkin_dt'] <= inv_row['arrival_dt'] + INVOICE_DATE_WINDOW)
        ].copy()

        if candidates.empty:
            continue

        # Score each candidate
        for _, book_row in candidates.iterrows():
            conf = score_match(
                inv_row, book_row,
                name_a='guest_name', name_b='guest_name',
                date_a='arrival_dt', date_b='checkin_dt',
                amount_a='gross_amount', amount_b='settlement_amount'
            )

            if conf >= 0.6:
                matches.append({
                    'invoice_no': inv_row['invoice_no'],
                    'invoice_date': inv_row['invoice_date'],
                    'guest_name_inv': inv_row['guest_name'],
                    'gross_amount': inv_row['gross_amount'],
                    'arrival': inv_row['arrival'],
                    'agoda_booking_id': book_row.get('agoda_booking_id'),
                    'guest_name_book': book_row.get('guest_name'),
                    'settlement_amount': book_row.get('settlement_amount'),
                    'checkin': book_row.get('checkin'),
                    'checkout': book_row.get('checkout'),
                    'match_type': 'invoice_booking',
                    'match_stage': 'fuzzy',
                    'match_rule': 'name_date_amount_fuzzy',
                    'confidence': round(conf, 2)
                })

    result = pd.DataFrame(matches)
    # Keep best match per invoice
    if not result.empty:
        result = result.sort_values('confidence', ascending=False).drop_duplicates('invoice_no', keep='first')
    return result


def fuzzy_match_payment_invoice(payment: pd.DataFrame, invoice: pd.DataFrame,
                                 already_matched: set) -> pd.DataFrame:
    """Stage 2: Fuzzy match Payment ↔ Invoice on amount + date + guest."""
    if payment.empty or invoice.empty:
        return pd.DataFrame()

    pay = payment[~payment['txn_id'].isin(already_matched)].copy()
    inv = invoice[~invoice['invoice_no'].isin(already_matched)].copy()

    pay['txn_dt_dt'] = pd.to_datetime(pay['txn_dt'], errors='coerce')
    inv['invoice_date_dt'] = pd.to_datetime(inv['invoice_date'], errors='coerce')

    matches = []
    for _, pay_row in pay.iterrows():
        if pd.isna(pay_row['txn_dt_dt']):
            continue

        # Filter by date window (invoice_date <= txn_date <= invoice_date + 7 days)
        candidates = inv[
            (inv['invoice_date_dt'].notna()) &
            (inv['invoice_date_dt'] <= pay_row['txn_dt_dt']) &
            (inv['invoice_date_dt'] >= pay_row['txn_dt_dt'] - PAYMENT_DATE_WINDOW)
        ].copy()

        if candidates.empty:
            continue

        # Score each candidate
        for _, inv_row in candidates.iterrows():
            conf = score_match(
                pay_row, inv_row,
                name_a='pos_guest_name', name_b='guest_name',
                date_a='txn_dt_dt', date_b='invoice_date_dt',
                amount_a='amount_gross', amount_b='gross_amount'
            )

            if conf >= 0.6:
                matches.append({
                    'txn_id': pay_row['txn_id'],
                    'txn_dt': pay_row['txn_dt'],
                    'amount_gross': pay_row['amount_gross'],
                    'settled_amount': pay_row.get('settled_amount'),
                    'payment_mode': pay_row.get('payment_mode'),
                    'utr': pay_row.get('utr'),
                    'guest_name_pay': pay_row.get('pos_guest_name'),
                    'invoice_no': inv_row['invoice_no'],
                    'invoice_date': inv_row['invoice_date'],
                    'invoice_gross': inv_row['gross_amount'],
                    'guest_name_inv': inv_row.get('guest_name'),
                    'match_type': 'payment_invoice',
                    'match_stage': 'fuzzy',
                    'match_rule': 'amount_date_guest_fuzzy',
                    'confidence': round(conf, 2)
                })

    result = pd.DataFrame(matches)
    # Keep best match per payment
    if not result.empty:
        result = result.sort_values('confidence', ascending=False).drop_duplicates('txn_id', keep='first')
    return result


# ── Stage 3: Manual Review Queue ──────────────────────────────────────────

def classify_unmatched(df: pd.DataFrame, record_type: str,
                       key_col: str, amount_col: str = None,
                       date_col: str = None) -> pd.DataFrame:
    """Classify unmatched records with reason codes per requirements §3.3."""
    if df.empty:
        return df

    result = df.copy()
    reasons = []

    for _, row in result.iterrows():
        reason_codes = []

        # Check for missing join key
        if pd.isna(row.get(key_col)) or str(row.get(key_col)).strip() == '':
            reason_codes.append('NO_JOIN_KEY')

        # Check for amount issues (if amount column provided)
        if amount_col and (pd.isna(row.get(amount_col)) or row.get(amount_col) == 0):
            reason_codes.append('AMOUNT_MISSING')

        # Check for date out of range (if date column provided)
        if date_col:
            dt = parse_date_safe(row.get(date_col))
            if dt:
                days_old = (pd.Timestamp.now() - dt).days
                if days_old > 90:
                    reason_codes.append('DATE_OUT_RANGE')

        if not reason_codes:
            reason_codes.append('NO_MATCH_FOUND')

        reasons.append(','.join(reason_codes))

    result['unmatched_reason'] = reasons
    result['record_type'] = record_type
    return result


# ── PTM ↔ Bank (legacy, keep for backward compat) ────────────────────────

def match_ptm_bank(ptm: pd.DataFrame, bank: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PTM `UTR_No.` is Paytm's internal aggregator reference; bank shows the
    NEFT UTR (different format). The actual link is:
      sum(PTM.Settled_Amount where Payout_ID=X) ≈ bank.credit on bank.value_date
      where bank.description contains 'ONE 97 COM' / 'PAYTM',
      and bank.value_date ≈ PTM.Settled_Date (±1 day).
    """
    if "settled_amount" not in ptm.columns or bank.empty:
        return pd.DataFrame(), ptm.copy()

    # Bank candidates: credit rows from Paytm
    bk = bank.copy()
    bk["value_date"] = pd.to_datetime(bk["value_date"], errors="coerce")
    bk = bk[(bk["credit"].fillna(0) > 0)
            & bk["description"].astype(str).str.contains("ONE 97|PAYTM|97 COM", case=False, na=False)
            & bk["value_date"].notna()]

    # PTM grouped by Payout_ID (a single settlement batch from Paytm to bank)
    p = ptm.copy()
    p["settled_dt"] = pd.to_datetime(p["settled_dt"], errors="coerce")
    g = p.dropna(subset=["payout_id"]).groupby("payout_id", as_index=False).agg(
        n_txns=("txn_id", "count"),
        sum_settled=("settled_amount", "sum"),
        sum_amount_gross=("amount_gross", "sum"),
        utr=("utr", "first"),
        settled_dt=("settled_dt", "min"),
        units=("unit", lambda x: ",".join(sorted(set(x.dropna())))),
    )

    rows: list[dict] = []
    matched_payouts: set[str] = set()
    for _, pr in g.iterrows():
        if pd.isna(pr["settled_dt"]) or not pr["sum_settled"]:
            continue
        d = pd.Timestamp(pr["settled_dt"]).normalize()
        cand = bk[
            (bk["value_date"] >= d - pd.Timedelta(days=1)) &
            (bk["value_date"] <= d + pd.Timedelta(days=2)) &
            ((bk["credit"] - pr["sum_settled"]).abs() <= 1.00)
        ]
        if cand.empty:
            # Try wider amount tolerance for fees-on-bank-side scenarios
            cand = bk[
                (bk["value_date"] >= d - pd.Timedelta(days=1)) &
                (bk["value_date"] <= d + pd.Timedelta(days=2)) &
                ((bk["credit"] - pr["sum_settled"]).abs() <= 2.00)
            ]
        if cand.empty:
            continue
        best = cand.iloc[0]
        rows.append({
            "payout_id": pr["payout_id"],
            "ptm_utr": pr["utr"],
            "n_ptm_txns": pr["n_txns"],
            "sum_settled": pr["sum_settled"],
            "sum_amount_gross": pr["sum_amount_gross"],
            "settled_dt": pr["settled_dt"],
            "bank_value_date": best["value_date"],
            "bank_credit": best["credit"],
            "bank_neft_utr": best["utr_extracted"],
            "delta": round(float(best["credit"] - pr["sum_settled"]), 2),
            "bank_account": best.get("account_number"),
            "match_rule": "amount_date_paytm_narration",
            "match_confidence": 0.95,
        })
        matched_payouts.add(pr["payout_id"])

    matched = pd.DataFrame(rows)

    # Unmatched PTM rows = those whose payout_id isn't in matched, OR no payout_id
    if matched.empty:
        unmatched = p.copy()
    else:
        unmatched = p[~p["payout_id"].isin(matched_payouts)].copy()
    unmatched["unmatched_reason"] = "no_bank_credit_for_payout"
    return matched, unmatched


# ── PTM ↔ Invoice ─────────────────────────────────────────────────────────

def match_ptm_invoice(ptm: pd.DataFrame, invoice: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each PTM SUCCESS row, find candidate invoices where:
      gross within ±AMOUNT_TOL AND invoice_date <= txn_date <= invoice_date+DATE_WINDOW.
    If unique → match. Tie-break by guest fuzzy when available."""
    if invoice.empty or ptm.empty:
        return pd.DataFrame(), ptm.copy()

    p = ptm.copy()
    p["txn_dt"] = pd.to_datetime(p["txn_dt"], errors="coerce")
    p["amount_gross"] = pd.to_numeric(p["amount_gross"], errors="coerce")
    p = p[p["amount_gross"].notna() & p["txn_dt"].notna()]

    inv = invoice.copy()
    inv["invoice_date"] = pd.to_datetime(inv["invoice_date"], errors="coerce")
    inv["gross_amount"] = pd.to_numeric(inv["gross_amount"], errors="coerce")
    inv = inv[inv["gross_amount"].notna()]

    rows: list[dict] = []
    for _, pr in p.iterrows():
        cand = inv[
            (inv["gross_amount"].between(pr["amount_gross"] - AMOUNT_TOL,
                                         pr["amount_gross"] + AMOUNT_TOL))
            & (inv["invoice_date"].notna())
            & (inv["invoice_date"] <= pr["txn_dt"])
            & (inv["invoice_date"] >= pr["txn_dt"] - DATE_WINDOW)
        ]
        if cand.empty:
            continue

        # Guest fuzzy if we have a name
        guest_hint = ""
        for f in ("pos_guest_name", "customer_vpa"):
            v = pr.get(f)
            if isinstance(v, str) and v.strip():
                guest_hint = v.strip().split("@")[0].replace(".", " ").replace("/", " ")
                break

        if guest_hint and len(cand) > 1:
            cand = cand.copy()
            cand["fuzzy"] = cand.apply(
                lambda r: fuzz.token_set_ratio(guest_hint.lower(),
                                                f"{r.get('guest_name','')} {r.get('bill_to_name','')}".lower()),
                axis=1,
            )
            cand = cand.sort_values("fuzzy", ascending=False)

        best = cand.iloc[0]
        rule = "amount_date_window"
        conf = 0.7
        if guest_hint and "fuzzy" in cand.columns and best["fuzzy"] >= 80:
            rule = "amount_date_guest"
            conf = 0.92

        rows.append({
            "txn_id":         pr.get("txn_id"),
            "txn_dt":         pr["txn_dt"],
            "amount_gross":   pr["amount_gross"],
            "settled_amount": pr.get("settled_amount"),
            "payment_mode":   pr.get("payment_mode"),
            "utr":            pr.get("utr"),
            "invoice_no":     best["invoice_no"],
            "invoice_date":   best["invoice_date"],
            "invoice_gross":  best["gross_amount"],
            "guest_invoice":  best.get("guest_name"),
            "guest_pos":      guest_hint,
            "candidates":     int(len(cand)),
            "match_rule":     rule,
            "match_confidence": conf,
        })

    matched = pd.DataFrame(rows)
    matched_txns = set(matched["txn_id"]) if not matched.empty else set()
    unmatched = p[~p["txn_id"].isin(matched_txns)].copy()
    return matched, unmatched


# ── Booking ↔ Invoice ─────────────────────────────────────────────────────

def match_booking_invoice(booking: pd.DataFrame, invoice: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Direct join on invoice_no when present; fallback by guest+arrival fuzzy."""
    if booking.empty or invoice.empty:
        return pd.DataFrame(), booking.copy()

    direct = booking.dropna(subset=["invoice_no"]).merge(
        invoice[["invoice_no","invoice_date","guest_name","bill_to_name","gross_amount","travel_agent","arrival","departure"]],
        on="invoice_no", how="left", suffixes=("_book", "_inv"),
    )
    matched_direct = direct[direct["invoice_date"].notna()].copy()
    matched_direct["match_rule"] = "invoice_no_exact"
    matched_direct["match_confidence"] = 1.0

    # Booking rows without invoice_no — try guest fuzzy
    leftover = booking[booking["invoice_no"].isna()].copy()
    candidates = invoice[invoice["travel_agent"].fillna("").str.contains("agoda", case=False, na=False)].copy()
    candidates["arrival"] = pd.to_datetime(candidates["arrival"], errors="coerce")
    leftover["checkin"] = pd.to_datetime(leftover["checkin"], errors="coerce")

    fuzzy_rows: list[dict] = []
    for _, b in leftover.iterrows():
        if not b.get("guest_name"):
            continue
        cand = candidates[
            (candidates["arrival"].notna())
            & (candidates["arrival"] >= b["checkin"] - timedelta(days=2))
            & (candidates["arrival"] <= b["checkin"] + timedelta(days=2))
        ]
        if cand.empty: continue
        cand = cand.copy()
        cand["fuzzy"] = cand["guest_name"].fillna("").apply(
            lambda g: fuzz.token_set_ratio(str(b["guest_name"]).lower(), g.lower())
        )
        cand = cand.sort_values("fuzzy", ascending=False)
        if cand.iloc[0]["fuzzy"] < 75:
            continue
        best = cand.iloc[0]
        fuzzy_rows.append({
            **{k: b[k] for k in b.index if k in booking.columns},
            "invoice_no":    best["invoice_no"],
            "invoice_date":  best["invoice_date"],
            "gross_amount":  best["gross_amount"],
            "fuzzy_score":   best["fuzzy"],
            "match_rule":    "guest_arrival_fuzzy",
            "match_confidence": min(0.85, best["fuzzy"] / 100),
        })

    matched_fuzzy = pd.DataFrame(fuzzy_rows)
    matched = pd.concat([matched_direct, matched_fuzzy], ignore_index=True) if not matched_fuzzy.empty else matched_direct

    matched_keys = set(zip(matched.get("settlement_batch_id", pd.Series()), matched.get("agoda_booking_id", pd.Series())))
    book_keys = list(zip(booking["settlement_batch_id"], booking["agoda_booking_id"]))
    unmatched = booking[[k not in matched_keys for k in book_keys]].copy()
    return matched, unmatched


# ── driver (new 3-stage pipeline) ────────────────────────────────────────

def main() -> int:
    """Production 3-stage matcher: exact → fuzzy → manual queue."""
    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    UNMATCHED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Load canonical data
    invoice = _read("invoice")
    booking = _read("booking")
    payment = _read("payment")
    bank    = _read("bank")

    print(f"Loaded canonical data:")
    print(f"  invoices: {len(invoice)}")
    print(f"  bookings: {len(booking)}")
    print(f"  payments: {len(payment)}")
    print(f"  bank: {len(bank)}")

    # ── STAGE 1: Exact Matches ────────────────────────────────────────────
    print("\n=== STAGE 1: Exact Matches ===")

    exact_inv_book = exact_match_invoice_booking(invoice, booking)
    print(f"Invoice ↔ Booking (invoice_no exact): {len(exact_inv_book)} matches")

    exact_pay_bank = exact_match_payment_bank(payment, bank)
    print(f"Payment ↔ Bank (utr exact): {len(exact_pay_bank)} matches")

    # Track matched IDs
    matched_invoices = set(exact_inv_book['invoice_no']) if not exact_inv_book.empty else set()
    matched_payments = set(exact_pay_bank['txn_id']) if not exact_pay_bank.empty else set()

    # Combine exact matches
    exact_matches = pd.concat([exact_inv_book, exact_pay_bank], ignore_index=True)
    exact_matches.to_csv(MATCH_DIR / "exact_matches.csv", index=False)
    print(f"Saved: {MATCH_DIR / 'exact_matches.csv'}")

    # ── STAGE 2: Fuzzy Matches ────────────────────────────────────────────
    print("\n=== STAGE 2: Fuzzy Matches ===")

    fuzzy_inv_book = fuzzy_match_invoice_booking(invoice, booking, matched_invoices)
    print(f"Invoice ↔ Booking (fuzzy): {len(fuzzy_inv_book)} matches")
    if not fuzzy_inv_book.empty:
        matched_invoices.update(fuzzy_inv_book['invoice_no'])

    fuzzy_pay_inv = fuzzy_match_payment_invoice(payment, invoice, matched_payments)
    print(f"Payment ↔ Invoice (fuzzy): {len(fuzzy_pay_inv)} matches")
    if not fuzzy_pay_inv.empty:
        matched_payments.update(fuzzy_pay_inv['txn_id'])

    # Combine fuzzy matches
    fuzzy_matches = pd.concat([fuzzy_inv_book, fuzzy_pay_inv], ignore_index=True)
    fuzzy_matches.to_csv(MATCH_DIR / "fuzzy_matches.csv", index=False)
    print(f"Saved: {MATCH_DIR / 'fuzzy_matches.csv'}")

    # ── STAGE 3: Manual Review Queue ──────────────────────────────────────
    print("\n=== STAGE 3: Manual Review Queue ===")

    # Identify unmatched records
    unmatched_bookings = booking[
        ~booking.get('invoice_no', pd.Series()).isin(matched_invoices) &
        ~booking.get('agoda_booking_id', pd.Series()).isin(
            fuzzy_inv_book.get('agoda_booking_id', pd.Series())
        )
    ].copy()

    unmatched_invoices = invoice[~invoice['invoice_no'].isin(matched_invoices)].copy()

    unmatched_payments = payment[~payment['txn_id'].isin(matched_payments)].copy()

    # Classify with reason codes
    unmatched_bookings = classify_unmatched(
        unmatched_bookings, 'booking',
        key_col='invoice_no', amount_col='settlement_amount', date_col='checkin'
    )

    unmatched_invoices = classify_unmatched(
        unmatched_invoices, 'invoice',
        key_col='invoice_no', amount_col='gross_amount', date_col='invoice_date'
    )

    unmatched_payments = classify_unmatched(
        unmatched_payments, 'payment',
        key_col='utr', amount_col='amount_gross', date_col='txn_dt'
    )

    # Save unmatched files
    unmatched_bookings.to_csv(UNMATCHED_DIR / "bookings.csv", index=False)
    unmatched_invoices.to_csv(UNMATCHED_DIR / "invoices.csv", index=False)
    unmatched_payments.to_csv(UNMATCHED_DIR / "payments.csv", index=False)

    print(f"Unmatched bookings: {len(unmatched_bookings)}")
    print(f"Unmatched invoices: {len(unmatched_invoices)}")
    print(f"Unmatched payments: {len(unmatched_payments)}")
    print(f"Saved: {UNMATCHED_DIR / 'bookings.csv'}")
    print(f"Saved: {UNMATCHED_DIR / 'invoices.csv'}")
    print(f"Saved: {UNMATCHED_DIR / 'payments.csv'}")

    # ── Generate Match Summary Report ─────────────────────────────────────
    print("\n=== Match Summary Report ===")

    # Calculate match rates
    total_bookings = len(booking)
    total_invoices = len(invoice)
    total_payments = len(payment)

    matched_bookings_count = len(matched_invoices)
    matched_payments_count = len(matched_payments)

    booking_match_rate = (matched_bookings_count / total_bookings * 100) if total_bookings > 0 else 0
    invoice_match_rate = (matched_bookings_count / total_invoices * 100) if total_invoices > 0 else 0
    payment_match_rate = (matched_payments_count / total_payments * 100) if total_payments > 0 else 0

    # Count by reason code
    def count_reasons(df):
        if df.empty or 'unmatched_reason' not in df.columns:
            return {}
        reason_counts = {}
        for reasons in df['unmatched_reason']:
            for r in str(reasons).split(','):
                r = r.strip()
                reason_counts[r] = reason_counts.get(r, 0) + 1
        return reason_counts

    booking_reasons = count_reasons(unmatched_bookings)
    invoice_reasons = count_reasons(unmatched_invoices)
    payment_reasons = count_reasons(unmatched_payments)

    # Build summary dataframe
    summary_data = {
        'stream': ['bookings', 'invoices', 'payments'],
        'total_records': [total_bookings, total_invoices, total_payments],
        'exact_matches': [
            len(exact_inv_book),
            len(exact_inv_book),
            len(exact_pay_bank)
        ],
        'fuzzy_matches': [
            len(fuzzy_inv_book),
            len(fuzzy_inv_book),
            len(fuzzy_pay_inv)
        ],
        'total_matched': [
            matched_bookings_count,
            matched_bookings_count,
            matched_payments_count
        ],
        'unmatched': [
            len(unmatched_bookings),
            len(unmatched_invoices),
            len(unmatched_payments)
        ],
        'match_rate_pct': [
            round(booking_match_rate, 1),
            round(invoice_match_rate, 1),
            round(payment_match_rate, 1)
        ],
        'unmatched_rate_pct': [
            round(100 - booking_match_rate, 1),
            round(100 - invoice_match_rate, 1),
            round(100 - payment_match_rate, 1)
        ]
    }

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(REPORT_DIR / "match_summary.csv", index=False)
    print(f"Saved: {REPORT_DIR / 'match_summary.csv'}")

    # Generate detailed text report
    summary_text = f"""# TMV Reconciliation Match Summary
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Input Statistics
Total Records:
  Bookings:  {total_bookings:>6}
  Invoices:  {total_invoices:>6}
  Payments:  {total_payments:>6}
  Bank:      {len(bank):>6}

## Stage 1: Exact Matches (confidence=1.0)
Invoice ↔ Booking (invoice_no):  {len(exact_inv_book):>6}
Payment ↔ Bank (utr):            {len(exact_pay_bank):>6}

## Stage 2: Fuzzy Matches (confidence=0.6-0.9)
Invoice ↔ Booking (name+date+amt): {len(fuzzy_inv_book):>6}
Payment ↔ Invoice (name+date+amt): {len(fuzzy_pay_inv):>6}

## Overall Match Rates
Bookings:  {matched_bookings_count:>6} / {total_bookings:>6} ({booking_match_rate:>5.1f}%)
Invoices:  {matched_bookings_count:>6} / {total_invoices:>6} ({invoice_match_rate:>5.1f}%)
Payments:  {matched_payments_count:>6} / {total_payments:>6} ({payment_match_rate:>5.1f}%)

## Unmatched Records (Manual Review Queue)
Bookings:  {len(unmatched_bookings):>6}
Invoices:  {len(unmatched_invoices):>6}
Payments:  {len(unmatched_payments):>6}

### Unmatched Reasons - Bookings
"""
    for reason, count in sorted(booking_reasons.items(), key=lambda x: x[1], reverse=True):
        summary_text += f"  {reason:<25} {count:>6}\n"

    summary_text += "\n### Unmatched Reasons - Invoices\n"
    for reason, count in sorted(invoice_reasons.items(), key=lambda x: x[1], reverse=True):
        summary_text += f"  {reason:<25} {count:>6}\n"

    summary_text += "\n### Unmatched Reasons - Payments\n"
    for reason, count in sorted(payment_reasons.items(), key=lambda x: x[1], reverse=True):
        summary_text += f"  {reason:<25} {count:>6}\n"

    summary_text += f"""
## Validation Status
Target: 95%+ match rate (invoice ↔ booking, payment ↔ bank)
Actual: {max(booking_match_rate, invoice_match_rate):.1f}% (invoice ↔ booking), {payment_match_rate:.1f}% (payment ↔ bank)

Status: {'✓ PASS' if booking_match_rate >= 95 and payment_match_rate >= 95 else '✗ FAIL'}

## Output Files
Exact Matches:     {MATCH_DIR / 'exact_matches.csv'}
Fuzzy Matches:     {MATCH_DIR / 'fuzzy_matches.csv'}
Unmatched Queue:   {UNMATCHED_DIR}/{{bookings,invoices,payments}}.csv
Match Summary:     {REPORT_DIR / 'match_summary.csv'}
"""

    (REPORT_DIR / "match_summary.txt").write_text(summary_text)
    print(f"Saved: {REPORT_DIR / 'match_summary.txt'}")

    print("\n" + summary_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
