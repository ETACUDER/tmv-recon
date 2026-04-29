"""Tests for ground truth comparison module."""
from __future__ import annotations
import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path

from tmv_recon.etl.ground_truth import (
    parse_tally_vouchers,
    parse_generated_vouchers,
    compare_vouchers,
    compare_narrations,
    extract_invoice_no,
    find_best_match,
    TallyVoucher,
    LedgerEntry,
    filter_vouchers_by_date
)


def test_extract_invoice_no():
    """Test invoice number extraction from various formats."""
    assert extract_invoice_no("INVOICE NO:-25-26/6453 MRS. MADHUR") == "25-26/6453"
    assert extract_invoice_no("25-26/5924") == "25-26/5924"
    assert extract_invoice_no("BEING PAID THROUGH UPI AGAINST INVOICE NO:25-26/5924") == "25-26/5924"
    assert extract_invoice_no("INV 25-26/1234") == "25-26/1234"
    assert extract_invoice_no("No invoice here") is None
    assert extract_invoice_no("") is None


def test_compare_narrations():
    """Test narration comparison with fuzzy matching."""
    # Exact match
    assert compare_narrations(
        "INVOICE NO:-25-26/6453 MRS. MADHUR",
        "INVOICE NO:-25-26/6453 MRS. MADHUR"
    )

    # Case and whitespace differences
    assert compare_narrations(
        "invoice no:-25-26/6453 mrs. madhur",
        "INVOICE NO:-25-26/6453  MRS. MADHUR"
    )

    # Invoice number match is sufficient
    assert compare_narrations(
        "INVOICE NO:-25-26/6453 JOHN DOE",
        "INV: 25-26/6453 JANE DOE"
    )

    # Different invoice numbers
    assert not compare_narrations(
        "INVOICE NO:-25-26/6453",
        "INVOICE NO:-25-26/1234"
    )

    # Empty strings
    assert compare_narrations("", "")
    assert not compare_narrations("something", "")


def test_voucher_totals():
    """Test voucher total calculation."""
    voucher = TallyVoucher(
        guid="test-guid",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test narration",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000"), "No"),  # Debit
            LedgerEntry("SALE ACCOMODATION GST @ 5%", Decimal("-9523.81"), "Yes"),  # Credit
            LedgerEntry("CGST", Decimal("-238.10"), "Yes"),  # Credit
            LedgerEntry("SGST", Decimal("-238.09"), "Yes"),  # Credit
        ]
    )

    assert voucher.total_debit == Decimal("10000")
    assert voucher.total_credit == Decimal("10000")  # Sum of absolute values


def test_compare_vouchers_perfect_match():
    """Test comparing two identical vouchers."""
    voucher1 = TallyVoucher(
        guid="guid1",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="INVOICE NO:-25-26/6453 MRS. MADHUR",
        party_ledger_name="Sundry Debtors",
        reference="25-26/6453",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000"), "No"),
            LedgerEntry("SALE ACCOMODATION GST @ 5%", Decimal("-9523.81"), "Yes"),
        ]
    )

    voucher2 = TallyVoucher(
        guid="guid2",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="INVOICE NO:-25-26/6453 MRS. MADHUR",
        party_ledger_name="Sundry Debtors",
        reference="25-26/6453",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000"), "No"),
            LedgerEntry("SALE ACCOMODATION GST @ 5%", Decimal("-9523.81"), "Yes"),
        ]
    )

    result = compare_vouchers(voucher1, voucher2)

    assert result.match_score == 1.0
    assert result.voucher_type_match
    assert result.ledger_names_match
    assert result.amount_match
    assert result.narration_pattern_match
    assert len(result.differences) == 0


def test_compare_vouchers_amount_tolerance():
    """Test amount comparison with ₹1 tolerance."""
    voucher1 = TallyVoucher(
        guid="guid1",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000.50"), "No"),
        ]
    )

    voucher2 = TallyVoucher(
        guid="guid2",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000.00"), "No"),
        ]
    )

    result = compare_vouchers(voucher1, voucher2)

    # Within ₹1 tolerance
    assert result.amount_match
    assert result.match_score >= 0.95


def test_compare_vouchers_type_mismatch():
    """Test voucher type mismatch."""
    voucher1 = TallyVoucher(
        guid="guid1",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[LedgerEntry("Sundry Debtors", Decimal("10000"), "No")]
    )

    voucher2 = TallyVoucher(
        guid="guid2",
        voucher_type="Journal",  # Different type
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[LedgerEntry("Sundry Debtors", Decimal("10000"), "No")]
    )

    result = compare_vouchers(voucher1, voucher2)

    assert not result.voucher_type_match
    assert "Voucher type: Sales != Journal" in result.differences
    assert result.match_score < 1.0


