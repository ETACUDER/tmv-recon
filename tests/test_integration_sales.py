"""Integration test for Sales voucher generation workflow.

Tests complete workflow: Invoice data → Voucher generation → XML validation.
"""
import sys
from pathlib import Path
from datetime import date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.tally.voucher_generators import (
    Invoice,
    generate_sales_voucher,
    vouchers_envelope,
    calculate_gst_split,
)


def test_complete_workflow():
    """Test complete workflow from invoice to XML."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Complete Sales Voucher Workflow")
    print("=" * 70)

    # Step 1: Create invoices
    print("\nStep 1: Create invoice data")
    invoices = [
        Invoice(
            invoice_no="25-26/6453",
            invoice_date=date(2026, 3, 31),
            guest_name="Mrs. Madhur Piparsania",
            net_amount=2984.19,
            cgst=74.60,
            sgst=74.60,
            gross_amount=3133.39,
            gst_rate=5.0,
        ),
        Invoice(
            invoice_no="25-26/7000",
            invoice_date=date(2026, 4, 15),
            guest_name="Mr. John O'Brien & Sons",  # Special chars
            net_amount=4761.90,
            cgst=119.05,
            sgst=119.05,
            gross_amount=5000.00,
            gst_rate=5.0,
        ),
        Invoice(
            invoice_no="RENT/MARCH26",
            invoice_date=date(2026, 3, 31),
            guest_name="TMV Rooftop Restaurant",
            net_amount=50000.00,
            cgst=4500.00,
            sgst=4500.00,
            gross_amount=59000.00,
            gst_rate=18.0,
        ),
    ]
    print(f"  ✓ Created {len(invoices)} invoices")

    # Step 2: Generate vouchers
    print("\nStep 2: Generate voucher XML")
    voucher_xmls = []
    for inv in invoices:
        try:
            voucher = generate_sales_voucher(inv)
            voucher_xmls.append(voucher)
            print(f"  ✓ Generated: {inv.invoice_no}")
        except Exception as e:
            print(f"  ✗ Failed: {inv.invoice_no} - {e}")
            raise

    assert len(voucher_xmls) == 3, "Should generate 3 vouchers"

    # Step 3: Create envelope
    print("\nStep 3: Create XML envelope")
    envelope = vouchers_envelope(voucher_xmls)
    print(f"  ✓ Envelope size: {len(envelope):,} bytes")

    # Step 4: Validate structure
    print("\nStep 4: Validate XML structure")

    # Check XML declaration
    assert envelope.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    print("  ✓ XML declaration present")

    # Check envelope structure
    assert "<ENVELOPE>" in envelope
    assert "<HEADER>" in envelope
    assert "<TALLYREQUEST>Import</TALLYREQUEST>" in envelope
    assert "<ID>Vouchers</ID>" in envelope
    assert "<BODY>" in envelope
    assert "<DATA>" in envelope
    print("  ✓ Envelope structure valid")

    # Check company name
    assert "<SVCURRENTCOMPANY>THE MANGAL VIEW RESIDENCY Final</SVCURRENTCOMPANY>" in envelope
    print("  ✓ Company name set")

    # Check voucher count
    assert envelope.count('<TALLYMESSAGE xmlns:UDF="TallyUDF">') == 3
    print("  ✓ All 3 vouchers included")

    # Step 5: Validate voucher content
    print("\nStep 5: Validate voucher content")

    # Check LEDGERENTRIES.LIST usage
    assert envelope.count("<LEDGERENTRIES.LIST>") == 12  # 4 entries × 3 vouchers
    assert "<ALLLEDGERENTRIES.LIST>" not in envelope
    print("  ✓ Uses LEDGERENTRIES.LIST (not ALLLEDGERENTRIES.LIST)")

    # Check ledgers
    assert "Sundry Debtors" in envelope
    assert "SALE ACCOMODATION GST @ 5 %" in envelope
    assert "RENTAL INCOME GST @ 18%" in envelope
    assert "CGST" in envelope
    assert "SGST" in envelope
    print("  ✓ All required ledgers present")

    # Check sign conventions
    assert "<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>" in envelope  # Debit
    assert "<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>" in envelope  # Credit
    print("  ✓ Sign conventions present")

    # Check amounts (sample)
    assert "<AMOUNT>3133.39</AMOUNT>" in envelope  # Dr Sundry Debtors
    assert "<AMOUNT>-2984.19</AMOUNT>" in envelope  # Cr Income
    assert "<AMOUNT>-74.60</AMOUNT>" in envelope  # Cr GST
    print("  ✓ Amounts formatted correctly")

    # Check narrations
    assert "INVOICE NO:-25-26/6453 MRS. MADHUR PIPARSANIA" in envelope.upper()
    assert "INVOICE NO:-RENT/MARCH26" in envelope.upper()
    print("  ✓ Narrations formatted correctly")

    # Check XML escaping for special chars
    assert "&apos;" in envelope and "&amp;" in envelope  # Check escaping present
    print("  ✓ Special characters escaped")

    # Check party ledger
    assert envelope.count("<PARTYLEDGERNAME>Sundry Debtors</PARTYLEDGERNAME>") == 3
    assert envelope.count("<ISPARTYLEDGER>Yes</ISPARTYLEDGER>") == 3
    print("  ✓ Party ledger configured")

    # Step 6: Validate GST calculation helper
    print("\nStep 6: Test GST calculation helper")
    net, cgst, sgst = calculate_gst_split(5250.00, gst_rate=5.0)
    assert net == 5000.00
    assert cgst == 125.00
    assert sgst == 125.00
    assert abs((net + cgst + sgst) - 5250.00) < 0.01
    print("  ✓ GST calculation accurate")

    # Step 7: Test validation
    print("\nStep 7: Test amount validation")
    try:
        bad_invoice = Invoice(
            invoice_no="BAD/001",
            invoice_date=date.today(),
            guest_name="Test",
            net_amount=5000.00,
            cgst=250.00,
            sgst=250.00,
            gross_amount=6000.00,  # Mismatch
            gst_rate=5.0,
        )
        generate_sales_voucher(bad_invoice)
        print("  ✗ Validation should have failed")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "GST validation failed" in str(e)
        print(f"  ✓ Validation works: {str(e)[:50]}...")

    # Summary
    print("\n" + "=" * 70)
    print("INTEGRATION TEST RESULTS")
    print("=" * 70)
    print("  ✓ Invoice creation")
    print("  ✓ Voucher generation")
    print("  ✓ Envelope creation")
    print("  ✓ Structure validation")
    print("  ✓ Content validation")
    print("  ✓ GST calculation")
    print("  ✓ Amount validation")
    print("\n✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
    print("=" * 70)


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Edge Cases")
    print("=" * 70)

    # Test 1: Zero GST rate (calculate from amounts)
    print("\nTest 1: Calculate GST rate from amounts")
    invoice = Invoice(
        invoice_no="25-26/8888",
        invoice_date=date.today(),
        guest_name="Test Guest",
        net_amount=2000.00,
        cgst=100.00,
        sgst=100.00,
        gross_amount=2200.00,
        gst_rate=0.0,  # Not provided
    )
    xml = generate_sales_voucher(invoice)
    assert "SALE ACCOMODATION GST @ 5 %" in xml  # Should use 5% ledger
    print("  ✓ GST rate calculated and correct ledger selected")

    # Test 2: Tolerance boundary (within ₹1)
    print("\nTest 2: Validation tolerance (within ₹1)")
    invoice = Invoice(
        invoice_no="25-26/9999",
        invoice_date=date.today(),
        guest_name="Test Guest",
        net_amount=5000.00,
        cgst=250.00,
        sgst=250.00,
        gross_amount=5500.75,  # Off by 0.75
        gst_rate=5.0,
    )
    xml = generate_sales_voucher(invoice)
    assert "<AMOUNT>5500.75</AMOUNT>" in xml
    print("  ✓ Validation passes within tolerance")

    # Test 3: Empty guest name
    print("\nTest 3: Empty guest name handling")
    invoice = Invoice(
        invoice_no="25-26/7777",
        invoice_date=date.today(),
        guest_name="",  # Empty
        net_amount=1000.00,
        cgst=25.00,
        sgst=25.00,
        gross_amount=1050.00,
        gst_rate=5.0,
    )
    xml = generate_sales_voucher(invoice)
    assert "INVOICE NO:-25-26/7777" in xml
    print("  ✓ Handles empty guest name")

    # Test 4: Very small amounts (paisa precision)
    print("\nTest 4: Paisa precision")
    invoice = Invoice(
        invoice_no="25-26/6666",
        invoice_date=date.today(),
        guest_name="Test",
        net_amount=95.24,
        cgst=2.38,
        sgst=2.38,
        gross_amount=100.00,
        gst_rate=5.0,
    )
    xml = generate_sales_voucher(invoice)
    assert "<AMOUNT>-95.24</AMOUNT>" in xml
    assert "<AMOUNT>-2.38</AMOUNT>" in xml
    print("  ✓ Handles paisa-level precision")

    # Test 5: Large amounts
    print("\nTest 5: Large amounts")
    invoice = Invoice(
        invoice_no="25-26/5555",
        invoice_date=date.today(),
        guest_name="Corporate Client",
        net_amount=95238.10,
        cgst=4761.90,
        sgst=4761.90,
        gross_amount=104761.90,
        gst_rate=10.0,
    )
    xml = generate_sales_voucher(invoice)
    assert "<AMOUNT>104761.90</AMOUNT>" in xml
    print("  ✓ Handles large amounts")

    print("\n" + "=" * 70)
    print("✓✓✓ ALL EDGE CASE TESTS PASSED ✓✓✓")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_complete_workflow()
        test_edge_cases()
        print("\n" + "=" * 70)
        print("✓✓✓ ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY ✓✓✓")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print(f"\n✗✗✗ INTEGRATION TEST FAILED ✗✗✗")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
