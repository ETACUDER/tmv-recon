#!/usr/bin/env python3
"""Test importing vouchers to Tally via HTTP API."""
import os
import sys
from pathlib import Path
import requests

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tmv_recon.config import TALLY_HOST, TALLY_PORT, TALLY_COMPANY


def import_voucher_xml(xml_file: Path) -> dict:
    """Import vouchers from XML file to Tally.

    Args:
        xml_file: Path to XML file with vouchers

    Returns:
        dict with status and response
    """
    url = f"http://{TALLY_HOST}:{TALLY_PORT}"

    # Read XML content
    xml_content = xml_file.read_text()

    print(f"\n{'='*60}")
    print(f"Importing: {xml_file.name}")
    print(f"URL: {url}")
    print(f"File size: {len(xml_content):,} bytes")
    print(f"{'='*60}\n")

    # Send to Tally
    headers = {
        'Content-Type': 'application/xml',
    }

    try:
        response = requests.post(
            url,
            data=xml_content.encode('utf-8'),
            headers=headers,
            timeout=30
        )

        print(f"Response Status: {response.status_code}")
        print(f"Response Length: {len(response.text)} bytes")

        # Check for Tally response patterns
        response_text = response.text.lower()

        if 'created' in response_text or 'imported' in response_text:
            status = 'SUCCESS'
        elif 'error' in response_text or 'failed' in response_text:
            status = 'ERROR'
        elif response.status_code == 200:
            status = 'SENT (check Tally for confirmation)'
        else:
            status = 'UNKNOWN'

        print(f"\nStatus: {status}")

        # Print first 500 chars of response
        if response.text:
            print(f"\nResponse Preview:")
            print(response.text[:500])
            if len(response.text) > 500:
                print("...")

        return {
            'status': status,
            'status_code': response.status_code,
            'response': response.text
        }

    except Exception as e:
        print(f"\nERROR: {e}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }


def main():
    """Test import with sample vouchers first, then full dataset."""

    # Test files
    test_files = [
        ROOT / "data/tally/generated/sample_sales_vouchers.xml",
        ROOT / "data/tally/generated/sample_journal_vouchers.xml",
    ]

    # Full files
    full_files = [
        ROOT / "data/tally/generated/sales_vouchers_oct2025.xml",
        ROOT / "data/tally/generated/journal_vouchers_oct2025.xml",
    ]

    print("\n" + "="*60)
    print("TALLY IMPORT TEST")
    print("="*60)
    print(f"Tally Server: {TALLY_HOST}:{TALLY_PORT}")
    print(f"Company: {TALLY_COMPANY}")

    # Step 1: Test with samples
    print("\n\n### STEP 1: Testing with SAMPLE vouchers ###\n")

    for xml_file in test_files:
        if xml_file.exists():
            result = import_voucher_xml(xml_file)

            if result['status'] == 'ERROR':
                print("\n⚠️  Sample import failed. Fix errors before importing full dataset.")
                return
        else:
            print(f"⚠️  File not found: {xml_file}")

    # Ask for confirmation before full import
    print("\n\n" + "="*60)
    print("Sample import complete. Ready for FULL dataset import?")
    print(f"  - Sales vouchers: 579 vouchers (542 KB)")
    print(f"  - Journal vouchers: 392 vouchers (218 KB)")
    print("="*60)

    response = input("\nProceed with full import? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\nFull import cancelled.")
        return

    # Step 2: Import full dataset
    print("\n\n### STEP 2: Importing FULL October 2025 dataset ###\n")

    for xml_file in full_files:
        if xml_file.exists():
            result = import_voucher_xml(xml_file)
        else:
            print(f"⚠️  File not found: {xml_file}")

    print("\n\n" + "="*60)
    print("Import complete! Please verify in Tally:")
    print("  1. Gateway → Display → Day Book")
    print("  2. Filter by date: 01-Oct-2025 to 31-Oct-2025")
    print("  3. Verify voucher counts match")
    print("="*60)


if __name__ == "__main__":
    main()
