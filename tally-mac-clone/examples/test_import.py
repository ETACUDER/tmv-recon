"""Test script for Import/ETL functionality.

Demonstrates:
- Template download
- Excel import (ledgers, vouchers)
- Bank statement import
- XML import
"""
import requests
import io
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_download_templates():
    """Test downloading all import templates."""
    print("=" * 60)
    print("TEST: Download Import Templates")
    print("=" * 60)

    templates = {
        "ledgers": "/api/import/template/ledgers",
        "groups": "/api/import/template/groups",
        "vouchers": "/api/import/template/vouchers?voucher_type=Payment",
        "stock_items": "/api/import/template/stock-items"
    }

    for name, endpoint in templates.items():
        print(f"\nDownloading {name} template...")
        response = requests.get(f"{BASE_URL}{endpoint}")

        if response.status_code == 200:
            filename = f"{name}_template.xlsx"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded: {filename} ({len(response.content)} bytes)")
        else:
            print(f"✗ Failed: {response.status_code} - {response.text}")

    print("\n" + "=" * 60)


def test_import_ledgers():
    """Test importing ledgers from Excel."""
    print("\n" + "=" * 60)
    print("TEST: Import Ledgers from Excel")
    print("=" * 60)

    # First, ensure we have groups
    print("\nChecking available groups...")
    response = requests.get(f"{BASE_URL}/api/groups")
    groups = response.json()
    print(f"Available groups: {len(groups)}")

    # Create sample Excel data (would normally use openpyxl)
    print("\nNote: Use the downloaded template and fill with data")
    print("Expected columns: Name, Group Name, Opening Balance, Notes")
    print("\nSample data:")
    print("  ABC Suppliers, Sundry Creditors, 50000, Opening balance")
    print("  XYZ Customer, Sundry Debtors, 75000, ")
    print("  HDFC Bank, Bank Accounts, 100000, Current account")

    # To actually test, you would:
    # 1. Create Excel file with openpyxl
    # 2. Upload it
    # Example:
    # with open('ledgers_sample.xlsx', 'rb') as f:
    #     files = {'file': f}
    #     response = requests.post(f"{BASE_URL}/api/import/excel/ledgers", files=files)
    #     result = response.json()
    #     print(f"\nImport Results:")
    #     print(f"  Total: {result['total_records']}")
    #     print(f"  Success: {result['success_count']}")
    #     print(f"  Errors: {result['error_count']}")
    #     if result['errors']:
    #         print(f"\nErrors:")
    #         for error in result['errors']:
    #             print(f"  Row {error['row']}: {error['error']}")

    print("\n" + "=" * 60)


def test_import_vouchers():
    """Test importing vouchers from Excel."""
    print("\n" + "=" * 60)
    print("TEST: Import Vouchers from Excel")
    print("=" * 60)

    print("\nNote: Use the downloaded template and fill with data")
    print("Expected columns: Date, Voucher Number, Ledger Name, Debit, Credit, Narration")
    print("\nSample data (Payment voucher):")
    print("  2026-04-15, PMT/001, HDFC Bank, , 10000, Payment to ABC Suppliers")
    print("  2026-04-15, PMT/001, ABC Suppliers, 10000, , Payment to ABC Suppliers")
    print("\nNote: Entries grouped by voucher number must balance (Dr = Cr)")

    # To test:
    # with open('payments_sample.xlsx', 'rb') as f:
    #     files = {'file': f}
    #     params = {'voucher_type': 'Payment', 'company_id': 1}
    #     response = requests.post(
    #         f"{BASE_URL}/api/import/excel/vouchers",
    #         files=files,
    #         params=params
    #     )
    #     result = response.json()
    #     print(f"\nImport Results:")
    #     print(f"  Total vouchers: {result['total_vouchers']}")
    #     print(f"  Success: {result['success_count']}")
    #     print(f"  Errors: {result['error_count']}")

    print("\n" + "=" * 60)


def test_bank_statement_import():
    """Test importing bank statement."""
    print("\n" + "=" * 60)
    print("TEST: Import Bank Statement")
    print("=" * 60)

    # Get bank ledgers
    print("\nFetching bank ledgers...")
    response = requests.get(f"{BASE_URL}/api/ledgers")
    ledgers = response.json()
    bank_ledgers = [l for l in ledgers if 'Bank' in l.get('group', '')]

    if bank_ledgers:
        print(f"Available bank ledgers: {len(bank_ledgers)}")
        for ledger in bank_ledgers[:3]:
            print(f"  ID: {ledger['id']}, Name: {ledger['name']}")
    else:
        print("No bank ledgers found. Create one first.")

    print("\nBank statement format:")
    print("Columns: date, description, debit, credit, balance, cheque_number (opt), reference (opt)")
    print("\nAuto-detected formats:")
    print("  HDFC: Date, Narration, Withdrawal Amt., Deposit Amt., Closing Balance")
    print("  ICICI: Transaction Date, Description, Debit, Credit, Balance")

    print("\nSample data:")
    print("  2026-04-15, NEFT-SALARY, , 50000, 150000")
    print("  2026-04-16, ELECTRICITY BILL, 2500, , 147500")
    print("  2026-04-17, CHQ-123456, 10000, , 137500")

    # To test:
    # with open('bank_statement.xlsx', 'rb') as f:
    #     files = {'file': f}
    #     params = {'ledger_id': 5, 'file_format': 'excel'}
    #     response = requests.post(
    #         f"{BASE_URL}/api/import/bank-statement",
    #         files=files,
    #         params=params
    #     )
    #     result = response.json()
    #     print(f"\nImport Results:")
    #     print(f"  Total records: {result['total_records']}")
    #     print(f"  Imported: {result['imported_count']}")
    #     print(f"  Matched: {result['matched_count']}")
    #     print(f"  Unmatched: {result['unmatched_count']}")
    #     print(f"\nMatch rate: {result['matched_count']/result['imported_count']*100:.1f}%")
    #
    #     if result['suggestions']:
    #         print(f"\nLedger suggestions for unmatched transactions:")
    #         for suggestion in result['suggestions'][:5]:
    #             print(f"  {suggestion['description']} → {suggestion['suggested_ledger']}")

    print("\n" + "=" * 60)


