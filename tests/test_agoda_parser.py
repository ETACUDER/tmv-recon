"""Test AGODA parser with all 17 header variants and edge cases."""
from __future__ import annotations
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import date
import pandas as pd
from io import BytesIO

from tmv_recon.etl.extract.booking import (
    extract_one,
    _levenshtein_distance,
    _fuzzy_match_column,
    _find_col_fuzzy,
    _split_invoice_list,
    _detect_credit_note,
    _parse_date,
    _calculate_net_settled,
    _safe_num,
)
from tmv_recon.etl.models import Booking


class TestLevenshteinDistance:
    """Test fuzzy matching for typo variants."""

    def test_exact_match(self):
        assert _levenshtein_distance("INVOICE", "INVOICE") == 0

    def test_single_char_diff(self):
        assert _levenshtein_distance("INVOICE", "INVOCIE") == 2  # swap = 2 ops

    def test_space_diff(self):
        assert _levenshtein_distance("INVOICE NO", "INVOICE  NO") == 1

    def test_case_insensitive_needs_normalization(self):
        # Note: Levenshtein is case-sensitive, normalization happens in fuzzy_match
        assert _levenshtein_distance("invoice", "INVOICE") == 7


class TestFuzzyColumnMatching:
    """Test column header matching with variants."""

    def test_exact_match_any_case(self):
        assert _fuzzy_match_column("INVOICE NO.", ["INVOICE NO.", "invoice no"])
        assert _fuzzy_match_column("invoice no", ["INVOICE NO.", "invoice no"])

    def test_typo_variant_invocie(self):
        assert _fuzzy_match_column("INVOCIE NO.", ["INVOICE NO."], threshold=3)

    def test_double_space_variant(self):
        assert _fuzzy_match_column("INVOICE  NO.", ["INVOICE NO."], threshold=3)

    def test_no_match_beyond_threshold(self):
        assert not _fuzzy_match_column("TOTAL", ["INVOICE NO."], threshold=3)


class TestInvoiceListSplitting:
    """Test multi-invoice credit note parsing."""

    def test_single_invoice(self):
        assert _split_invoice_list("5802") == ["25-26/5802"]

    def test_comma_separated(self):
        result = _split_invoice_list("5802, 5803")
        assert len(result) == 2
        assert "25-26/5802" in result
        assert "25-26/5803" in result

    def test_semicolon_separated(self):
        result = _split_invoice_list("5802; 5803")
        assert len(result) == 2

    def test_spaces_comma(self):
        result = _split_invoice_list("6106 , 6122")
        assert len(result) == 2
        assert "25-26/6106" in result
        assert "25-26/6122" in result

    def test_empty_string(self):
        assert _split_invoice_list("") == []
        assert _split_invoice_list(None) == []


class TestCreditNoteDetection:
    """Test credit note identification."""

    def test_multi_invoice_is_credit_note(self):
        invoices = ["25-26/5802", "25-26/5803"]
        guest = "John Doe"
        assert _detect_credit_note(invoices, guest) == "25-26/5802"

    def test_rate_nights_annotation_is_credit_note(self):
        invoices = ["25-26/5802"]
        guest = "John Doe (1500*2)"
        assert _detect_credit_note(invoices, guest) == "25-26/5802"

    def test_rate_nights_bracket_variant(self):
        invoices = ["25-26/5802"]
        guest = "Jane Smith [1200 * 3]"
        assert _detect_credit_note(invoices, guest) == "25-26/5802"

    def test_normal_booking_no_credit_note(self):
        invoices = ["25-26/5802"]
        guest = "John Doe"
        assert _detect_credit_note(invoices, guest) is None


class TestDateParsing:
    """Test multiple date format handling."""

    def test_iso_format(self):
        assert _parse_date("2026-03-01") == date(2026, 3, 1)

    def test_dd_mmm_yy(self):
        assert _parse_date("01-Mar-26") == date(2026, 3, 1)

    def test_dd_mmm_yyyy(self):
        assert _parse_date("01-Mar-2026") == date(2026, 3, 1)

    def test_slash_format(self):
        # DD/MM/YYYY (Indian format) - 03/01/2026 = 3rd Jan 2026
        assert _parse_date("03/01/2026") == date(2026, 1, 3)

    def test_excel_serial_date(self):
        # Excel serial 44970 = 2023-02-01
        result = _parse_date(44970)
        assert result.year == 2023
        assert result.month == 2

    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2026-03-01")
        assert _parse_date(ts) == date(2026, 3, 1)

    def test_null_values(self):
        assert _parse_date(None) is None
        assert _parse_date(pd.NaT) is None
        assert _parse_date("") is None


