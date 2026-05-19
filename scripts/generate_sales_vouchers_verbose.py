#!/usr/bin/env python3
"""Generate verbose Tally Sales vouchers for a month.

Reads canonical invoice CSV (from aggregate_invoices_monthly.py), emits
UTF-16 LE+BOM XML. All business logic lives in
`src/tmv_recon/vouchers/`; this script is just I/O orchestration.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tmv_recon.vouchers.primitives import (
    wrap_envelope,
    wrap_tally_message,
    write_xml,
)
from tmv_recon.vouchers.sales import render_sales_voucher


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="canonical invoice CSV")
    ap.add_argument("--output", required=True, help="output XML path")
    ap.add_argument("--alter-id-base", type=int, default=70000)
    args = ap.parse_args()

    src_csv = Path(args.input)
    out_xml = Path(args.output)
    if not src_csv.exists():
        print(f"ERROR: source CSV not found: {src_csv}", file=sys.stderr)
        return 1

    vouchers: list[str] = []
    skipped = 0
    with src_csv.open("r", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            v = render_sales_voucher(row, args.alter_id_base + i)
            if v is None:
                skipped += 1
                continue
            vouchers.append(wrap_tally_message(v))

    envelope = wrap_envelope(vouchers)
    write_xml(out_xml, envelope)

    print(f"Wrote {len(vouchers)} Sales vouchers ({skipped} skipped zero-gross)")
    print(f"  -> {out_xml}")
    print(f"  size: {out_xml.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
