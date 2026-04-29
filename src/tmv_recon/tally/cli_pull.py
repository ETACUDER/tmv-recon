"""CLI: pull data from a running Tally and save to data/recon/canonical/.

Usage:
    tmv-recon-pull --company "TMV Recon Test" --from 2025-04-01 --to 2026-03-31 --report day_book
    tmv-recon-pull --report list_companies
    tmv-recon-pull --report ledger_outstandings --ledger "CARD / UPI / PAYTM / G PAY"
"""
from __future__ import annotations
import argparse
import sys

from tmv_recon.tally import connectors as conn
from tmv_recon.config import TALLY_COMPANY


REPORTS = {
    "list_companies":      lambda a: conn.list_companies(),
    "day_book":            lambda a: conn.day_book(a.from_date, a.to_date, a.company),
    "ledger_outstandings": lambda a: conn.ledger_outstandings(a.ledger, a.company, a.from_date, a.to_date),
    "bills_receivable":    lambda a: conn.bills_receivable(a.from_date, a.to_date, a.company),
    "bills_payable":       lambda a: conn.bills_payable(a.from_date, a.to_date, a.company),
    "trial_balance":       lambda a: conn.trial_balance(a.from_date, a.to_date, a.company),
    "balance_sheet":       lambda a: conn.balance_sheet(a.to_date, a.company),
    "profit_loss":         lambda a: conn.profit_loss(a.from_date, a.to_date, a.company),
    "sales_register":      lambda a: conn.sales_register(a.from_date, a.to_date, a.company),
    "purchase_register":   lambda a: conn.purchase_register(a.from_date, a.to_date, a.company),
    "payment_register":    lambda a: conn.payment_register(a.from_date, a.to_date, a.company),
    "journal_register":    lambda a: conn.journal_register(a.from_date, a.to_date, a.company),
    "voucher_register":    lambda a: conn.voucher_register(a.voucher_type, a.from_date, a.to_date, a.company),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tmv-recon-pull",
        description="Pull data from a running Tally instance.")
    ap.add_argument("--report", required=True, choices=list(REPORTS),
                    help="Tally report to pull")
    ap.add_argument("--company", default=TALLY_COMPANY or None,
                    help="Tally company name (defaults to .env TALLY_COMPANY)")
    ap.add_argument("--from", dest="from_date", default=None, help="from date YYYY-MM-DD")
    ap.add_argument("--to",   dest="to_date",   default=None, help="to date YYYY-MM-DD")
    ap.add_argument("--ledger", default=None, help="ledger name (for ledger_outstandings)")
    ap.add_argument("--voucher-type", dest="voucher_type", default=None,
                    help="voucher type (for voucher_register)")
    ap.add_argument("--save", default=None, help="save to data/recon/canonical/tally_<save>.csv")
    args = ap.parse_args(argv)

    fn = REPORTS[args.report]
    try:
        df = fn(args)
    except conn.TallyError as e:
        print(f"Tally error: {e}")
        return 2
    print(f"{len(df)} rows × {len(df.columns)} cols")
    if not df.empty:
        print(df.head(10).to_string(index=False))
    if args.save:
        path = conn.save_canonical(df, args.save)
        print(f"\nsaved → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