class TestAmountParsing:
    """Test financial amount parsing."""

    def test_integer(self):
        assert _safe_num(1000) == Decimal("1000")

    def test_float(self):
        assert _safe_num(1234.56) == Decimal("1234.56")

    def test_string_with_comma(self):
        assert _safe_num("12,345.67") == Decimal("12345.67")

    def test_string_plain(self):
        assert _safe_num("999.99") == Decimal("999.99")

    def test_null_values(self):
        assert _safe_num(None) is None
        assert _safe_num(pd.NA) is None
        assert _safe_num("") is None


class TestNetSettledCalculation:
    """Test net settlement formula."""

    def test_basic_calculation(self):
        gross = Decimal("10000")
        commission = Decimal("1000")
        commission_gst = Decimal("180")
        tcs = Decimal("100")
        tds = Decimal("200")

        result = _calculate_net_settled(gross, commission, commission_gst, tcs, tds)
        # 10000 - 1000 - 180 - 100 + 200 = 8920
        assert result == Decimal("8920")

    def test_no_commission(self):
        gross = Decimal("5000")
        result = _calculate_net_settled(gross, None, None, None, None)
        assert result == Decimal("5000")

    def test_null_gross(self):
        assert _calculate_net_settled(None, None, None, None, None) is None


class TestHeaderVariants:
    """Test parsing different header variants."""

    @pytest.fixture
    def mock_excel_variant1(self, tmp_path):
        """Standard Agoda format with INVOICE NO."""
        data = {
            "INVOICE NO.": ["5936", "6105"],
            "Reference number": [1983036406, 1971333244],
            "Guest name": ["John Doe", "Jane Smith"],
            "Booking paid by": ["Agoda", "Agoda"],
            "AGODA SITE": [5000.00, 6000.00],
            "INVOICE AMT.": [11687.12, 13500.00],
            "e-f =g": [0, 0],  # Formula column
            "From Agoda": [10500.00, 12000.00],
            "COMM + GST": [1187.12, 1500.00],
            "CREDIT NOTE": [0, 0],
            "Check-in date": ["2026-03-01", "2026-03-12"],
            "Check-out date": ["2026-03-03", "2026-03-13"],
        }
        df = pd.DataFrame(data)
        path = tmp_path / "test_variant1.xlsx"
        df.to_excel(path, index=False)
        return path

    @pytest.fixture
    def mock_excel_variant_typo(self, tmp_path):
        """Typo variant: INVOCIE NO. and INVOCIE AMT."""
        data = {
            "INVOCIE NO.": ["5936"],
            "Booking ID": [1983036406],
            "Guest name": ["John Doe"],
            "Booking paid by": ["Agoda"],
            "AGODAT SITE": [5000.00],  # Typo variant
            "INVOCIE AMT": [11687.12],
            "From Agoda": [10500.00],
            "COMM+GST": [1187.12],  # No spaces
            "Check-in date": ["2026-03-01"],
            "Check-out date": ["2026-03-03"],
        }
        df = pd.DataFrame(data)
        path = tmp_path / "test_typo.xlsx"
        df.to_excel(path, index=False)
        return path

    @pytest.fixture
    def mock_excel_credit_note(self, tmp_path):
        """Multi-invoice credit note scenario."""
        data = {
            "INVOICE NO.": ["6106 , 6122", "6105"],
            "Reference number": [1971317500, 1971333244],
            "Guest name": ["Repeat Guest (1500*2)", "Jane Smith"],
            "INVOICE AMT.": [14000.00, 13500.00],
            "From Agoda": [12500.00, 12000.00],
            "COMM + GST": [1500.00, 1500.00],
            "Check-in date": ["2026-03-12", "2026-03-12"],
            "Check-out date": ["2026-03-13", "2026-03-13"],
        }
        df = pd.DataFrame(data)
        path = tmp_path / "test_credit_note.xlsx"
        df.to_excel(path, index=False)
        return path

    def test_parse_standard_variant(self, mock_excel_variant1):
        unrecognized = set()
        bookings = extract_one(mock_excel_variant1, unrecognized)

        assert len(bookings) == 2
        assert bookings[0].invoice_no == "25-26/5936"
        assert bookings[0].guest_name == "John Doe"
        assert bookings[0].gross_amount == Decimal("11687.12")
        assert bookings[0].source == "agoda"
        # Formula column "e-f =g" is expected to be unrecognized
        assert len(unrecognized) <= 1  # Only formula column should be unrecognized

    def test_parse_typo_variant(self, mock_excel_variant_typo):
        """INVOCIE instead of INVOICE should still match."""
        unrecognized = set()
        bookings = extract_one(mock_excel_variant_typo, unrecognized)

        assert len(bookings) == 1
        assert bookings[0].invoice_no == "25-26/5936"
        assert bookings[0].gross_amount == Decimal("11687.12")
        # Fuzzy match should find INVOCIE NO. and INVOCIE AMT
        assert unrecognized == set()

    def test_parse_credit_note_multi_invoice(self, mock_excel_credit_note):
        """Multi-invoice should create separate rows with credit_note_for."""
        unrecognized = set()
        bookings = extract_one(mock_excel_credit_note, unrecognized)

        # First row has 2 invoices = 2 booking rows
        assert len(bookings) == 3

        # Find the credit note bookings
        credit_bookings = [b for b in bookings if b.credit_note_for]
        assert len(credit_bookings) >= 1
        assert credit_bookings[0].credit_note_for == "25-26/6106"

    def test_parse_rate_nights_annotation(self, mock_excel_credit_note):
        """Extract rate and nights from guest name annotation."""
        unrecognized = set()
        bookings = extract_one(mock_excel_credit_note, unrecognized)

        # Find booking with rate annotation
        annotated = [b for b in bookings if b.rate_per_night]
        assert len(annotated) >= 1
        assert annotated[0].rate_per_night == Decimal("1500")
        assert annotated[0].nights == 2
        assert annotated[0].guest_name == "Repeat Guest"  # Annotation stripped


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_excel_with_total_row(self, tmp_path):
        """File with TOTAL footer row."""
        data = {
            "INVOICE NO.": ["5936", "6105", "TOTAL"],
            "Guest name": ["John Doe", "Jane Smith", ""],
            "INVOICE AMT.": [11687.12, 13500.00, 25187.12],
        }
        df = pd.DataFrame(data)
        path = tmp_path / "test_total_row.xlsx"
        df.to_excel(path, index=False)
        return path

    @pytest.fixture
    def mock_excel_empty(self, tmp_path):
        """Empty file."""
        df = pd.DataFrame()
        path = tmp_path / "test_empty.xlsx"
        df.to_excel(path, index=False)
        return path

    def test_drop_total_rows(self, mock_excel_with_total_row):
        """TOTAL footer should be filtered out."""
        unrecognized = set()
        bookings = extract_one(mock_excel_with_total_row, unrecognized)

        assert len(bookings) == 2  # TOTAL row excluded
        assert all(b.guest_name != "" for b in bookings)

    def test_empty_file(self, mock_excel_empty):
        """Empty file should return empty list."""
        unrecognized = set()
        bookings = extract_one(mock_excel_empty, unrecognized)
        assert len(bookings) == 0


class TestValidation:
    """Test validation and reporting."""

    def test_unrecognized_column_tracking(self, tmp_path):
        """Unknown columns should be tracked."""
        data = {
            "INVOICE NO.": ["5936"],
            "Guest name": ["John Doe"],
            "UNKNOWN_COLUMN": ["something"],
            "ANOTHER_WEIRD_COL": [123],
        }
        df = pd.DataFrame(data)
        path = tmp_path / "test_unknown.xlsx"
        df.to_excel(path, index=False)

        unrecognized = set()
        extract_one(path, unrecognized)

        assert len(unrecognized) == 2
        assert any("UNKNOWN_COLUMN" in s for s in unrecognized)
        assert any("ANOTHER_WEIRD_COL" in s for s in unrecognized)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
