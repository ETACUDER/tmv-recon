#!/usr/bin/env python
"""One-off QA: compare a generated Rooftop XML against the accountant's Tally export
and write a standalone, printable System-Verification report (self-contained HTML).

NOT part of the web app — verification needs the accountant's Transactions.xml, which
the app never has during the monthly run.

    python scripts/verify_rooftop_vs_tally.py \
      --gen   data/recon/rooftop/runs/2026-03/<run>/combined_rooftop_2026-03.xml \
      --tally TMV_tally/Transactions.xml \
      --month 2026-03 \
      --out   data/recon/rooftop/System_Verification_March2026.html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from tmv_recon.restaurant.pipeline import compare_to_tally  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True, help="generated combined XML")
    ap.add_argument("--tally", required=True, help="accountant's Tally Transactions.xml")
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--out", required=True, help="output .html")
    args = ap.parse_args()

    c = compare_to_tally(args.gen, args.tally)
    env = Environment(loader=FileSystemLoader(str(ROOT / "web_ui" / "templates")),
                      autoescape=True)
    html = env.get_template("rooftop_verify.html").render(
        c=c, month=args.month, run_id="—", auth_enabled=False)
    Path(args.out).write_text(html, encoding="utf-8")

    print(f"✓ {c['coverage_pct']}% of Tally's {c['tally_total']} vouchers reproduced "
          f"({c['ours_total']} generated) → {args.out}")
    s, m, pm, df = c["sales"], c["mode"], c["payments"], c["deferred"]
    print(f"  Sales {s['amount_match']}/{s['common']} match by amount "
          f"({s['match_pct']}%) · turnover diff ₹{s['turnover_diff']:,.0f}")
    print(f"  Mode routing agrees {m['agree_pct']}% ({m['agree']}/{m['common']})")
    print(f"  Payments {pm['ours']}/{pm['tally']} · "
          f"accountant-only: {df['purchase']} Purchase + {df['sw_zo_receipts']} Swiggy/Zomato receipts")


if __name__ == "__main__":
    main()
