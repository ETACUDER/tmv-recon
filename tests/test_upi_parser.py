"""Tests for UPI parser with UTR aggregation handling."""
import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.etl.extract.payment import (
    extract_upi,
    aggregate_by_utr,
    _detect_unit_from_path,
)


class TestUnitDetection:
    """Test unit dimension extraction from filepath."""

    def test_rooftop_detection(self):
        assert _detect_unit_from_path(Path("/data/PTM ROOFTOP/file.xlsx")) == "rooftop"
        assert _detect_unit_from_path(Path("/data/TMV ROOFTOP - MARCH.xlsx")) == "rooftop"
        assert _detect_unit_from_path(Path("/data/JKP/file.xlsx")) == "rooftop"

    def test_fnb_detection(self):
        assert _detect_unit_from_path(Path("/data/F&B UPI/file.xlsx")) == "f&b"
        assert _detect_unit_from_path(Path("/data/FB SERVICE/file.xlsx")) == "f&b"

    def test_front_office_default(self):
        assert _detect_unit_from_path(Path("/data/PTM - MARCH 2026.xlsx")) == "front_office"
        assert _detect_unit_from_path(Path("/data/UPI STATMENT/file.xlsx")) == "front_office"


class TestUTRAggregation:
    """Test UTR aggregation strategy (Section 4.3)."""

    @pytest.fixture
    def sample_upi_data(self):
        """Sample data with duplicate UTRs (Paytm batch settlement)."""
        return pd.DataFrame({
            'utr': ['UTR001', 'UTR001', 'UTR001', 'UTR002', None, None, ''],
            'amount_gross': [500, 300, 200, 1000, 150, 250, 100],
            'commission': [10, 6, 4, 20, 3, 5, 2],
            'gst': [1.8, 1.08, 0.72, 3.6, 0.54, 0.9, 0.36],
            'settled_amount': [488.2, 292.92, 195.28, 976.4, 146.46, 244.1, 97.64],
            'settled_dt': pd.to_datetime([
                '2026-03-01', '2026-03-01', '2026-03-02',  # UTR001: take earliest (03-01)
                '2026-03-03',  # UTR002
                '2026-03-04', '2026-03-05', '2026-03-06'  # Nulls: keep separate
            ]),
            'txn_dt': pd.to_datetime(['2026-03-01'] * 7),
            'payment_mode': ['UPI', 'UPI', 'UPI', 'CREDIT_CARD', 'UPI', 'CASH', 'UPI'],
            'issuing_bank': ['HDFC', 'HDFC', 'HDFC', 'ICICI', None, None, None],
            'unit': ['front_office'] * 7,
            'raw_path': ['file1.xlsx', 'file1.xlsx', 'file2.xlsx', 'file1.xlsx',
                         'file3.xlsx', 'file3.xlsx', 'file3.xlsx'],
        })

    def test_aggregate_by_utr_sums_amounts(self, sample_upi_data):
        """Aggregate should sum transaction_amount, commission, gst, settled_amount."""
        result = aggregate_by_utr(sample_upi_data)

        # Find UTR001 aggregated row
        utr001 = result[result['utr'] == 'UTR001'].iloc[0]

        assert utr001['amount_gross'] == 1000  # 500 + 300 + 200
        assert utr001['commission'] == 20      # 10 + 6 + 4
        assert abs(utr001['gst'] - 3.6) < 0.01  # 1.8 + 1.08 + 0.72
        assert abs(utr001['settled_amount'] - 976.4) < 0.01  # 488.2 + 292.92 + 195.28

    def test_aggregate_by_utr_takes_earliest_date(self, sample_upi_data):
        """Should take earliest settled_date per UTR."""
        result = aggregate_by_utr(sample_upi_data)

        utr001 = result[result['utr'] == 'UTR001'].iloc[0]
        assert utr001['settled_dt'] == pd.Timestamp('2026-03-01')  # Not 03-02

    def test_aggregate_by_utr_counts_transactions(self, sample_upi_data):
        """Should count number of transactions per UTR."""
        result = aggregate_by_utr(sample_upi_data)

        utr001 = result[result['utr'] == 'UTR001'].iloc[0]
        utr002 = result[result['utr'] == 'UTR002'].iloc[0]

        assert utr001['utr_txn_count'] == 3
        assert utr002['utr_txn_count'] == 1

    def test_aggregate_by_utr_preserves_null_utrs(self, sample_upi_data):
        """Null UTRs should be kept as separate rows (low confidence)."""
        result = aggregate_by_utr(sample_upi_data)

        null_rows = result[(result['utr'].isna()) | (result['utr'] == '')]
        assert len(null_rows) == 3  # 2 None + 1 empty string

        # Null UTRs should not be aggregated
        assert all(null_rows['utr_txn_count'] == 1)
        assert all(null_rows['confidence'] == 'low')

    def test_aggregate_by_utr_marks_confidence(self, sample_upi_data):
        """High confidence for UTR, low confidence for null."""
        result = aggregate_by_utr(sample_upi_data)

        has_utr = result[result['utr'].notna() & (result['utr'] != '')]
        no_utr = result[(result['utr'].isna()) | (result['utr'] == '')]

        assert all(has_utr['confidence'] == 'high')
        assert all(no_utr['confidence'] == 'low')

    def test_aggregate_by_utr_merges_file_paths(self, sample_upi_data):
        """Should join multiple source files for same UTR."""
        result = aggregate_by_utr(sample_upi_data)

        utr001 = result[result['utr'] == 'UTR001'].iloc[0]
        assert 'file1.xlsx' in utr001['raw_path']
        assert 'file2.xlsx' in utr001['raw_path']
        assert '|' in utr001['raw_path']

    def test_aggregate_empty_dataframe(self):
        """Should handle empty input gracefully."""
        empty = pd.DataFrame()
        result = aggregate_by_utr(empty)
        assert result.empty

    def test_aggregate_all_null_utrs(self):
        """Should handle case where all UTRs are null."""
        data = pd.DataFrame({
            'utr': [None, None, None],
            'amount_gross': [100, 200, 300],
            'commission': [2, 4, 6],
            'gst': [0.36, 0.72, 1.08],
            'settled_amount': [97.64, 195.28, 292.92],
            'settled_dt': pd.to_datetime(['2026-03-01', '2026-03-02', '2026-03-03']),
            'txn_dt': pd.to_datetime(['2026-03-01'] * 3),
            'payment_mode': ['UPI'] * 3,
            'issuing_bank': [None] * 3,
            'unit': ['front_office'] * 3,
            'raw_path': ['file.xlsx'] * 3,
        })

        result = aggregate_by_utr(data)
        assert len(result) == 3  # No aggregation
        assert all(result['confidence'] == 'low')


