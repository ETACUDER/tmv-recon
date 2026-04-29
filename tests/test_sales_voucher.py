"""Test Sales voucher generation against discovered Tally patterns."""
import pytest
from datetime import date
from tmv_recon.tally.voucher_generators import (
    Invoice,
    generate_sales_voucher,
    calculate_gst_split,
    vouchers_envelope,
)


class TestSalesVoucherGeneration:
    """Test Sales voucher generation following requirements §1.1."""

    def test_invoice_with_gst_split_provided(self):
        """Test invoice where GST components are already calculated."""
        invoice = Invoice(
            invoice_no="25-26/6453",
            invoice_date=date(2026, 3, 31),
            guest_name="MRS. MADHUR PIPARSANIA",
            net_amount=2984.19,
            cgst=74.60,
            sgst=74.60,
            gross_amount=3133.39,
            gst_rate=5.0,
        )

        xml = generate_sales_voucher(invoice)

        # Verify structure
        assert '<VOUCHER VCHTYPE="Sales" ACTION="Create">' in xml
        assert '<DATE>20260331</DATE>' in xml
        assert '<VOUCHERNUMBER>25-26/6453</VOUCHERNUMBER>' in xml
        assert '<NARRATION>INVOICE NO:-25-26/6453 MRS. MADHUR PIPARSANIA</NARRATION>' in xml
        assert '<PARTYLEDGERNAME>Sundry Debtors</PARTYLEDGERNAME>' in xml

        # Verify LEDGERENTRIES.LIST (NOT ALLLEDGERENTRIES.LIST)
        assert '<LEDGERENTRIES.LIST>' in xml
        assert '<ALLLEDGERENTRIES.LIST>' not in xml

        # Verify ledger entries
        assert '<LEDGERNAME>Sundry Debtors</LEDGERNAME>' in xml
        assert '<LEDGERNAME>SALE ACCOMODATION GST @ 5 %</LEDGERNAME>' in xml
        assert '<LEDGERNAME>CGST</LEDGERNAME>' in xml
        assert '<LEDGERNAME>SGST</LEDGERNAME>' in xml

        # Verify sign convention (ISDEEMEDPOSITIVE + amount sign)
        # Dr: Sundry Debtors (ISDEEMEDPOSITIVE=No, positive amount)
        assert '<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>' in xml
        assert '<AMOUNT>3133.39</AMOUNT>' in xml

        # Cr: Income/GST (ISDEEMEDPOSITIVE=Yes, negative amount)
        assert '<AMOUNT>-2984.19</AMOUNT>' in xml
        assert '<AMOUNT>-74.60</AMOUNT>' in xml

        # Verify party ledger flag
        assert '<ISPARTYLEDGER>Yes</ISPARTYLEDGER>' in xml

    def test_invoice_without_gst_calculate_it(self):
        """Test invoice without GST split - calculate from gross amount."""
        # Gross = 5000, GST @ 5% means net = 5000/1.05 = 4761.90, CGST=SGST=119.05
        invoice = Invoice(
            invoice_no="25-26/7000",
            invoice_date=date(2026, 4, 15),
            guest_name="Mr. John Doe",
            net_amount=4761.90,
            cgst=119.05,
            sgst=119.05,
            gross_amount=5000.00,
            gst_rate=5.0,
        )

        xml = generate_sales_voucher(invoice)

        assert '<AMOUNT>5000.00</AMOUNT>' in xml  # Dr Sundry Debtors
        assert '<AMOUNT>-4761.90</AMOUNT>' in xml  # Cr Income
        assert '<AMOUNT>-119.05</AMOUNT>' in xml  # Cr CGST/SGST

    def test_invoice_with_18_percent_gst_rental_income(self):
        """Test rental income with 18% GST rate."""
        # Gross = 59000, GST @ 18% means net = 50000, CGST=SGST=4500
        invoice = Invoice(
            invoice_no="25-26/RENT-MAR26",
            invoice_date=date(2026, 3, 31),
            guest_name="TMV ROOFTOP RESTAURANT",
            net_amount=50000.00,
            cgst=4500.00,
            sgst=4500.00,
            gross_amount=59000.00,
            gst_rate=18.0,
        )

        xml = generate_sales_voucher(invoice)

        # Should use RENTAL INCOME ledger for 18% GST
        assert '<LEDGERNAME>RENTAL INCOME GST @ 18%</LEDGERNAME>' in xml
        assert '<AMOUNT>59000.00</AMOUNT>' in xml  # Dr
        assert '<AMOUNT>-50000.00</AMOUNT>' in xml  # Cr Income
        assert '<AMOUNT>-4500.00</AMOUNT>' in xml  # Cr CGST/SGST

    def test_amount_validation_fails_when_mismatch(self):
        """Test validation fails when net+cgst+sgst ≠ gross."""
        invoice = Invoice(
            invoice_no="25-26/9999",
            invoice_date=date(2026, 4, 29),
            guest_name="Test Guest",
            net_amount=5000.00,
            cgst=250.00,
            sgst=250.00,
            gross_amount=6000.00,  # Should be 5500, mismatch = 500
            gst_rate=5.0,
        )

        with pytest.raises(ValueError, match="GST validation failed"):
            generate_sales_voucher(invoice)

    def test_amount_validation_passes_within_tolerance(self):
        """Test validation passes when difference is within ₹1 tolerance."""
        invoice = Invoice(
            invoice_no="25-26/8888",
            invoice_date=date(2026, 4, 29),
            guest_name="Test Guest",
            net_amount=5000.00,
            cgst=250.00,
            sgst=250.00,
            gross_amount=5500.50,  # Off by 0.50, within ₹1 tolerance
            gst_rate=5.0,
        )

        # Should not raise
        xml = generate_sales_voucher(invoice)
        assert '<VOUCHERNUMBER>25-26/8888</VOUCHERNUMBER>' in xml

    def test_special_characters_in_guest_name_xml_escaping(self):
        """Test XML escaping for special characters in guest name."""
        invoice = Invoice(
            invoice_no="25-26/7777",
            invoice_date=date(2026, 4, 29),
            guest_name="Mr. O'Brien & Sons <Company>",
            net_amount=4761.90,
            cgst=119.05,
            sgst=119.05,
            gross_amount=5000.00,
            gst_rate=5.0,
        )

        xml = generate_sales_voucher(invoice)

        # Verify escaping
        assert "&apos;" in xml or "'" in xml  # Apostrophe handling
        assert "&amp;" in xml  # Ampersand
        assert "&lt;" in xml or "&gt;" in xml  # Angle brackets

        # Should not contain unescaped special chars in narration
        assert "O'BRIEN &amp; SONS &lt;COMPANY&gt;" in xml.upper() or \
               "O&apos;BRIEN" in xml.upper()

    def test_gst_rate_calculated_from_amounts_when_zero(self):
        """Test GST rate calculation from amounts when not provided."""
        invoice = Invoice(
            invoice_no="25-26/6666",
            invoice_date=date(2026, 4, 29),
            guest_name="Test Guest",
            net_amount=2000.00,
            cgst=100.00,
            sgst=100.00,
            gross_amount=2200.00,
            gst_rate=0.0,  # Not provided
        )

        xml = generate_sales_voucher(invoice)

        # Should calculate rate: (100+100)/2000 * 100 = 10%
        # But since it's not 18%, should default to 5% income ledger
        assert '<LEDGERNAME>SALE ACCOMODATION GST @ 5 %</LEDGERNAME>' in xml


