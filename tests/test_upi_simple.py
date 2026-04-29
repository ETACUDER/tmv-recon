"""Simple tests for UPI parser without pytest dependency."""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.etl.extract.payment import aggregate_by_utr, _detect_unit_from_path


def test_unit_detection():
    """Test unit dimension extraction."""
    print("Testing unit detection...")
    assert _detect_unit_from_path(Path("/data/PTM ROOFTOP/file.xlsx")) == "rooftop"
    assert _detect_unit_from_path(Path("/data/F&B UPI/file.xlsx")) == "f&b"
    assert _detect_unit_from_path(Path("/data/PTM - MARCH.xlsx")) == "front_office"
    print("  ✓ Unit detection works")


def test_utr_aggregation():
    """Test UTR aggregation with duplicate UTRs."""
    print("\nTesting UTR aggregation...")

    # Sample data with duplicate UTRs (Paytm batch settlement)
    data = pd.DataFrame({
        'utr': ['UTR001', 'UTR001', 'UTR001', 'UTR002', None, None, ''],
        'amount_gross': [500, 300, 200, 1000, 150, 250, 100],
        'commission': [10, 6, 4, 20, 3, 5, 2],
        'gst': [1.8, 1.08, 0.72, 3.6, 0.54, 0.9, 0.36],
        'settled_amount': [488.2, 292.92, 195.28, 976.4, 146.46, 244.1, 97.64],
        'settled_dt': pd.to_datetime([
            '2026-03-01', '2026-03-01', '2026-03-02',
            '2026-03-03',
            '2026-03-04', '2026-03-05', '2026-03-06'
        ]),
        'txn_dt': pd.to_datetime(['2026-03-01'] * 7),
        'payment_mode': ['UPI', 'UPI', 'UPI', 'CREDIT_CARD', 'UPI', 'CASH', 'UPI'],
        'issuing_bank': ['HDFC', 'HDFC', 'HDFC', 'ICICI', None, None, None],
        'unit': ['front_office'] * 7,
        'raw_path': ['file1.xlsx', 'file1.xlsx', 'file2.xlsx', 'file1.xlsx',
                     'file3.xlsx', 'file3.xlsx', 'file3.xlsx'],
    })

    result = aggregate_by_utr(data)

    # Test: Aggregated row count
    # 7 input rows → 2 aggregated UTRs + 3 null UTRs = 5 rows
    assert len(result) == 5, f"Expected 5 rows, got {len(result)}"
    print("  ✓ Correct row count after aggregation")

    # Test: UTR001 aggregation
    utr001 = result[result['utr'] == 'UTR001'].iloc[0]
    assert utr001['amount_gross'] == 1000, f"Expected 1000, got {utr001['amount_gross']}"
    assert utr001['commission'] == 20, f"Expected 20, got {utr001['commission']}"
    assert abs(utr001['gst'] - 3.6) < 0.01, f"Expected 3.6, got {utr001['gst']}"
    assert utr001['utr_txn_count'] == 3, f"Expected 3 txns, got {utr001['utr_txn_count']}"
    print("  ✓ UTR001: Amounts summed correctly")

    # Test: Earliest date selection
    assert utr001['settled_dt'] == pd.Timestamp('2026-03-01'), \
        f"Expected 2026-03-01, got {utr001['settled_dt']}"
    print("  ✓ UTR001: Earliest date selected")

    # Test: Null UTRs preserved
    null_rows = result[(result['utr'].isna()) | (result['utr'] == '')]
    assert len(null_rows) == 3, f"Expected 3 null rows, got {len(null_rows)}"
    assert all(null_rows['utr_txn_count'] == 1), "Null UTRs should not be aggregated"
    assert all(null_rows['confidence'] == 'low'), "Null UTRs should be low confidence"
    print("  ✓ Null UTRs preserved separately")

    # Test: Confidence marking
    has_utr = result[result['utr'].notna() & (result['utr'] != '')]
    assert all(has_utr['confidence'] == 'high'), "UTR rows should be high confidence"
    print("  ✓ Confidence marked correctly")


def test_utr_statistics():
    """Test UTR duplicate rate calculation."""
    print("\nTesting UTR statistics...")

    data = pd.DataFrame({
        'utr': ['A', 'A', 'A', 'B', None, None]
    })

    null_count = data['utr'].isna().sum()
    total = len(data)
    null_rate = null_count / total

    non_null = data[data['utr'].notna()]
    unique_utr = non_null['utr'].nunique()
    dup_rate = 1 - (unique_utr / len(non_null))

    assert abs(null_rate - 0.333) < 0.01, f"Expected 33.3% null rate, got {null_rate:.1%}"
    assert abs(dup_rate - 0.50) < 0.01, f"Expected 50% dup rate, got {dup_rate:.1%}"
    print("  ✓ Statistics calculated correctly")


def test_empty_dataframe():
    """Test handling of empty input."""
    print("\nTesting empty dataframe...")
    empty = pd.DataFrame()
    result = aggregate_by_utr(empty)
    assert result.empty, "Empty input should return empty output"
    print("  ✓ Empty dataframe handled")


def test_all_null_utrs():
    """Test case where all UTRs are null."""
    print("\nTesting all null UTRs...")

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
    assert len(result) == 3, "No aggregation should occur for null UTRs"
    assert all(result['confidence'] == 'low'), "All should be low confidence"
    print("  ✓ All null UTRs handled correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("UPI Parser Test Suite")
    print("=" * 60)

    try:
        test_unit_detection()
        test_utr_aggregation()
        test_utr_statistics()
        test_empty_dataframe()
        test_all_null_utrs()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
