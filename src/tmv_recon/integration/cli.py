"""CLI: excel + mapping → vouchers → XML/CSV/POST.

Usage:
  python -m tmv_recon.integration.cli \
      --excel data/input/bank.xlsx \
      --preset bank_statement \
      --xml data/output/bank.xml \
      --csv data/output/bank.csv

  # custom mapping:
  python -m tmv_recon.integration.cli --excel x.xlsx --mapping my.yaml --xml out.xml

  # push to running Tally:
  python -m tmv_recon.integration.cli --excel x.xlsx --preset journal --post --company "ACME PVT LTD"
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

from tmv_recon.parsers import excel as xls
from tmv_recon.tally.xml import vouchers_envelope
from tmv_recon.tally.csv_export import write as write_csv
from tmv_recon.tally.http import post_xml
from tmv_recon.config import TALLY_COMPANY
from . import mapping, pipeline, validators

console = Console()


def _load_mapping(args: argparse.Namespace) -> mapping.ColumnMap:
    if args.preset:
        return mapping.load_preset(args.preset)
    if args.mapping:
        return mapping.from_yaml(args.mapping)
    sys.exit("error: provide --preset or --mapping")


def _print_issues(issues: list[validators.Issue]) -> None:
    if not issues:
        console.print("[green]✓ no validation issues[/green]")
        return
    t = Table(title="Validation issues")
    t.add_column("#"); t.add_column("severity"); t.add_column("voucher"); t.add_column("message")
    for i, x in enumerate(issues):
        color = "red" if x.severity == "error" else "yellow"
        t.add_row(str(i), f"[{color}]{x.severity}[/]", str(x.voucher_index), x.message)
    console.print(t)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tmv-recon-import")
    ap.add_argument("--excel", required=True, help="path to .xlsx/.xls")
    ap.add_argument("--sheet", default=0, help="sheet name or 0-based index")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--preset", choices=["bank_statement", "sales_register", "purchase_register", "journal"])
    g.add_argument("--mapping", help="path to custom mapping .yaml")
    ap.add_argument("--xml", help="write Tally XML to this path")
    ap.add_argument("--csv", help="write flat CSV to this path")
    ap.add_argument("--post", action="store_true", help="POST to running Tally on :9000")
    ap.add_argument("--company", default=TALLY_COMPANY, help="Tally company name (overrides .env)")
    ap.add_argument("--strict", action="store_true", help="abort on validation warnings, not just errors")
    args = ap.parse_args(argv)

    sheet: int | str = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
    df = xls.sheet(args.excel, sheet)
    console.print(f"[blue]read[/] {len(df)} rows from {args.excel}")

    cmap = _load_mapping(args)
    vouchers = pipeline.build(df, cmap)
    console.print(f"[blue]built[/] {len(vouchers)} vouchers (mode={cmap.mode})")

    issues = validators.validate(vouchers)
    _print_issues(issues)
    if validators.has_errors(issues) or (args.strict and issues):
        console.print("[red]aborting[/]")
        return 2

    if args.xml:
        Path(args.xml).parent.mkdir(parents=True, exist_ok=True)
        Path(args.xml).write_text(vouchers_envelope(vouchers, company=args.company))
        console.print(f"[green]wrote XML →[/] {args.xml}")

    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        write_csv(vouchers, args.csv)
        console.print(f"[green]wrote CSV →[/] {args.csv}")

    if args.post:
        xml = vouchers_envelope(vouchers, company=args.company)
        console.print("[blue]POSTing to Tally…[/]")
        resp = post_xml(xml)
        console.print(resp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