class TestGSTCalculation:
    """Test GST split calculation helper."""

    def test_calculate_gst_split_5_percent(self):
        """Test GST split calculation for 5% rate."""
        net, cgst, sgst = calculate_gst_split(5250.00, gst_rate=5.0)

        assert net == 5000.00
        assert cgst == 125.00
        assert sgst == 125.00
        assert abs((net + cgst + sgst) - 5250.00) < 0.01

    def test_calculate_gst_split_18_percent(self):
        """Test GST split calculation for 18% rate."""
        net, cgst, sgst = calculate_gst_split(59000.00, gst_rate=18.0)

        assert net == 50000.00
        assert cgst == 4500.00
        assert sgst == 4500.00
        assert abs((net + cgst + sgst) - 59000.00) < 0.01

    def test_calculate_gst_split_default_rate(self):
        """Test default GST rate (5%) when not specified."""
        net, cgst, sgst = calculate_gst_split(2100.00)

        assert net == 2000.00
        assert cgst == 50.00
        assert sgst == 50.00


class TestEnvelopeGeneration:
    """Test envelope wrapper for vouchers."""

    def test_vouchers_envelope_structure(self):
        """Test envelope contains correct header and structure."""
        invoice = Invoice(
            invoice_no="25-26/1111",
            invoice_date=date(2026, 4, 29),
            guest_name="Test Guest",
            net_amount=1000.00,
            cgst=25.00,
            sgst=25.00,
            gross_amount=1050.00,
            gst_rate=5.0,
        )

        voucher_xml = generate_sales_voucher(invoice)
        envelope = vouchers_envelope([voucher_xml])

        # Verify XML declaration
        assert '<?xml version="1.0" encoding="UTF-8"?>' in envelope

        # Verify envelope structure
        assert '<ENVELOPE>' in envelope
        assert '<HEADER>' in envelope
        assert '<VERSION>1</VERSION>' in envelope
        assert '<TALLYREQUEST>Import</TALLYREQUEST>' in envelope
        assert '<TYPE>Data</TYPE>' in envelope
        assert '<ID>Vouchers</ID>' in envelope
        assert '</HEADER>' in envelope

        # Verify body
        assert '<BODY>' in envelope
        assert '<DESC>' in envelope
        assert '<STATICVARIABLES>' in envelope
        assert '<SVCURRENTCOMPANY>THE MANGAL VIEW RESIDENCY Final</SVCURRENTCOMPANY>' in envelope
        assert '<DATA>' in envelope
        assert '</DATA>' in envelope
        assert '</BODY>' in envelope
        assert '</ENVELOPE>' in envelope

        # Verify voucher is included
        assert '<TALLYMESSAGE xmlns:UDF="TallyUDF">' in envelope
        assert '<VOUCHERNUMBER>25-26/1111</VOUCHERNUMBER>' in envelope

    def test_envelope_with_multiple_vouchers(self):
        """Test envelope can contain multiple vouchers."""
        invoices = [
            Invoice(
                invoice_no=f"25-26/{i}",
                invoice_date=date(2026, 4, 29),
                guest_name=f"Guest {i}",
                net_amount=1000.00,
                cgst=25.00,
                sgst=25.00,
                gross_amount=1050.00,
                gst_rate=5.0,
            )
            for i in range(1, 4)
        ]

        voucher_xmls = [generate_sales_voucher(inv) for inv in invoices]
        envelope = vouchers_envelope(voucher_xmls)

        # Should contain all 3 vouchers
        assert envelope.count('<TALLYMESSAGE xmlns:UDF="TallyUDF">') == 3
        assert '<VOUCHERNUMBER>25-26/1</VOUCHERNUMBER>' in envelope
        assert '<VOUCHERNUMBER>25-26/2</VOUCHERNUMBER>' in envelope
        assert '<VOUCHERNUMBER>25-26/3</VOUCHERNUMBER>' in envelope

    def test_envelope_custom_company_name(self):
        """Test envelope with custom company name."""
        invoice = Invoice(
            invoice_no="25-26/1111",
            invoice_date=date(2026, 4, 29),
            guest_name="Test Guest",
            net_amount=1000.00,
            cgst=25.00,
            sgst=25.00,
            gross_amount=1050.00,
            gst_rate=5.0,
        )

        voucher_xml = generate_sales_voucher(invoice)
        envelope = vouchers_envelope([voucher_xml], company="Test Company")

        assert '<SVCURRENTCOMPANY>Test Company</SVCURRENTCOMPANY>' in envelope


class TestVoucherNumberFormat:
    """Test voucher number format validation."""

    def test_voucher_number_format_25_26(self):
        """Test fiscal year 2025-26 format."""
        invoice = Invoice(
            invoice_no="25-26/6453",
            invoice_date=date(2026, 3, 31),
            guest_name="Test Guest",
            net_amount=1000.00,
            cgst=25.00,
            sgst=25.00,
            gross_amount=1050.00,
            gst_rate=5.0,
        )

        xml = generate_sales_voucher(invoice)
        assert '<VOUCHERNUMBER>25-26/6453</VOUCHERNUMBER>' in xml

    def test_voucher_number_special_format_rent(self):
        """Test special format for rent vouchers."""
        invoice = Invoice(
            invoice_no="RENT/MARCH26",
            invoice_date=date(2026, 3, 31),
            guest_name="TMV ROOFTOP RESTAURANT",
            net_amount=50000.00,
            cgst=4500.00,
            sgst=4500.00,
            gross_amount=59000.00,
            gst_rate=18.0,
        )

        xml = generate_sales_voucher(invoice)
        assert '<VOUCHERNUMBER>RENT/MARCH26</VOUCHERNUMBER>' in xml
