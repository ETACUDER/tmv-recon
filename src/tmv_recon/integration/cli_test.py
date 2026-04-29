"""CLI for ground truth validation testing.

Compares generated vouchers against actual Tally daybook XML.

Usage:
  tmv-recon-test \
    --baseline data/tally/raw_xml/daybook_FY25-26.xml \
    --generated data/recon/output/ \
    --date-range 2026-03-01:2026-03-31 \
    --report data/recon/reports/ground_truth_diff.csv

  # Single generated file
  tmv-recon-test \
    --baseline daybook.xml \
    --generated vouchers_march.xml \
    --report diff.csv
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from datetime import date
from rich.console import Console
from rich.table import Table

from tmv_recon.etl.ground_truth import (
    parse_tally_vouchers,
    parse_generated_vouchers,
    filter_vouchers_by_date,
    find_best_match,
    compare_vouchers,
    generate_diff_report,
    generate_summary_report,
    ComparisonResult
)

console = Console()


def parse_date_range(date_range_str: str) -> tuple[date, date]:
    """Parse date range string: YYYY-MM-DD:YYYY-MM-DD"""
    parts = date_range_str.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid date range format: {date_range_str}. Expected YYYY-MM-DD:YYYY-MM-DD")

    start = date.fromisoformat(parts[0])
    end = date.fromisoformat(parts[1])
    return start, end


def collect_generated_files(path: Path) -> list[Path]:
    """Collect all XML files from directory or return single file."""
    if path.is_file():
        return [path]
    elif path.is_dir():
        return sorted(path.glob('*.xml'))
    else:
        raise FileNotFoundError(f"Path not found: {path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tmv-recon-test",
        description="Validate generated vouchers against Tally ground truth"
    )
    ap.add_argument(
        "--baseline",
        required=True,
        help="Path to Tally daybook XML (ground truth)"
    )
    ap.add_argument(
        "--generated",
        required=True,
        help="Path to generated voucher XML file or directory"
    )
    ap.add_argument(
        "--date-range",
        help="Filter date range YYYY-MM-DD:YYYY-MM-DD (e.g., 2026-03-01:2026-03-31)"
    )
    ap.add_argument(
        "--report",
        required=True,
        help="Output path for CSV diff report"
    )
    ap.add_argument(
        "--summary",
        help="Output path for text summary (defaults to report path with .txt)"
    )

    args = ap.parse_args(argv)

    # Parse baseline
    console.print(f"[blue]Parsing baseline[/] {args.baseline}")
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        console.print(f"[red]Error: baseline file not found: {baseline_path}[/]")
        return 1

    try:
        actual_vouchers = parse_tally_vouchers(str(baseline_path))
        console.print(f"[green]Loaded {len(actual_vouchers)} actual vouchers[/]")
    except Exception as e:
        console.print(f"[red]Error parsing baseline: {e}[/]")
        return 1

    # Parse generated
    console.print(f"[blue]Parsing generated[/] {args.generated}")
    generated_path = Path(args.generated)

    try:
        generated_files = collect_generated_files(generated_path)
        if not generated_files:
            console.print(f"[red]Error: no XML files found in {generated_path}[/]")
            return 1

        console.print(f"[blue]Found {len(generated_files)} generated file(s)[/]")

        generated_vouchers = []
        for xml_file in generated_files:
            vouchers = parse_generated_vouchers(str(xml_file))
            generated_vouchers.extend(vouchers)
            console.print(f"  - {xml_file.name}: {len(vouchers)} vouchers")

        console.print(f"[green]Loaded {len(generated_vouchers)} generated vouchers[/]")

    except Exception as e:
        console.print(f"[red]Error parsing generated vouchers: {e}[/]")
        return 1

    # Filter by date range if specified
    if args.date_range:
        try:
            start_date, end_date = parse_date_range(args.date_range)
            console.print(f"[blue]Filtering date range:[/] {start_date} to {end_date}")

            actual_before = len(actual_vouchers)
            actual_vouchers = filter_vouchers_by_date(actual_vouchers, start_date, end_date)
            console.print(f"  Actual: {actual_before} → {len(actual_vouchers)}")

            gen_before = len(generated_vouchers)
            generated_vouchers = filter_vouchers_by_date(generated_vouchers, start_date, end_date)
            console.print(f"  Generated: {gen_before} → {len(generated_vouchers)}")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/]")
            return 1

    # Match and compare
    console.print(f"\n[blue]Matching vouchers...[/]")

    comparisons: list[ComparisonResult] = []
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

            # Progress indicator
            if (i + 1) % 10 == 0 or (i + 1) == len(actual_vouchers):
                console.print(f"  Processed {i + 1}/{len(actual_vouchers)}")

    console.print(f"[green]Matched {len(comparisons)} voucher pairs[/]")

    # Display summary statistics
    console.print("\n[bold]Match Quality Summary[/bold]")

    if comparisons:
        avg_score = sum(c.match_score for c in comparisons) / len(comparisons)
        acceptable = sum(1 for c in comparisons if c.is_acceptable)

        voucher_type_match = sum(1 for c in comparisons if c.voucher_type_match)
        ledger_match = sum(1 for c in comparisons if c.ledger_names_match)
        amount_match = sum(1 for c in comparisons if c.amount_match)
        narration_match = sum(1 for c in comparisons if c.narration_pattern_match)

        table = Table(show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta", justify="right")
        table.add_column("Rate", style="green", justify="right")
        table.add_column("Target", style="yellow", justify="right")

        table.add_row("Average Score", "-", f"{avg_score:.1%}", "95%")
        table.add_row("Acceptable (≥95%)", str(acceptable), f"{acceptable/len(comparisons):.1%}", "-")
        table.add_row(
            "Voucher Type",
            str(voucher_type_match),
            f"{voucher_type_match/len(comparisons):.1%}",
            "95%"
        )
        table.add_row(
            "Ledger Names",
            str(ledger_match),
            f"{ledger_match/len(comparisons):.1%}",
            "100%"
        )
        table.add_row(
            "Amounts (±₹1)",
            str(amount_match),
            f"{amount_match/len(comparisons):.1%}",
            "98%"
        )
        table.add_row(
            "Narration",
            str(narration_match),
            f"{narration_match/len(comparisons):.1%}",
            "95%"
        )

        console.print(table)

    # Generate reports
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[blue]Writing CSV report[/] {report_path}")
    generate_diff_report(comparisons, actual_vouchers, generated_vouchers, str(report_path))

    summary_path = Path(args.summary) if args.summary else report_path.with_suffix('.txt')
    console.print(f"[blue]Writing summary[/] {summary_path}")
    generate_summary_report(comparisons, actual_vouchers, generated_vouchers, str(summary_path))

    console.print(f"\n[green]✓ Validation complete[/]")
    console.print(f"  CSV report: {report_path}")
    console.print(f"  Summary: {summary_path}")

    # Exit code based on acceptance criteria
    if comparisons:
        avg_score = sum(c.match_score for c in comparisons) / len(comparisons)
        if avg_score >= 0.95:
            console.print(f"\n[green bold]✓ PASS: Average score {avg_score:.1%} meets target (≥95%)[/]")
            return 0
        else:
            console.print(f"\n[red bold]✗ FAIL: Average score {avg_score:.1%} below target (≥95%)[/]")
            return 1
    else:
        console.print(f"\n[red bold]✗ FAIL: No vouchers matched[/]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