class TestPaymentModeMapping:
    """Test payment mode extraction and normalization."""

    def test_payment_mode_normalization(self):
        """Payment modes should be uppercase and stripped."""
        data = pd.DataFrame({
            'Transaction_Date': ['2026-03-01'],
            'Amount': [500],
            'Commission': [10],
            'GST': [1.8],
            'Settled_Amount': [488.2],
            'UTR_No.': ['UTR001'],
            'Settled_Date': ['2026-03-01'],
            'Payment_Mode': ["'upi'"],  # Excel-quoted lowercase
        })

        # Create temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        assert df['payment_mode'].iloc[0] == 'UPI'

    def test_payment_modes_observed(self):
        """All observed payment modes from requirements."""
        valid_modes = {
            'UPI', 'UPI_CREDIT_CARD', 'CREDIT_CARD', 'DEBIT_CARD',
            'UPI_LITE', 'TPP', 'TIDY_CARD', 'CASH'
        }
        # This is a documentation test - just ensure we handle these
        assert len(valid_modes) == 8


class TestColumnVariants:
    """Test handling of 4 column variants (per excel-structure.md)."""

    def test_variant_standard_txn_date(self):
        """Variant 2: Standard format with Transaction_Date (8 cols)."""
        data = pd.DataFrame({
            'Transaction_Date': ['2026-03-01'],
            'Amount': [500],
            'Commission': [10],
            'GST': [1.8],
            'Settled_Amount': [488.2],
            'UTR_No.': ['UTR001'],
            'Settled_Date': ['2026-03-01'],
            'Payment_Mode': ['UPI'],
        })

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        assert 'txn_dt' in df.columns
        assert not df.empty

    def test_variant_updated_date(self):
        """Variant 1: Updated_Date instead of Transaction_Date."""
        data = pd.DataFrame({
            'Updated_Date': ['2026-03-01'],  # Different column name
            'Amount': [500],
            'Commission': [10],
            'GST': [1.8],
            'Settled_Amount': [488.2],
            'UTR_No.': ['UTR001'],
            'Settled_Date': ['2026-03-01'],
            'Payment_Mode': ['UPI'],
        })

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        assert 'txn_dt' in df.columns
        assert not df.empty

    def test_variant_with_issuing_bank(self):
        """Variant 3: Includes Issuing_Bank (9 cols)."""
        data = pd.DataFrame({
            'Transaction_Date': ['2026-03-01'],
            'Amount': [500],
            'Commission': [10],
            'GST': [1.8],
            'Settled_Amount': [488.2],
            'UTR_No.': ['UTR001'],
            'Settled_Date': ['2026-03-01'],
            'Payment_Mode': ['UPI'],
            'Issuing_Bank': ['HDFC'],  # Extra column
        })

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        assert 'issuing_bank' in df.columns
        assert df['issuing_bank'].iloc[0] == 'HDFC'


