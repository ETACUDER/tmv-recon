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
        "Net Amount", "Tax Amount", "Tax Amount.1", "Gross Amount",
        "Settlement Amount", "Discount Amount",
        "Adjustment(Room Charge/Extra Charges)",
    ]:
        sub[col] = pd.to_numeric(sub.get(col), errors="coerce").fillna(0.0)

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
        cgst=("Tax Amount", "sum"),
        sgst=("Tax Amount.1", "sum"),
        gross_amount=("Gross Amount", "sum"),
        discount=("Discount Amount", "sum"),
        adjustment=("Adjustment(Room Charge/Extra Charges)", "sum"),
        settlement_amount=("Settlement Amount", lambda s: float(s[s < 0].abs().sum())),
        settlement_mode=("Settlement/Particular", first_non_null),
    ).reset_index()
    grouped["earliest_pay_date"] = grouped["Invoice #"].map(earliest_pay)
    # bill_opens_with: "journal" if any payment Txn Date < Invoice date, else "sales"
    has_advance = grouped["earliest_pay_date"].notna() & (grouped["earliest_pay_date"] < grouped["invoice_date"])
    grouped["bill_opens_with"] = has_advance.map({True: "journal", False: "sales"})
    grouped["earliest_event_date"] = grouped[["invoice_date", "earliest_pay_date"]].min(axis=1)

    grouped["calc_gross"] = grouped["net_amount"] + grouped["cgst"] + grouped["sgst"]
    grouped["diff"] = (grouped["calc_gross"] - grouped["gross_amount"]).round(2)

    # EZee export quirk fix: some invoices have labelled CGST/SGST rates but
    # zero amounts, while Gross still includes the tax inline (e.g. invoices
    # 87/88/89 in Apr 2026: net 6666.66 + gross 6999.98, but tax columns 0).
    # When net+cgst+sgst < gross by >0.5, redistribute the missing tax as
    # cgst = sgst = (gross - net) / 2. Otherwise voucher won't balance.
    missing = (grouped["calc_gross"] - grouped["gross_amount"]).abs() > 0.5
    needs_fix = missing & (grouped["cgst"] + grouped["sgst"] < 0.5) & (grouped["gross_amount"] > grouped["net_amount"])
    if needs_fix.any():
        n = int(needs_fix.sum())
        half_tax = (grouped.loc[needs_fix, "gross_amount"] - grouped.loc[needs_fix, "net_amount"]) / 2
        grouped.loc[needs_fix, "cgst"] = half_tax.round(2)
        grouped.loc[needs_fix, "sgst"] = half_tax.round(2)
        grouped["calc_gross"] = grouped["net_amount"] + grouped["cgst"] + grouped["sgst"]
        grouped["diff"] = (grouped["calc_gross"] - grouped["gross_amount"]).round(2)
        print(f"  ! derived CGST/SGST from Gross-Net for {n} invoice(s) (EZee tax-amount zero quirk)")
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
