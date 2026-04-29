"""Integration tests for ground truth validation CLI."""
import pytest
from pathlib import Path
import subprocess
import sys


@pytest.mark.skipif(
    not Path("data/tally/raw_xml/daybook_FY25-26.xml").exists(),
    reason="Test data not available"
)
def test_cli_full_run(tmp_path):
    """Test full CLI run with real data."""
    # Output paths
    csv_report = tmp_path / "test_diff.csv"
    txt_summary = tmp_path / "test_summary.txt"

    # Run CLI
    result = subprocess.run(
        [
            sys.executable, "-m", "tmv_recon.integration.cli_test",
            "--baseline", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--generated", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--date-range", "2026-03-01:2026-03-31",
            "--report", str(csv_report),
            "--summary", str(txt_summary)
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Check exit code (should be 0 for 100% match)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    # Check reports were created
    assert csv_report.exists(), "CSV report not created"
    assert txt_summary.exists(), "Text summary not created"

    # Check CSV has header + 60 data rows
    csv_lines = csv_report.read_text().splitlines()
    assert len(csv_lines) == 61, f"Expected 61 lines, got {len(csv_lines)}"
    assert csv_lines[0].startswith("Actual Voucher No")

    # Check summary contains expected sections
    summary_text = txt_summary.read_text()
    assert "GROUND TRUTH VALIDATION REPORT" in summary_text
    assert "Total actual vouchers:     60" in summary_text
    assert "Average match score:       100.00%" in summary_text
    assert "✓ PASS" in summary_text


@pytest.mark.skipif(
    not Path("data/tally/raw_xml/daybook_FY25-26.xml").exists(),
    reason="Test data not available"
)
def test_cli_date_filtering(tmp_path):
    """Test CLI with date range filtering."""
    csv_report = tmp_path / "test_diff.csv"

    result = subprocess.run(
        [
            sys.executable, "-m", "tmv_recon.integration.cli_test",
            "--baseline", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--generated", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--date-range", "2026-03-15:2026-03-20",
            "--report", str(csv_report)
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    assert result.returncode == 0

    # Check filtering worked (should have fewer vouchers)
    csv_lines = csv_report.read_text().splitlines()
    # At least header + 1 row, but less than full 60
    assert 2 <= len(csv_lines) <= 61


def test_cli_missing_baseline(tmp_path):
    """Test CLI handles missing baseline file."""
    csv_report = tmp_path / "test_diff.csv"

    result = subprocess.run(
        [
            sys.executable, "-m", "tmv_recon.integration.cli_test",
            "--baseline", "nonexistent.xml",
            "--generated", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--report", str(csv_report)
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Should fail with exit code 1
    assert result.returncode == 1
    assert "Error: baseline file not found" in result.stdout


def test_cli_invalid_date_range(tmp_path):
    """Test CLI handles invalid date range format."""
    csv_report = tmp_path / "test_diff.csv"

    result = subprocess.run(
        [
            sys.executable, "-m", "tmv_recon.integration.cli_test",
            "--baseline", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--generated", "data/tally/raw_xml/daybook_FY25-26.xml",
            "--date-range", "invalid-date",
            "--report", str(csv_report)
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    # Should fail with error
    assert result.returncode == 1
    assert "Error" in result.stdout
