#!/usr/bin/env python3
"""Extract payment rows from raw EZee Transaction Detail Report → canonical CSV.

One CSV row per payment line (an invoice may have multiple if split-paid).

Usage:
    python scripts/extract_payments_monthly.py \
        --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
        --month 2026-04 \
        --out data/recon/canonical/payment_apr2026.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

CANON_COLS = [
    "Invoice #", "Invoice date", "Guest Name",
    "Settlement/Particular", "Settlement Amount", "Reference #",
    "Transaction Date",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--month", required=True, help="YYYY-MM filter on Invoice date")
    p.add_argument("--out", required=True)
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
    end = start + pd.offsets.MonthBegin(1)
    sub = df[(df["_d"] >= start) & (df["_d"] < end)].copy()
    sub = sub[sub["Invoice #"].notna()]

    # Payment rows: Settlement Amount != 0 and Settlement/Particular not blank
    sub["Settlement Amount"] = pd.to_numeric(sub["Settlement Amount"], errors="coerce").fillna(0.0)
    pay = sub[
        (sub["Settlement Amount"] != 0.0)
        & (sub["Settlement/Particular"].notna())
        & (sub["Settlement/Particular"].astype(str).str.strip() != "")
    ].copy()

    out = pd.DataFrame({
        "Invoice #": pay["Invoice #"].astype(str),
        "Invoice date": pay["_d"].dt.strftime("%Y-%m-%d"),
        "Guest Name": pay["Guest Name"].fillna("").astype(str),
        "Settlement/Particular": pay["Settlement/Particular"].astype(str).str.strip(),
        # EZee sign: negative = collection (money in), positive = refund/reversal.
        # Negate so a collection is +ve and a refund is -ve — the sign is meaning,
        # not noise, and must survive to the journal (a dropped sign turns a refund
        # into a phantom over-collection).
        "Settlement Amount": (-pay["Settlement Amount"]).round(2),
        "Reference #": pay.get("Reference #", "").fillna("").astype(str),
        "Transaction Date": pd.to_datetime(pay.get("Transaction Date"), errors="coerce").dt.strftime("%Y-%m-%d").fillna(""),
    })[CANON_COLS]

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False)

    total = out["Settlement Amount"].sum()
    refunds = int((out["Settlement Amount"] < 0).sum())
    by_mode = out.groupby("Settlement/Particular").agg(count=("Invoice #","count"), amt=("Settlement Amount","sum"))
    print(f"wrote {a.out}")
    print(f"  payment rows: {len(out)}  unique invoices: {out['Invoice #'].nunique()}  refund/reversal rows: {refunds}")
    print(f"  net settlement (signed): {total:,.2f}")
    print(f"  by mode:")
    for mode, row in by_mode.iterrows():
        print(f"    {mode:<20} {int(row['count']):>4}  ₹{row['amt']:>14,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
