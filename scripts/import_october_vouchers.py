#!/usr/bin/env python3
"""Import October 2025 vouchers to Tally in batches."""
import os
import sys
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
from typing import List

# Add src to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tmv_recon.config import TALLY_HOST, TALLY_PORT, TALLY_COMPANY


def split_vouchers_into_batches(xml_file: Path, batch_size: int = 100) -> List[str]:
    """Split large XML file into smaller batches.

    Args:
        xml_file: Path to XML file
        batch_size: Number of vouchers per batch

    Returns:
        List of XML strings, each containing a batch
    """
    print(f"\nSplitting {xml_file.name} into batches of {batch_size}...")

    content = xml_file.read_text()

    # Parse XML
    root = ET.fromstring(content)

    # Extract header info
    company = root.find('.//SVCURRENTCOMPANY').text

    # Find all vouchers
    vouchers = root.findall('.//VOUCHER')
    print(f"  Found {len(vouchers)} vouchers")

    # Skip zero-amount vouchers
    valid_vouchers = []
    skipped = 0
    for v in vouchers:
        amounts = [float(amt.text) for amt in v.findall('.//AMOUNT') if amt.text]
        if all(abs(a) < 0.01 for a in amounts):  # All amounts are zero
            skipped += 1
            continue
        valid_vouchers.append(v)

    if skipped:
        print(f"  Skipped {skipped} zero-amount vouchers")
    print(f"  Valid vouchers: {len(valid_vouchers)}")

    # Split into batches
    batches = []
    for i in range(0, len(valid_vouchers), batch_size):
        batch_vouchers = valid_vouchers[i:i+batch_size]

        # Create batch XML
        batch_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Import</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
      </STATICVARIABLES>
    </DESC>
    <DATA>
      <TALLYMESSAGE>
'''

        # Add vouchers
        for voucher in batch_vouchers:
            batch_xml += ET.tostring(voucher, encoding='unicode') + '\n'

        batch_xml += '''      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>'''

        batches.append(batch_xml)

    print(f"  Created {len(batches)} batches")
    return batches


def import_batch(batch_xml: str, batch_num: int, total_batches: int) -> dict:
    """Import a batch of vouchers to Tally.

    Args:
        batch_xml: XML string with vouchers
        batch_num: Batch number (1-indexed)
        total_batches: Total number of batches

    Returns:
        dict with import results
    """
    url = f"http://{TALLY_HOST}:{TALLY_PORT}"

    print(f"\n  Batch {batch_num}/{total_batches}: Importing...")

    try:
        response = requests.post(
            url,
            data=batch_xml.encode('utf-8'),
            headers={'Content-Type': 'application/xml'},
            timeout=60
        )

        # Parse response
        result = {
            'batch': batch_num,
            'status_code': response.status_code,
            'created': 0,
            'altered': 0,
            'errors': 0,
            'exceptions': 0,
            'ignored': 0,
        }

        if response.status_code == 200:
            try:
                resp_root = ET.fromstring(response.text)
                import_result = resp_root.find('.//IMPORTRESULT')

                if import_result is not None:
                    result['created'] = int(import_result.findtext('CREATED', '0'))
                    result['altered'] = int(import_result.findtext('ALTERED', '0'))
                    result['errors'] = int(import_result.findtext('ERRORS', '0'))
                    result['exceptions'] = int(import_result.findtext('EXCEPTIONS', '0'))
                    result['ignored'] = int(import_result.findtext('IGNORED', '0'))

                    # Check for line errors
                    line_errors = resp_root.findall('.//LINEERROR')
                    if line_errors:
                        result['line_errors'] = [err.text for err in line_errors]

                    print(f"    ✓ Created: {result['created']}, Errors: {result['errors']}, Exceptions: {result['exceptions']}")

                    if line_errors:
                        print(f"    ⚠️  Line errors: {len(line_errors)}")
                        for err in line_errors[:3]:  # Show first 3
                            print(f"       - {err.text[:100]}")
                else:
                    print(f"    ⚠️  Response: {response.text[:200]}")
                    result['raw_response'] = response.text

            except ET.ParseError as e:
                print(f"    ⚠️  Could not parse response: {e}")
                result['parse_error'] = str(e)
                result['raw_response'] = response.text[:500]
        else:
            print(f"    ✗ HTTP {response.status_code}")
            result['raw_response'] = response.text

        return result

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return {
            'batch': batch_num,
            'error': str(e)
        }


def main():
    """Import October 2025 vouchers in batches."""

    files_to_import = [
        (ROOT / "data/tally/generated/sales_vouchers_oct2025.xml", "Sales", 100),
        (ROOT / "data/tally/generated/journal_vouchers_oct2025.xml", "Journal", 100),
    ]

    print("="*70)
    print("OCTOBER 2025 VOUCHER IMPORT")
    print("="*70)
    print(f"Tally Server: {TALLY_HOST}:{TALLY_PORT}")
    print(f"Company: {TALLY_COMPANY}")
    print("="*70)

    all_results = []

    for xml_file, voucher_type, batch_size in files_to_import:
        if not xml_file.exists():
            print(f"\n⚠️  File not found: {xml_file}")
            continue

        print(f"\n\n### {voucher_type.upper()} VOUCHERS ###")

        # Split into batches
        batches = split_vouchers_into_batches(xml_file, batch_size)

        # Import each batch
        batch_results = []
        for i, batch_xml in enumerate(batches, 1):
            result = import_batch(batch_xml, i, len(batches))
            batch_results.append(result)

            # Small delay between batches
            if i < len(batches):
                import time
                time.sleep(0.5)

        all_results.append({
            'type': voucher_type,
            'batches': batch_results
        })

    # Summary
    print("\n\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)

    for result_set in all_results:
        voucher_type = result_set['type']
        batches = result_set['batches']

        total_created = sum(b.get('created', 0) for b in batches)
        total_errors = sum(b.get('errors', 0) for b in batches)
        total_exceptions = sum(b.get('exceptions', 0) for b in batches)

        print(f"\n{voucher_type} Vouchers:")
        print(f"  Batches: {len(batches)}")
        print(f"  Created: {total_created}")
        print(f"  Errors: {total_errors}")
        print(f"  Exceptions: {total_exceptions}")

        if total_errors > 0 or total_exceptions > 0:
            print(f"  ⚠️  Some vouchers failed - check batch details above")

    print("\n" + "="*70)
    print("Verify in Tally:")
    print("  Gateway → Display → Day Book")
    print("  Period: 01-Oct-2025 to 31-Oct-2025")
    print("="*70)


if __name__ == "__main__":
    import time  # Import here to avoid import at top if not needed
    main()
