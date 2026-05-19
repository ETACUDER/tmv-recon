#!/usr/bin/env python3
"""Aggregate raw EZee Transaction Detail Report into canonical monthly invoice CSV.

Groups transaction-level rows by Invoice # for a chosen month and emits a CSV
with the schema matching `data/recon/canonical/invoice_oct2025_corrected.csv`.

Usage:
    python scripts/aggregate_invoices_monthly.py \
        --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
        --month 2026-04 \
        --out data/recon/canonical/invoice_apr2026.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


CANON_COLS = [
    "invoice_no_normalized", "Invoice date", "Invoice #", "Guest Name",
    "Room Type", "Travel Agent", "Business Source",
    "Net Amount", "Tax Amount", "Tax Amount.1", "Gross Amount",
    "Discount Amount", "Adjustment", "Total Payable",
    "settlement_amount_abs", "Settlement/Particular",
    "earliest_event_date", "bill_opens_with",
    "calc_gross", "diff",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True, help="Path to raw EZee xlsx")
    p.add_argument("--month", required=True, help="YYYY-MM month filter on Invoice date")
    p.add_argument("--out", required=True, help="Output canonical CSV path")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    raw = Path(a.raw)
    if not raw.exists():
        raise SystemExit(f"raw file not found: {raw}")

    df = pd.read_excel(raw, header=0)
    df.columns = [str(c).strip() for c in df.columns]

    df["_d"] = pd.to_datetime(df["Invoice date"], errors="coerce")
    start = pd.Timestamp(a.month + "-01")
    end = (start + pd.offsets.MonthBegin(1))
    sub = df[(df["_d"] >= start) & (df["_d"] < end)].copy()
    sub = sub[sub["Invoice #"].notna()]

    for col in [
        "Net Amount", "Gross Amount", "Settlement Amount", "Discount Amount",
        "Adjustment(Room Charge/Extra Charges)",
    ]:
        sub[col] = pd.to_numeric(sub.get(col), errors="coerce").fillna(0.0)

    # EZee exports up to 4 (Tax Name, Tax %, Tax Amount) triples per row.
    # When invoices are edited, the tax can move from .0/.1 to .2/.3.
    # Sum per-row tax amounts into row-level CGST/SGST/IGST buckets using
    # the Tax Name label to allocate.
    tax_pairs = []
    for suf in ("", ".1", ".2", ".3"):
        name_col, amt_col = f"Tax Name{suf}", f"Tax Amount{suf}"
        if name_col in sub.columns and amt_col in sub.columns:
            tax_pairs.append((name_col, amt_col))

    def _bucket(row: pd.Series) -> tuple[float, float, float]:
        cgst = sgst = igst = 0.0
        for name_col, amt_col in tax_pairs:
            label = str(row.get(name_col) or "").upper()
            amt = pd.to_numeric(row.get(amt_col), errors="coerce")
            if pd.isna(amt) or amt == 0:
                continue
            if "CGST" in label: cgst += float(amt)
            elif "SGST" in label: sgst += float(amt)
            elif "IGST" in label: igst += float(amt)
        return cgst, sgst, igst

    tax_rows = sub.apply(_bucket, axis=1, result_type="expand")
    tax_rows.columns = ["_cgst", "_sgst", "_igst"]
    sub = pd.concat([sub, tax_rows], axis=1)

    def first_non_null(s: pd.Series) -> str:
        for v in s:
            if pd.notna(v) and str(v).strip():
                return str(v).strip()
        return ""

    # Pre-compute earliest payment-row Transaction Date per invoice (advance receipts).
    pay = sub[
        (sub["Settlement Amount"] != 0)
        & (sub["Settlement/Particular"].notna())
        & (sub["Settlement/Particular"].astype(str).str.strip() != "")
    ].copy()
    pay["_pdate"] = pd.to_datetime(pay.get("Transaction Date"), errors="coerce")
    earliest_pay = pay.groupby("Invoice #")["_pdate"].min()

    grouped = sub.groupby("Invoice #", sort=False).agg(
        invoice_date=("_d", "first"),
        guest_name=("Guest Name", first_non_null),
        room_type=("Room Type", first_non_null),
        travel_agent=("Travel Agent", first_non_null),
        business_source=("Business Source", first_non_null),
        net_amount=("Net Amount", "sum"),
        # Sum the LABEL-categorised tax buckets across all 4 EZee tax columns,
        # not just Tax Amount / Tax Amount.1.
        cgst=("_cgst", "sum"),
        sgst=("_sgst", "sum"),
        igst=("_igst", "sum"),
        gross_amount=("Gross Amount", "sum"),
        discount=("Discount Amount", "sum"),
        adjustment=("Adjustment(Room Charge/Extra Charges)", "sum"),
        settlement_amount=("Settlement Amount", lambda s: float(s[s < 0].abs().sum())),
        settlement_mode=("Settlement/Particular", first_non_null),
    ).reset_index()
    if grouped["igst"].sum() > 0.5:
        print(f"  ! IGST detected on {(grouped['igst']>0.5).sum()} invoices "
              f"(₹{grouped['igst'].sum():,.2f}) — emitter currently only "
              f"handles CGST+SGST; review before importing.")
    grouped["earliest_pay_date"] = grouped["Invoice #"].map(earliest_pay)
    # bill_opens_with: "journal" if any payment Txn Date < Invoice date, else "sales"
    has_advance = grouped["earliest_pay_date"].notna() & (grouped["earliest_pay_date"] < grouped["invoice_date"])
    grouped["bill_opens_with"] = has_advance.map({True: "journal", False: "sales"})
    grouped["earliest_event_date"] = grouped[["invoice_date", "earliest_pay_date"]].min(axis=1)

    grouped["calc_gross"] = grouped["net_amount"] + grouped["cgst"] + grouped["sgst"] + grouped["igst"]
    grouped["diff"] = (grouped["calc_gross"] - grouped["gross_amount"]).round(2)
    # Total Payable: what the customer actually owes after discount/adjustment.
    # Drives Sundry Debtors AMOUNT and bill-allocation face value on Sales voucher.
    grouped["total_payable"] = (
        grouped["gross_amount"] - grouped["discount"] - grouped["adjustment"]
    ).round(2)

    out = pd.DataFrame({
        "invoice_no_normalized": grouped["Invoice #"].astype(str),
        "Invoice date": grouped["invoice_date"].dt.strftime("%Y-%m-%d"),
        "Invoice #": grouped["Invoice #"].astype(str),
        "Guest Name": grouped["guest_name"],
        "Room Type": grouped["room_type"],
        "Travel Agent": grouped["travel_agent"],
        "Business Source": grouped["business_source"],
        "Net Amount": grouped["net_amount"].round(2),
        "Tax Amount": grouped["cgst"].round(2),
        "Tax Amount.1": grouped["sgst"].round(2),
        "Gross Amount": grouped["gross_amount"].round(2),
        "Discount Amount": grouped["discount"].round(2),
        "Adjustment": grouped["adjustment"].round(2),
        "Total Payable": grouped["total_payable"],
        "settlement_amount_abs": grouped["settlement_amount"].round(2),
        "Settlement/Particular": grouped["settlement_mode"],
        "earliest_event_date": grouped["earliest_event_date"].dt.strftime("%Y-%m-%d"),
        "bill_opens_with": grouped["bill_opens_with"],
        "calc_gross": grouped["calc_gross"].round(2),
        "diff": grouped["diff"],
    })[CANON_COLS]

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False)

    total = out["Gross Amount"].sum()
    valid = (out["Gross Amount"] > 0).sum()
    mismatch = (out["diff"].abs() > 0.5).sum()
    print(f"wrote {a.out}")
    print(f"  invoices: {len(out)}  valid (gross>0): {valid}  zero/neg: {len(out)-valid}")
    print(f"  sum Gross: {total:,.2f}")
    print(f"  internal mismatches (|net+cgst+sgst-gross|>0.5): {mismatch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
