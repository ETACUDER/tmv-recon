"""Generate Tally vouchers from Excel data.

Creates Sales and Journal vouchers in Tally XML format from EZee invoice data.
"""
from __future__ import annotations
import pandas as pd
from datetime import datetime
from pathlib import Path
import re
from xml.sax.saxutils import escape as xml_escape


def normalize_invoice_no(inv_no: str) -> str:
    """Convert 25-26/123 to 2025/2026/123 format."""
    if pd.isna(inv_no):
        return ""
    inv_str = str(inv_no).strip()

    # Convert short form to long form
    match = re.match(r'(\d{2})-(\d{2})/(\d+)', inv_str)
    if match:
        y1, y2, num = match.groups()
        return f"20{y1}/20{y2}/{num}"

    return inv_str


def format_tally_date(date_str: str) -> str:
    """Convert date to Tally format YYYYMMDD."""
    if pd.isna(date_str):
        return ""

    # Parse various date formats
    try:
        if isinstance(date_str, str):
            dt = pd.to_datetime(date_str)
        else:
            dt = date_str
        return dt.strftime('%Y%m%d')
    except:
        return ""


def determine_gst_ledger(gst_rate: float, net_amount: float) -> str:
    """Determine the appropriate GST ledger based on rate."""
    if pd.isna(gst_rate) or pd.isna(net_amount):
        # Infer from amounts if rate not available
        return "SALE ACCOMODATION GST @ 12 %"

    rate = float(gst_rate)

    if abs(rate - 5.0) < 0.5:
        return "SALE ACCOMODATION GST @ 5 %"
    elif abs(rate - 12.0) < 0.5:
        return "SALE ACCOMODATION GST @ 12 %"
    elif abs(rate - 18.0) < 0.5:
        return "SALE ACCOMODATION GST @ 18 %"
    else:
        return "SALE ACCOMODATION GST @ 12 %"  # Default


def map_settlement_to_ledger(settlement_mode: str) -> str:
    """Map settlement mode to Tally ledger."""
    if pd.isna(settlement_mode):
        return "CARD / UPI / PAYTM / G PAY"

    mode = str(settlement_mode).upper()

    # For multiple modes, use the first one or default
    if ',' in mode:
        mode = mode.split(',')[0].strip()

    if 'CASH' in mode:
        return "Cash"
    elif 'AGODA' in mode:
        return "Sundry Debtors"  # Agoda settles later
    elif 'BOOKING' in mode or 'GOIBIBO' in mode or 'MMT' in mode:
        return "Sundry Debtors"
    else:
        # UPI, Credit Card, Debit Card, etc.
        return "CARD / UPI / PAYTM / G PAY"


def generate_sales_voucher(invoice_row: pd.Series) -> dict:
    """Generate Sales voucher from invoice data.

    Returns dict with voucher structure ready for XML export.
    """
    invoice_no = normalize_invoice_no(invoice_row.get('Invoice #', ''))
    date = format_tally_date(invoice_row.get('Invoice date'))
    guest_name = invoice_row.get('Guest Name', 'Guest')

    # Amounts
    net_amount = float(invoice_row.get('Net Amount', 0))
    cgst = float(invoice_row.get('Tax Amount', 0))
    sgst = float(invoice_row.get('Tax Amount.1', 0))
    gross_amount = float(invoice_row.get('Gross Amount', 0))

    # Determine GST ledger
    gst_rate = invoice_row.get('Tax %', 12.0)
    sales_ledger = determine_gst_ledger(gst_rate, net_amount)

    # Party ledger (always Sundry Debtors for now)
    party_ledger = "Sundry Debtors"

    voucher = {
        'type': 'Sales',
        'number': invoice_no,
        'date': date,
        'narration': f"INVOICE NO:-{invoice_no}, {guest_name}",
        'party': party_ledger,
        'ledgers': [
            {
                'name': party_ledger,
                'is_deemed_positive': 'Yes',
                'amount': -gross_amount  # Negative for Dr
            },
            {
                'name': sales_ledger,
                'is_deemed_positive': 'No',
                'amount': net_amount  # Positive for Cr
            },
            {
                'name': 'CGST',
                'is_deemed_positive': 'No',
                'amount': cgst
            },
            {
                'name': 'SGST',
                'is_deemed_positive': 'No',
                'amount': sgst
            }
        ]
    }

    return voucher


def generate_journal_voucher(invoice_row: pd.Series) -> dict | None:
    """Generate Journal voucher for payment settlement.

    Returns dict with voucher structure, or None if no settlement.
    """
    settlement_amt = invoice_row.get('settlement_amount_abs', 0)
    if pd.isna(settlement_amt) or settlement_amt <= 0:
        return None

    invoice_no = normalize_invoice_no(invoice_row.get('Invoice #', ''))
    date = format_tally_date(invoice_row.get('Invoice date'))
    settlement_mode = invoice_row.get('Settlement/Particular', '')

    # Map settlement mode to ledger
    payment_ledger = map_settlement_to_ledger(settlement_mode)

    # Generate voucher number (J/YYYY/invoice_num)
    vch_num = f"J/2025/{invoice_no.split('/')[-1]}" if invoice_no else "J/2025/0000"

    voucher = {
        'type': 'Journal',
        'number': vch_num,
        'date': date,
        'narration': f"BEING PAID THROUGH {settlement_mode.upper()} AGAINST INVOICE NO:{invoice_no}",
        'party': None,
        'ledgers': [
            {
                'name': payment_ledger,
                'is_deemed_positive': 'Yes',
                'amount': -float(settlement_amt)  # Dr
            },
            {
                'name': 'Sundry Debtors',
                'is_deemed_positive': 'No',
                'amount': float(settlement_amt)  # Cr
            }
        ]
    }

    return voucher