def test_xml_import():
    """Test importing Tally XML."""
    print("\n" + "=" * 60)
    print("TEST: Import Tally XML")
    print("=" * 60)

    print("\nTally XML format (ENVELOPE/BODY/TALLYMESSAGE structure):")
    print("""
<ENVELOPE>
  <BODY>
    <IMPORTDATA>
      <REQUESTDATA>
        <TALLYMESSAGE>
          <VOUCHER>
            <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
            <VOUCHERNUMBER>PMT/001</VOUCHERNUMBER>
            <DATE>20260415</DATE>
            <NARRATION>Payment to supplier</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>HDFC Bank</LEDGERNAME>
              <AMOUNT>-10000</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>ABC Suppliers</LEDGERNAME>
              <AMOUNT>10000</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>
    """)

    print("\nNotes:")
    print("  - Date format: YYYYMMDD or YYYY-MM-DD")
    print("  - Amount: Negative for debit, Positive for credit (Tally convention)")
    print("  - All ledgers must exist before import")

    # To test:
    # with open('tally_vouchers.xml', 'rb') as f:
    #     files = {'file': f}
    #     params = {'company_id': 1}
    #     response = requests.post(
    #         f"{BASE_URL}/api/import/xml",
    #         files=files,
    #         params=params
    #     )
    #     result = response.json()
    #     print(f"\nImport Results:")
    #     print(f"  Total vouchers: {result['total_vouchers']}")
    #     print(f"  Success: {result['success_count']}")
    #     print(f"  Errors: {result['error_count']}")
    #     if result['errors']:
    #         print(f"\nErrors:")
    #         for error in result['errors']:
    #             print(f"  {error['voucher']}: {error['error']}")

    print("\n" + "=" * 60)


def create_sample_xml():
    """Create a sample Tally XML file for testing."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
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
        <IMPORTDUPS>@@DUPCONFIGIGNORE</IMPORTDUPS>
      </STATICVARIABLES>
    </DESC>
    <DATA>
      <TALLYMESSAGE>
        <VOUCHER>
          <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
          <VOUCHERNUMBER>PMT/001</VOUCHERNUMBER>
          <DATE>20260415</DATE>
          <NARRATION>Payment to ABC Suppliers</NARRATION>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>HDFC Bank</LEDGERNAME>
            <AMOUNT>-10000</AMOUNT>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>ABC Suppliers</LEDGERNAME>
            <AMOUNT>10000</AMOUNT>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
      <TALLYMESSAGE>
        <VOUCHER>
          <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
          <VOUCHERNUMBER>RCP/001</VOUCHERNUMBER>
          <DATE>20260416</DATE>
          <NARRATION>Receipt from XYZ Customer</NARRATION>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>HDFC Bank</LEDGERNAME>
            <AMOUNT>15000</AMOUNT>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
          </ALLLEDGERENTRIES.LIST>
          <ALLLEDGERENTRIES.LIST>
            <LEDGERNAME>XYZ Customer</LEDGERNAME>
            <AMOUNT>-15000</AMOUNT>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          </ALLLEDGERENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>"""

    with open('sample_vouchers.xml', 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print("Created sample_vouchers.xml")
    return 'sample_vouchers.xml'


def main():
    """Run all import tests."""
    print("\n" + "=" * 60)
    print("IMPORT/ETL SYSTEM TEST SUITE")
    print("=" * 60)

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        print(f"\n✓ Server is running at {BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Server is not running at {BASE_URL}")
        print("Start the server with: uvicorn tally_mac_clone.app:app")
        return

    # Run tests
    test_download_templates()
    test_import_ledgers()
    test_import_vouchers()
    test_bank_statement_import()
    test_xml_import()

    # Create sample XML
    print("\n" + "=" * 60)
    print("CREATING SAMPLE FILES")
    print("=" * 60)
    xml_file = create_sample_xml()
    print(f"\nCreated {xml_file} - you can import this via:")
    print(f"  curl -X POST -F 'file=@{xml_file}' '{BASE_URL}/api/import/xml?company_id=1'")

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Use downloaded templates to create import files")
    print("2. Fill templates with actual data")
    print("3. Upload via API or UI (Alt+X → Import Excel)")
    print("4. Check import results and handle any errors")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
