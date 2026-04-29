"""Tests for bank statement parser.

Tests all 4 column variants:
- 5-col (minimal): Value Date, Description, Debit Amount, Credit Amount, Balance
- 6-col (standard): + Chq No/REF No/UTR No
- 8-col (full): + Post Date, Remitter Branch
- 14-col (alternate): Date, Transaction Details, Debits, Credits, Balance
"""
from __future__ import annotations
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

# Add src to path for direct testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.etl.extract.bank import (
    find_header_row,
    extract_metadata,
    parse_date_str,
    parse_amount,
    extract_utr,
    clean_balance_suffix,
    parse_bank_statement,
)


class TestUtilityFunctions:
    """Test individual utility functions."""

    def test_parse_date_dd_mm_yyyy(self):
        """Test DD/MM/YYYY format."""
        assert parse_date_str("01/07/2025") == date(2025, 7, 1)
        assert parse_date_str("31/12/2025") == date(2025, 12, 31)

    def test_parse_date_dd_mon_yyyy(self):
        """Test DD Mon YYYY format."""
        assert parse_date_str("01 Jan 2026") == date(2026, 1, 1)
        assert parse_date_str("15 Mar 2026") == date(2026, 3, 15)

    def test_parse_date_iso_timestamp(self):
        """Test YYYY-MM-DD HH:MM:SS format."""
        assert parse_date_str("2026-03-01 00:00:00") == date(2026, 3, 1)
        assert parse_date_str("2026-03-15 14:30:00") == date(2026, 3, 15)

    def test_parse_date_invalid(self):
        """Test invalid date returns None."""
        assert parse_date_str(None) is None
        assert parse_date_str("") is None
        assert parse_date_str("invalid") is None

    def test_parse_amount_valid(self):
        """Test amount parsing."""
        assert parse_amount("1000.50") == Decimal("1000.50")
        assert parse_amount("35997.98") == Decimal("35997.98")
        assert parse_amount("1,234.56") == Decimal("1234.56")

    def test_parse_amount_blank(self):
        """Test blank amount returns 0."""
        assert parse_amount("") == Decimal(0)
        assert parse_amount(None) == Decimal(0)
        assert parse_amount(pd.NA) == Decimal(0)

    def test_clean_balance_with_cr_suffix(self):
        """Test balance with CR suffix."""
        amount, bal_type = clean_balance_suffix("894825.55CR")
        assert amount == Decimal("894825.55")
        assert bal_type == "CR"

    def test_clean_balance_with_dr_suffix(self):
        """Test balance with DR suffix."""
        amount, bal_type = clean_balance_suffix("1234.56 DR")
        assert amount == Decimal("1234.56")
        assert bal_type == "DR"

    def test_clean_balance_with_currency_prefix(self):
        """Test balance with INR prefix (14-col variant)."""
        amount, bal_type = clean_balance_suffix("INR 672,698.44")
        assert amount == Decimal("672698.44")
        assert bal_type == ""

    def test_extract_utr_from_column(self):
        """Test UTR extraction when column has value."""
        assert extract_utr("some desc", "YESBN12025070105404991") == "YESBN12025070105404991"

    def test_extract_utr_from_description(self):
        """Test UTR extraction from NEFT description."""
        desc = "BY TRANSFER NEFT/YESB/YESBN12025070105404991/ONE 97 COM/"
        assert extract_utr(desc, "") == "YESBN12025070105404991"

    def test_extract_utr_none(self):
        """Test UTR extraction when not present."""
        assert extract_utr("CASH DEPOSIT", "") == ""


class TestHeaderDetection:
    """Test header row detection for all variants."""

    def test_find_header_6col_standard(self):
        """Test finding header for 6-column standard format."""
        # Simulate rows from actual file
        data = {
            0: [None] * 6,
            19: ["Statement of Account from 01/07/2025 to 31/07/2025"] + [None] * 5,
            21: ["Value Date", "Description", "Chq No/REF No/UTR No", "Debit Amount", "Credit Amount", "Balance"],
        }
        df = pd.DataFrame(data).T

        header_row = find_header_row(df)
        assert header_row == 21

    def test_find_header_14col_alternate(self):
        """Test finding header for 14-column alternate format."""
        data = {
            0: [None] * 14,
            36: ["Date", "Transaction Details"] + [None] * 12,
        }
        df = pd.DataFrame(data).T

        header_row = find_header_row(df)
        assert header_row == 36

    def test_find_header_compact(self):
        """Test finding header for compact format (rows ~12)."""
        data = {
            0: [None] * 6,
            12: ["Txn Date", "Description", "Cheque No", "Debit Amount", "Credit Amount", "Balance"],
        }
        df = pd.DataFrame(data).T

        header_row = find_header_row(df)
        assert header_row == 12

    def test_find_header_not_found(self):
        """Test when header is not found."""
        data = {i: [None] * 6 for i in range(30)}
        df = pd.DataFrame(data).T

        header_row = find_header_row(df)
        assert header_row is None


