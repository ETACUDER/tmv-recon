#!/usr/bin/env python3
"""Fetch FY25-26 daybook using the connector module."""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.connectors import day_book
from tmv_recon.config import TALLY_COMPANY

if __name__ == "__main__":
    print(f"Fetching daybook for FY25-26...")
    print(f"Company: {TALLY_COMPANY}")

    # Try shorter date ranges first to see what data exists
    date_ranges = [
        ("2025-04-01", "2025-06-30", "Q1_FY2526"),
        ("2025-07-01", "2025-09-30", "Q2_FY2526"),
        ("2025-10-01", "2025-12-31", "Q3_FY2526"),
        ("2026-01-01", "2026-03-31", "Q4_FY2526"),
    ]

    for from_date, to_date, label in date_ranges:
        try:
            print(f"\n{label}: {from_date} to {to_date}")
            df = day_book(from_date, to_date, TALLY_COMPANY)
            print(f"  Vouchers: {len(df):,}")

            if len(df) > 0:
                # Show summary
                print(f"  Types: {df['voucher_type'].value_counts().to_dict()}")
                print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

                # Show party ledgers used
                party_ledgers = df[df['party_ledger'] != '']['party_ledger'].value_counts()
                if len(party_ledgers) > 0:
                    print(f"  Top party ledgers:")
                    for ledger, count in party_ledgers.head(10).items():
                        print(f"    {ledger}: {count}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "="*60)
    print("Summary: Use connectors.day_book() to fetch data by quarter")