def voucher_to_xml(voucher: dict) -> str:
    """Convert voucher dict to Tally XML format."""
    xml_lines = []

    xml_lines.append(f'  <VOUCHER VCHTYPE="{voucher["type"]}">')
    xml_lines.append(f'    <DATE>{voucher["date"]}</DATE>')
    xml_lines.append(f'    <VOUCHERNUMBER>{xml_escape(voucher["number"])}</VOUCHERNUMBER>')

    if voucher.get('party'):
        xml_lines.append(f'    <PARTYLEDGERNAME>{xml_escape(voucher["party"])}</PARTYLEDGERNAME>')

    xml_lines.append(f'    <NARRATION>{xml_escape(voucher["narration"])}</NARRATION>')

    # Ledger entries
    for ledger in voucher['ledgers']:
        xml_lines.append('    <ALLLEDGERENTRIES.LIST>')
        xml_lines.append(f'      <LEDGERNAME>{xml_escape(ledger["name"])}</LEDGERNAME>')
        xml_lines.append(f'      <ISDEEMEDPOSITIVE>{ledger["is_deemed_positive"]}</ISDEEMEDPOSITIVE>')
        xml_lines.append(f'      <AMOUNT>{ledger["amount"]:.2f}</AMOUNT>')
        xml_lines.append('    </ALLLEDGERENTRIES.LIST>')

    xml_lines.append('  </VOUCHER>')

    return '\n'.join(xml_lines)


def generate_vouchers_from_invoices(invoice_df: pd.DataFrame, limit: int = None) -> tuple[list, list]:
    """Generate vouchers from invoice dataframe.

    Args:
        invoice_df: DataFrame with invoice data
        limit: Maximum number of vouchers to generate (None = all)

    Returns:
        Tuple of (sales_vouchers, journal_vouchers) as list of dicts
    """
    if limit:
        invoice_df = invoice_df.head(limit)

    sales_vouchers = []
    journal_vouchers = []

    for idx, row in invoice_df.iterrows():
        # Generate Sales voucher
        sales = generate_sales_voucher(row)
        sales_vouchers.append(sales)

        # Generate Journal voucher if settlement exists
        journal = generate_journal_voucher(row)
        if journal:
            journal_vouchers.append(journal)

    return sales_vouchers, journal_vouchers


def export_vouchers_to_xml(vouchers: list, output_file: Path, company_name: str = "THE MANGAL VIEW RESIDENCY Final"):
    """Export vouchers to Tally XML file.

    Args:
        vouchers: List of voucher dicts
        output_file: Path to output XML file
        company_name: Tally company name
    """
    xml_content = []

    # XML Header
    xml_content.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_content.append('<ENVELOPE>')
    xml_content.append('  <HEADER>')
    xml_content.append('    <VERSION>1</VERSION>')
    xml_content.append('    <TALLYREQUEST>Import</TALLYREQUEST>')
    xml_content.append('    <TYPE>Data</TYPE>')
    xml_content.append(f'    <ID>Vouchers</ID>')
    xml_content.append('  </HEADER>')
    xml_content.append('  <BODY>')
    xml_content.append('    <DESC>')
    xml_content.append('      <STATICVARIABLES>')
    xml_content.append(f'        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>')
    xml_content.append('      </STATICVARIABLES>')
    xml_content.append('    </DESC>')
    xml_content.append('    <DATA>')
    xml_content.append('      <TALLYMESSAGE>')

    # Add all vouchers
    for voucher in vouchers:
        xml_content.append(voucher_to_xml(voucher))

    # XML Footer
    xml_content.append('      </TALLYMESSAGE>')
    xml_content.append('    </DATA>')
    xml_content.append('  </BODY>')
    xml_content.append('</ENVELOPE>')

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('\n'.join(xml_content))


if __name__ == "__main__":
    # Test with October 2025 data
    from tmv_recon.config import ROOT

    invoice_file = ROOT / "data/recon/canonical/invoice_oct2025_corrected.csv"
    invoices = pd.read_csv(invoice_file)

    # Generate 10 samples
    sales, journal = generate_vouchers_from_invoices(invoices, limit=10)

    print(f"Generated {len(sales)} Sales vouchers")
    print(f"Generated {len(journal)} Journal vouchers")

    # Export samples
    output_dir = ROOT / "data/tally/generated"
    export_vouchers_to_xml(sales, output_dir / "sample_sales_vouchers.xml")
    export_vouchers_to_xml(journal, output_dir / "sample_journal_vouchers.xml")

    print(f"\nSaved to:")
    print(f"  {output_dir / 'sample_sales_vouchers.xml'}")
    print(f"  {output_dir / 'sample_journal_vouchers.xml'}")
