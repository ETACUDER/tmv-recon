#!/usr/bin/env python3
"""Fetch FY 2024-25 daybook."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.connectors import day_book
from tmv_recon.config import TALLY_COMPANY

if __name__ == "__main__":
    print(f"Fetching FY 2024-25 (Apr 2024 to Mar 2025)")
    print(f"Company: {TALLY_COMPANY}\n")

    quarters = [
        ("2024-04-01", "2024-06-30", "Q1"),
        ("2024-07-01", "2024-09-30", "Q2"),
        ("2024-10-01", "2024-12-31", "Q3"),
        ("2025-01-01", "2025-03-31", "Q4"),
    ]

    total_vouchers = 0
    for from_date, to_date, label in quarters:
        try:
            df = day_book(from_date, to_date, TALLY_COMPANY)
            print(f"{label}: {len(df):,} vouchers")
            if len(df) > 0:
                types = df['voucher_type'].value_counts().to_dict()
                print(f"  Types: {types}")
                total_vouchers += len(df)
        except Exception as e:
            print(f"{label}: Error - {e}")

    print(f"\nTotal FY 2024-25: {total_vouchers:,} vouchers")
