"""Voucher generation functions for different voucher types.

Generates Tally vouchers following discovered patterns from daybook_FY25-26.xml.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class Invoice:
    """Invoice data from canonical invoices.csv."""
    invoice_no: str
    invoice_date: date
    guest_name: str
    net_amount: float
    cgst: float
    sgst: float
    gross_amount: float
    gst_rate: float = 0.0


def generate_sales_voucher(invoice: Invoice) -> str:
    """Generate Sales voucher XML using LEDGERENTRIES.LIST pattern.

    Pattern from requirements §1.1:
        Dr  Sundry Debtors                (gross_amount)
            Cr  SALE ACCOMODATION GST @ 5%  (net_amount)
            Cr  CGST                        (cgst)
            Cr  SGST                        (sgst)

    Sign convention:
        - ISDEEMEDPOSITIVE=No + positive amount = Debit (Sundry Debtors)
        - ISDEEMEDPOSITIVE=Yes + negative amount = Credit (income, GST)

    Args:
        invoice: Invoice data with GST split

    Returns:
        TALLYMESSAGE XML string

    Raises:
        ValueError: If validation fails (net + cgst + sgst ≠ gross within ₹1)
    """
    # Validate GST calculation
    calculated_gross = invoice.net_amount + invoice.cgst + invoice.sgst
    tolerance = 1.0
    if abs(calculated_gross - invoice.gross_amount) > tolerance:
        raise ValueError(
            f"GST validation failed for {invoice.invoice_no}: "
            f"net({invoice.net_amount}) + cgst({invoice.cgst}) + sgst({invoice.sgst}) = {calculated_gross}, "
            f"but gross = {invoice.gross_amount}"
        )

    # Determine GST rate and income ledger name
    gst_rate = invoice.gst_rate
    if gst_rate == 0.0 and invoice.net_amount > 0:
        # Calculate from amounts
        gst_rate = round(((invoice.cgst + invoice.sgst) / invoice.net_amount) * 100, 2)

    # Default to 5% for accommodation
    if gst_rate == 0.0:
        gst_rate = 5.0

    # Select income ledger based on GST rate
    if abs(gst_rate - 18.0) < 0.1:
        income_ledger = "RENTAL INCOME GST @ 18%"
    else:
        income_ledger = "SALE ACCOMODATION GST @ 5 %"  # Match exact spacing from ground truth

    # Format narration: INVOICE NO:-{{invoice_no}} {{GUEST_NAME_UPPERCASE}}
    narration = f"INVOICE NO:-{invoice.invoice_no} {invoice.guest_name.upper()}"

    # Format date as YYYYMMDD
    voucher_date = invoice.invoice_date.strftime("%Y%m%d")

    # Build ledger entries - CRITICAL: Use LEDGERENTRIES.LIST for Sales vouchers
    entries = []

    # Entry 1: Dr Sundry Debtors (ISDEEMEDPOSITIVE=No, positive amount = Debit)
    entries.append(
        "      <LEDGERENTRIES.LIST>\n"
        "        <LEDGERNAME>Sundry Debtors</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        "        <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        f"        <AMOUNT>{invoice.gross_amount:.2f}</AMOUNT>\n"
        "      </LEDGERENTRIES.LIST>"
    )

    # Entry 2: Cr Income (ISDEEMEDPOSITIVE=Yes, negative amount = Credit)
    entries.append(
        "      <LEDGERENTRIES.LIST>\n"
        f"        <LEDGERNAME>{income_ledger}</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        f"        <AMOUNT>{-invoice.net_amount:.2f}</AMOUNT>\n"
        "      </LEDGERENTRIES.LIST>"
    )

    # Entry 3: Cr CGST (ISDEEMEDPOSITIVE=Yes, negative amount = Credit)
    entries.append(
        "      <LEDGERENTRIES.LIST>\n"
        "        <LEDGERNAME>CGST</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        f"        <AMOUNT>{-invoice.cgst:.2f}</AMOUNT>\n"
        "      </LEDGERENTRIES.LIST>"
    )

    # Entry 4: Cr SGST (ISDEEMEDPOSITIVE=Yes, negative amount = Credit)
    entries.append(
        "      <LEDGERENTRIES.LIST>\n"
        "        <LEDGERNAME>SGST</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        f"        <AMOUNT>{-invoice.sgst:.2f}</AMOUNT>\n"
        "      </LEDGERENTRIES.LIST>"
    )

    # Assemble TALLYMESSAGE
    return (
        '    <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        '      <VOUCHER VCHTYPE="Sales" ACTION="Create">\n'
        f"        <DATE>{voucher_date}</DATE>\n"
        "        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>\n"
        f"        <VOUCHERNUMBER>{_escape_xml(invoice.invoice_no)}</VOUCHERNUMBER>\n"
        f"        <NARRATION>{_escape_xml(narration)}</NARRATION>\n"
        "        <PARTYLEDGERNAME>Sundry Debtors</PARTYLEDGERNAME>\n"
        + "\n".join(entries) + "\n"
        "      </VOUCHER>\n"
        "    </TALLYMESSAGE>"
    )


def calculate_gst_split(gross_amount: float, gst_rate: float = 5.0) -> tuple[float, float, float]:
    """Calculate net, CGST, and SGST from gross amount.

    Args:
        gross_amount: Total invoice amount (inclusive of GST)
        gst_rate: Total GST rate (default 5% for accommodation)

    Returns:
        Tuple of (net_amount, cgst, sgst)
    """
    divisor = 1 + (gst_rate / 100)
    net = gross_amount / divisor
    total_gst = gross_amount - net
    cgst = total_gst / 2
    sgst = total_gst / 2

    return round(net, 2), round(cgst, 2), round(sgst, 2)


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def generate_journal_voucher(
    payment_amount: float,
    invoice_no: str,
    payment_mode: str,
    guest_name: str,
    voucher_date: date | None = None,
) -> str:
    """Generate Journal voucher for payment settlement.

    Pattern from requirements §1.2:
        Dr  CARD / UPI / PAYTM / G PAY  (payment_amount)
            Cr  Sundry Debtors          (payment_amount)

    Sign convention (ALLLEDGERENTRIES.LIST):
        - ISDEEMEDPOSITIVE=Yes + negative amount = Credit (payment ledger)
        - ISDEEMEDPOSITIVE=No + positive amount = Debit (Sundry Debtors)

    Args:
        payment_amount: Amount settled
        invoice_no: Invoice number for linkage
        payment_mode: UPI/TPP/CARD/CASH etc
        guest_name: Guest name (uppercase in narration)
        voucher_date: Voucher date (defaults to today)

    Returns:
        TALLYMESSAGE XML string
    """
    # Format narration: BEING PAID THROUGH {{MODE}} AGAINST INVOICE NO:{{no}} {{guest}}
    narration = f"BEING PAID THROUGH {payment_mode.upper()} AGAINST INVOICE NO:{invoice_no} {guest_name.upper()}"

    # Use today if no date provided
    if voucher_date is None:
        voucher_date = date.today()

    # Format date as YYYYMMDD
    vch_date = voucher_date.strftime("%Y%m%d")

    # Build ledger entries - CRITICAL: Use ALLLEDGERENTRIES.LIST for Journal vouchers
    entries = []

    # Entry 1: Dr CARD / UPI / PAYTM / G PAY (ISDEEMEDPOSITIVE=Yes, negative = Credit)
    # Wait - the pattern shows CARD/UPI is credited (receives money), Sundry Debtors is debited
    # From XML: CARD/UPI has ISDEEMEDPOSITIVE=Yes and AMOUNT=-1000 (Credit)
    #           Sundry Debtors has ISDEEMEDPOSITIVE=No and AMOUNT=1000 (Debit)
    entries.append(
        "      <ALLLEDGERENTRIES.LIST>\n"
        "        <LEDGERNAME>CARD / UPI / PAYTM / G PAY</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        "        <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        f"        <AMOUNT>{-payment_amount:.2f}</AMOUNT>\n"
        "      </ALLLEDGERENTRIES.LIST>"
    )

    # Entry 2: Cr Sundry Debtors (ISDEEMEDPOSITIVE=No, positive = Debit)
    entries.append(
        "      <ALLLEDGERENTRIES.LIST>\n"
        "        <LEDGERNAME>Sundry Debtors</LEDGERNAME>\n"
        "        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        "        <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        f"        <AMOUNT>{payment_amount:.2f}</AMOUNT>\n"
        "      </ALLLEDGERENTRIES.LIST>"
    )

    # Assemble TALLYMESSAGE
    return (
        '    <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        '      <VOUCHER VCHTYPE="Journal" ACTION="Create">\n'
        f"        <DATE>{vch_date}</DATE>\n"
        "        <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>\n"
        f"        <VOUCHERNUMBER>{_escape_xml(invoice_no)}</VOUCHERNUMBER>\n"
        f"        <REFERENCE>{_escape_xml(invoice_no)}</REFERENCE>\n"
        f"        <NARRATION>{_escape_xml(narration)}</NARRATION>\n"
        "        <PARTYLEDGERNAME>CARD / UPI / PAYTM / G PAY</PARTYLEDGERNAME>\n"
        + "\n".join(entries) + "\n"
        "      </VOUCHER>\n"
        "    </TALLYMESSAGE>"
    )


def vouchers_envelope(tallymessages: list[str], company: str = "THE MANGAL VIEW RESIDENCY Final") -> str:
    """Wrap TALLYMESSAGE entries in ENVELOPE structure.

    Args:
        tallymessages: List of TALLYMESSAGE XML strings
        company: Tally company name

    Returns:
        Complete XML document ready for Tally import
    """
    sv = f"<SVCURRENTCOMPANY>{_escape_xml(company)}</SVCURRENTCOMPANY>" if company else ""
    static_vars = f"<STATICVARIABLES>{sv}</STATICVARIABLES>" if sv else ""

    body = "\n".join(tallymessages)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <VERSION>1</VERSION>\n"
        "    <TALLYREQUEST>Import</TALLYREQUEST>\n"
        "    <TYPE>Data</TYPE>\n"
        "    <ID>Vouchers</ID>\n"
        "  </HEADER>\n"
        f"  <BODY>\n    <DESC>{static_vars}</DESC>\n    <DATA>\n{body}\n    </DATA>\n  </BODY>\n"
        "</ENVELOPE>\n"
    )