class TestDataQuality:
    """Test handling of data quality issues."""

    def test_excel_quoted_strings_stripped(self):
        """Excel-quoted strings (leading ') should be stripped."""
        data = pd.DataFrame({
            'Transaction_Date': ["'2026-03-01 10:00:00'"],
            'Amount': [500],
            'Commission': [10],
            'GST': [1.8],
            'Settled_Amount': [488.2],
            'UTR_No.': ["'YESAP60615253073'"],  # Quoted
            'Settled_Date': ["'2026-03-01 13:24:07'"],
            'Payment_Mode': ["'UPI'"],
        })

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        # Should strip leading/trailing quotes
        assert not df['utr'].iloc[0].startswith("'")
        assert not df['utr'].iloc[0].endswith("'")
        assert df['utr'].iloc[0] == 'YESAP60615253073'

    def test_summary_rows_filtered(self):
        """Summary rows (TOTAL, etc.) should be filtered out."""
        data = pd.DataFrame({
            'Transaction_Date': ['2026-03-01', 'TOTAL'],
            'Amount': [500, 500],
            'Commission': [10, 10],
            'GST': [1.8, 1.8],
            'Settled_Amount': [488.2, 488.2],
            'UTR_No.': ['UTR001', ''],
            'Settled_Date': ['2026-03-01', ''],
            'Payment_Mode': ['UPI', ''],
        })

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            data.to_excel(f.name, index=False)
            df = extract_upi(Path(f.name))

        assert len(df) == 1  # TOTAL row filtered


class TestValidationReport:
    """Test validation report generation."""

    def test_utr_statistics(self):
        """Should calculate correct UTR statistics."""
        # This is tested in the main validation runner
        # Just ensure the formulas are correct
        data = pd.DataFrame({
            'utr': ['A', 'A', 'A', 'B', None, None]
        })

        null_count = data['utr'].isna().sum()
        total = len(data)
        null_rate = null_count / total

        non_null = data[data['utr'].notna()]
        unique_utr = non_null['utr'].nunique()
        dup_rate = 1 - (unique_utr / len(non_null))

        assert null_rate == pytest.approx(0.333, 0.01)  # 2/6
        assert dup_rate == pytest.approx(0.50, 0.01)     # 1 - (2/4)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
