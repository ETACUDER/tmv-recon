#!/usr/bin/env python3
"""Fetch full FY25-26 daybook from Tally VM and save as XML."""
import sys
from pathlib import Path
from datetime import date
from xml.etree import ElementTree as ET

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.http import post_xml
from tmv_recon.config import TALLY_HOST, TALLY_PORT, TALLY_COMPANY


def fetch_daybook_xml(from_date: str, to_date: str, company: str) -> str:
    """Fetch daybook XML directly from Tally."""
    xml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Day Book</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        <SVFROMDATE>{from_date}</SVFROMDATE>
        <SVTODATE>{to_date}</SVTODATE>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>'''

    print(f"Fetching daybook from {from_date} to {to_date}...")
    response = post_xml(xml_request, host=TALLY_HOST, port=TALLY_PORT, timeout=300)

    # Clean invalid XML characters (&#4; and other control chars)
    import re
    # Remove invalid control characters but keep valid ones (tab, newline, carriage return)
    response = re.sub(r'&#([0-8]|1[1-2]|1[4-9]|[2-3][0-9]);', '', response)

    # Check status
    root = ET.fromstring(response)
    status = root.findtext("HEADER/STATUS") or root.findtext(".//STATUS")
    if status != "1":
        error = root.findtext(".//LINEERROR") or "Unknown error"
        raise RuntimeError(f"Tally error: {error}")

    return response


if __name__ == "__main__":
    print(f"Connecting to Tally at {TALLY_HOST}:{TALLY_PORT}")
    print(f"Company: {TALLY_COMPANY}")

    # FY25-26: April 1, 2025 to March 31, 2026
    from_date = "20250401"
    to_date = "20260331"

    try:
        xml_data = fetch_daybook_xml(from_date, to_date, TALLY_COMPANY)

        # Save to file
        output_dir = Path(__file__).parent.parent / "data" / "tally" / "raw_xml"
        output_file = output_dir / "daybook_FY25-26_FULL.xml"
        output_file.write_text(xml_data, encoding="utf-8")

        # Count vouchers
        root = ET.fromstring(xml_data)
        voucher_count = len(root.findall(".//VOUCHER"))
        file_size_mb = len(xml_data) / (1024 * 1024)

        print(f"\n✅ Success!")
        print(f"Saved: {output_file}")
        print(f"Vouchers: {voucher_count:,}")
        print(f"Size: {file_size_mb:.1f} MB")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
