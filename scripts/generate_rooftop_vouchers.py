#!/usr/bin/env python
"""CLI: TMV Rooftop Restaurant monthly vouchers (Sales + Receipt + Payment).

    python scripts/generate_rooftop_vouchers.py \
      --sales      "TMV_tally/Sales Detail.html" \
      --bank       "TMV_tally/TMV - Statement Of Account - MARCH 2026.xlsx" \
      --settlement "TMV_tally/TMV ROOFTOP - MARCH 2026.xlsx" \
      --month 2026-03 \
      --out data/recon/rooftop/runs/2026-03/combined_rooftop_2026-03.xml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tmv_recon.restaurant import generate  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sales", required=True, help="EZee Sales Detail .html (dated turnover)")
    ap.add_argument("--settlement", required=True, help="EZee Settlement Detail .html (per-order payment channel)")
    ap.add_argument("--bank", default=None, help="Indian Bank statement .xlsx (OPTIONAL → adds Receipts + Payments)")
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--out", required=True, help="output combined XML path")
    ap.add_argument("--alter-id-base", type=int, default=300000)
    args = ap.parse_args()

    s = generate(args.sales, args.settlement, args.out,
                 month=args.month, bank_path=args.bank, alter_base=args.alter_id_base)
    print(f"✓ {s['total_vouchers']} vouchers → {s['out']}")
    print(f"  SALES    {s['sales_count']:>3}  ₹{s['sales_total']:>11,.2f}   (bank_used={s['bank_used']})")
    for ch, d in sorted(s["sales_by_channel"].items(), key=lambda x: -x[1]["amount"]):
        print(f"    {ch:12} {d['orders']:>4}  ₹{d['amount']:>11,.2f}  -> {d['ledger']}")
    if s["bank_used"]:
        print(f"  RECEIPTS {s['receipts']:>3}  ₹{s['receipt_total']:>11,.2f}")
        print(f"  PAYMENTS {s['payments']:>3}  ₹{s['payment_total']:>11,.2f}")
    if s["exception_count"]:
        print(f"  ⚠ {s['exception_count']} exception(s): {s['exceptions_summary']}")


if __name__ == "__main__":
    main()