def test_compare_vouchers_ledger_mismatch():
    """Test ledger name mismatch."""
    voucher1 = TallyVoucher(
        guid="guid1",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000"), "No"),
            LedgerEntry("SALE ACCOMODATION GST @ 5%", Decimal("-10000"), "Yes"),
        ]
    )

    voucher2 = TallyVoucher(
        guid="guid2",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="Test",
        party_ledger_name="Sundry Debtors",
        reference="",
        ledger_entries=[
            LedgerEntry("Sundry Debtors", Decimal("10000"), "No"),
            LedgerEntry("RENTAL INCOME GST @ 18%", Decimal("-10000"), "Yes"),  # Different ledger
        ]
    )

    result = compare_vouchers(voucher1, voucher2)

    assert not result.ledger_names_match
    assert any("Missing ledgers" in d for d in result.differences)
    assert result.match_score < 1.0


def test_find_best_match_invoice_number():
    """Test finding best match by invoice number."""
    actual = TallyVoucher(
        guid="guid1",
        voucher_type="Sales",
        voucher_number="25-26/6453",
        date=date(2026, 3, 31),
        narration="INVOICE NO:-25-26/6453",
        party_ledger_name="Sundry Debtors",
        reference="25-26/6453",
        ledger_entries=[],
        invoice_no_pattern="25-26/6453"
    )

    candidates = [
        TallyVoucher(
            guid="guid2",
            voucher_type="Sales",
            voucher_number="25-26/5924",
            date=date(2026, 3, 30),
            narration="INVOICE NO:-25-26/5924",
            party_ledger_name="Sundry Debtors",
            reference="25-26/5924",
            ledger_entries=[],
            invoice_no_pattern="25-26/5924"
        ),
        TallyVoucher(
            guid="guid3",
            voucher_type="Sales",
            voucher_number="25-26/6453",
            date=date(2026, 3, 31),
            narration="INVOICE NO:-25-26/6453",
            party_ledger_name="Sundry Debtors",
            reference="25-26/6453",
            ledger_entries=[],
            invoice_no_pattern="25-26/6453"
        ),
    ]

    match, score, index = find_best_match(actual, candidates, set())

    assert match is not None
    assert match.invoice_no_pattern == "25-26/6453"
    assert index == 1


def test_filter_vouchers_by_date():
    """Test filtering vouchers by date range."""
    vouchers = [
        TallyVoucher(
            guid="1",
            voucher_type="Sales",
            voucher_number="1",
            date=date(2026, 2, 28),
            narration="",
            party_ledger_name="",
            reference=""
        ),
        TallyVoucher(
            guid="2",
            voucher_type="Sales",
            voucher_number="2",
            date=date(2026, 3, 15),
            narration="",
            party_ledger_name="",
            reference=""
        ),
        TallyVoucher(
            guid="3",
            voucher_type="Sales",
            voucher_number="3",
            date=date(2026, 4, 1),
            narration="",
            party_ledger_name="",
            reference=""
        ),
    ]

    filtered = filter_vouchers_by_date(
        vouchers,
        date(2026, 3, 1),
        date(2026, 3, 31)
    )

    assert len(filtered) == 1
    assert filtered[0].voucher_number == "2"


@pytest.mark.skipif(
    not Path("data/tally/raw_xml/daybook_FY25-26.xml").exists(),
    reason="Test data not available"
)
def test_parse_real_daybook():
    """Integration test: parse real Tally daybook XML."""
    vouchers = parse_tally_vouchers("data/tally/raw_xml/daybook_FY25-26.xml")

    assert len(vouchers) > 0

    # Check first voucher has expected structure
    v = vouchers[0]
    assert v.voucher_type in ["Sales", "Journal", "Purchase", "Receipt", "Credit Note"]
    assert v.voucher_number
    assert v.date.year >= 2026
    assert len(v.ledger_entries) > 0

    # Check ledger entries
    for entry in v.ledger_entries:
        assert entry.ledger_name
        assert entry.is_deemed_positive in ["Yes", "No"]

    # Check balance (should sum to zero, within ₹1)
    total = sum(e.amount for e in v.ledger_entries)
    assert abs(total) <= Decimal("1.0")
