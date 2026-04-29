#!/usr/bin/env python3
"""Check what companies are available on Tally."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.connectors import list_companies, current_company

if __name__ == "__main__":
    print("Checking Tally companies...\n")

    try:
        current = current_company()
        print(f"Current company: {current}\n")
    except Exception as e:
        print(f"Error getting current company: {e}\n")

    try:
        companies = list_companies()
        print(f"Available companies ({len(companies)}):")
        for idx, row in companies.iterrows():
            print(f"  {idx+1}. {row['name']}")
            if 'starting_from' in row and row['starting_from']:
                print(f"     Starting from: {row['starting_from']}")
    except Exception as e:
        print(f"Error listing companies: {e}")
