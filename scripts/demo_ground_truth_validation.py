#!/usr/bin/env python3
"""Demo script to validate ground truth comparison tool.

This script demonstrates the ground truth validation by:
1. Parsing actual Tally daybook XML
2. Using it as both baseline and generated (should be 100% match)
3. Generating comparison reports
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.etl.ground_truth import (
    parse_tally_vouchers,
    filter_vouchers_by_date,
    find_best_match,
    compare_vouchers,
    generate_diff_report,
    generate_summary_report,
)
from datetime import date


def main():
    # Paths
    baseline_path = "data/tally/raw_xml/daybook_FY25-26.xml"
    report_dir = Path("data/recon/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("GROUND TRUTH VALIDATION DEMO")
    print("=" * 80)
    print()

    # Parse baseline
    print(f"[1/5] Parsing baseline: {baseline_path}")
    actual_vouchers = parse_tally_vouchers(baseline_path)
    print(f"      Loaded {len(actual_vouchers)} actual vouchers")

    # For demo, use baseline as generated (should be 100% match)
    print(f"[2/5] Parsing generated (using same file for demo)")
    generated_vouchers = parse_tally_vouchers(baseline_path)
    print(f"      Loaded {len(generated_vouchers)} generated vouchers")

    # Filter to March 2026
    print(f"[3/5] Filtering to March 2026")
    start_date = date(2026, 3, 1)
    end_date = date(2026, 3, 31)

    actual_vouchers = filter_vouchers_by_date(actual_vouchers, start_date, end_date)
    generated_vouchers = filter_vouchers_by_date(generated_vouchers, start_date, end_date)

    print(f"      Actual: {len(actual_vouchers)} vouchers")
    print(f"      Generated: {len(generated_vouchers)} vouchers")

    # Match and compare
    print(f"[4/5] Matching and comparing vouchers...")
    comparisons = []
    used_generated_indices = set()

    for i, actual in enumerate(actual_vouchers):
        best_match, score, match_index = find_best_match(
            actual,
            generated_vouchers,
            used_generated_indices
        )

        if best_match:
            used_generated_indices.add(match_index)
            comparison = compare_vouchers(actual, best_match)
            comparisons.append(comparison)

        if (i + 1) % 10 == 0 or (i + 1) == len(actual_vouchers):
            print(f"      Processed {i + 1}/{len(actual_vouchers)}")

    # Calculate statistics
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    if comparisons:
        avg_score = sum(c.match_score for c in comparisons) / len(comparisons)
        acceptable = sum(1 for c in comparisons if c.is_acceptable)

        voucher_type_match = sum(1 for c in comparisons if c.voucher_type_match)
        ledger_match = sum(1 for c in comparisons if c.ledger_names_match)
        amount_match = sum(1 for c in comparisons if c.amount_match)
        narration_match = sum(1 for c in comparisons if c.narration_pattern_match)

        print(f"Total matched: {len(comparisons)}")
        print(f"Average score: {avg_score:.2%}")
        print(f"Acceptable (≥95%): {acceptable} ({acceptable/len(comparisons):.1%})")
        print()
        print("Component match rates:")
        print(f"  Voucher type:    {voucher_type_match}/{len(comparisons)} ({voucher_type_match/len(comparisons):.1%}) [Target: 95%]")
        print(f"  Ledger names:    {ledger_match}/{len(comparisons)} ({ledger_match/len(comparisons):.1%}) [Target: 100%]")
        print(f"  Amounts (±₹1):   {amount_match}/{len(comparisons)} ({amount_match/len(comparisons):.1%}) [Target: 98%]")
        print(f"  Narration:       {narration_match}/{len(comparisons)} ({narration_match/len(comparisons):.1%}) [Target: 95%]")

    # Generate reports
    print()
    print(f"[5/5] Generating reports...")

    csv_path = report_dir / "ground_truth_diff_demo.csv"
    txt_path = report_dir / "ground_truth_summary_demo.txt"

    generate_diff_report(comparisons, actual_vouchers, generated_vouchers, str(csv_path))
    print(f"      CSV report: {csv_path}")

    generate_summary_report(comparisons, actual_vouchers, generated_vouchers, str(txt_path))
    print(f"      Text summary: {txt_path}")

    print()
    print("=" * 80)
    if comparisons and avg_score >= 0.95:
        print("✓ VALIDATION PASSED")
    else:
        print("✗ VALIDATION FAILED")
    print("=" * 80)


if __name__ == "__main__":
    main()