class TestMetadataExtraction:
    """Test metadata extraction from header rows."""

    def test_extract_metadata_standard_format(self):
        """Test metadata extraction from standard format."""
        # Simulate rows 0-20 from actual file
        data = [
            ["", "INDIAN BANK"],
            ["", "UDAIPUR GOVERDHAN"],
            ["", "IFSC CODE :IDIB000U506"],
            ["Account Number : 7223534417"],
            ["Statement Date :Fri Aug 08 14:03:50 IST 2025"],
            ["Cleared Balance :894825.55"],
            ["Statement of Account from 01/07/2025 to 31/07/2025"],
        ]
        df = pd.DataFrame(data)

        meta = extract_metadata(df, Path("/test/file.xlsx"))

        assert meta.account_number == "7223534417"
        assert meta.ifsc_code == "IDIB000U506"
        assert meta.cleared_balance == "894825.55"
        assert "01/07/2025" in meta.date_range


class TestFullParsing:
    """Integration tests parsing actual file structures."""

    @pytest.fixture
    def sample_6col_file(self, tmp_path):
        """Create sample 6-column bank statement."""
        # Create DataFrame with metadata rows + transactions
        rows = []

        # Metadata rows (0-20)
        for i in range(21):
            if i == 6:
                rows.append({"col0": "Account Number : 7223534417", "col1": None, "col2": None, "col3": None, "col4": None, "col5": None})
            elif i == 15:
                rows.append({"col0": "Cleared Balance :894825.55", "col1": None, "col2": None, "col3": None, "col4": None, "col5": None})
            elif i == 19:
                rows.append({"col0": "Statement of Account from 01/07/2025 to 31/07/2025", "col1": None, "col2": None, "col3": None, "col4": None, "col5": None})
            else:
                rows.append({"col0": None, "col1": None, "col2": None, "col3": None, "col4": None, "col5": None})

        # Header row (21)
        rows.append({
            "col0": "Value Date",
            "col1": "Description",
            "col2": "Chq No/REF No/UTR No",
            "col3": "Debit Amount",
            "col4": "Credit Amount",
            "col5": "Balance"
        })

        # Transaction rows
        rows.append({
            "col0": "01/07/2025",
            "col1": "BY TRANSFER NEFT/YESB/YESBN12025070105404991/ONE 97 COM/",
            "col2": "YESBN12025070105404991",
            "col3": None,
            "col4": 35997.98,
            "col5": "470414.15CR"
        })
        rows.append({
            "col0": "02/07/2025",
            "col1": "CASH WITHDRAWAL",
            "col2": None,
            "col3": 5000.00,
            "col4": None,
            "col5": "465414.15CR"
        })

        df = pd.DataFrame(rows)
        file_path = tmp_path / "test_statement.xlsx"
        df.to_excel(file_path, index=False, header=False)

        return file_path

    def test_parse_6col_statement(self, sample_6col_file):
        """Test parsing 6-column statement end-to-end."""
        payments, metadata, stats = parse_bank_statement(sample_6col_file)

        # Check metadata
        assert metadata.account_number == "7223534417"
        assert metadata.cleared_balance == "894825.55"

        # Check stats
        assert stats['variant'] == "6-col (standard)"
        assert stats['parsed_count'] == 2
        assert stats['with_utr'] == 1

        # Check payments
        assert len(payments) == 2

        # First payment (credit)
        p1 = payments[0]
        assert p1.txn_date == date(2025, 7, 1)
        assert p1.gross_amount == Decimal("35997.98")
        assert p1.utr == "YESBN12025070105404991"
        assert p1.payment_mode == "BANK_TRANSFER"
        assert p1.source == "bank"

        # Second payment (debit)
        p2 = payments[1]
        assert p2.txn_date == date(2025, 7, 2)
        assert p2.gross_amount == Decimal("-5000.00")
        assert p2.utr == ""


class TestColumnVariants:
    """Test detection of all 4 column variants."""

    def test_detect_5col_minimal(self):
        """Test 5-column detection."""
        df = pd.DataFrame(columns=["Value Date", "Description", "Debit Amount", "Credit Amount", "Balance"])
        from tmv_recon.etl.extract.bank import detect_column_variant
        assert detect_column_variant(df) == "5-col (minimal)"

    def test_detect_6col_standard(self):
        """Test 6-column detection."""
        df = pd.DataFrame(columns=["Value Date", "Description", "Chq No/REF No/UTR No", "Debit Amount", "Credit Amount", "Balance"])
        from tmv_recon.etl.extract.bank import detect_column_variant
        assert detect_column_variant(df) == "6-col (standard)"

    def test_detect_8col_full(self):
        """Test 8-column detection."""
        df = pd.DataFrame(columns=["Value Date", "Post Date", "Remitter Branch", "Description", "Chq No/REF No/UTR No", "Debit Amount", "Credit Amount", "Balance"])
        from tmv_recon.etl.extract.bank import detect_column_variant
        assert detect_column_variant(df) == "8-col (full)"

    def test_detect_14col_alternate(self):
        """Test 14-column detection."""
        df = pd.DataFrame(columns=["Date", "Transaction Details"] + [f"Col{i}" for i in range(12)])
        from tmv_recon.etl.extract.bank import detect_column_variant
        assert detect_column_variant(df) == "14-col (alternate)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
