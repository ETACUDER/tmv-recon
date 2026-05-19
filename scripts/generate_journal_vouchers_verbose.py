#!/usr/bin/env python3
"""Generate verbose Tally Journal vouchers for a month.

Reads canonical payment CSV + canonical invoice CSV (for Total Payable +
bill_opens_with). Walks payment splits per invoice chronologically,
allocating Cr Sundry Debtors against remaining bill balance and putting
the residue (paid vs billed) into ROUND OFF on the last split.

All business logic lives in `src/tmv_recon/vouchers/`; this script is
just I/O orchestration.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tmv_recon.vouchers.ledgers import pick_payment_ledger
from tmv_recon.vouchers.primitives import (
    ffloat,
    wrap_envelope,
    wrap_tally_message,
    write_xml,
)
from tmv_recon.vouchers.journal import render_journal_voucher


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="payment canonical CSV")
    ap.add_argument("--invoices", required=True, help="invoice canonical CSV (Total Payable + bill_opens_with)")
    ap.add_argument("--output", required=True, help="output XML path")
    ap.add_argument("--alter-id-base", type=int, default=80000)
    args = ap.parse_args()

    src = Path(args.input)
    inv_csv = Path(args.invoices)
    out = Path(args.output)
    if not src.exists():
        print(f"ERROR: source CSV not found: {src}", file=sys.stderr)
        return 1
    if not inv_csv.exists():
        print(f"ERROR: invoice CSV not found: {inv_csv}", file=sys.stderr)
        return 1

    total_payable_by_inv: dict[str, float] = {}
    opens_with_by_inv: dict[str, str] = {}
    with inv_csv.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inv = r["Invoice #"].strip()
            tp = ffloat(r.get("Total Payable") or r.get("Gross Amount", "0"))
            total_payable_by_inv[inv] = tp
            opens_with_by_inv[inv] = (r.get("bill_opens_with") or "sales").strip().lower()

    all_rows: list[dict] = list(csv.DictReader(src.open("r", encoding="utf-8")))
    groups: dict[str, list[tuple[int, dict]]] = {}
    for i, row in enumerate(all_rows):
        groups.setdefault(row["Invoice #"].strip(), []).append((i, row))
    # Sort splits per invoice by Transaction Date ascending (earliest first).
    for rows in groups.values():
        rows.sort(key=lambda ir: (ir[1].get("Transaction Date") or "", ir[0]))

    vouchers: list[str] = []
    skipped_unmapped: list[str] = []
    skipped_zero = 0

    for invoice_no, rows in groups.items():
        remaining = total_payable_by_inv.get(invoice_no, 0.0)
        bill_opens_with = opens_with_by_inv.get(invoice_no, "sales")
        n = len(rows)
        for split_idx, (i, row) in enumerate(rows):
            amount = ffloat(row["Settlement Amount"])
            if amount <= 0:
                skipped_zero += 1
                continue
            mode = (row["Settlement/Particular"] or "").strip()
            if not pick_payment_ledger(mode):
                skipped_unmapped.append(mode)
                continue

            is_last = split_idx == n - 1
            if not is_last:
                cr_to_debtor = min(amount, max(remaining, 0.0))
                round_off = 0.0
                remaining -= cr_to_debtor
            else:
                cr_to_debtor = max(remaining, 0.0)
                round_off = amount - cr_to_debtor
                remaining = 0.0

            # Earliest split of an invoice opened by Journal carries New Ref;
            # every other Cr Sundry Debtors settles via Agst Ref.
            cr_bill_type = "New Ref" if (split_idx == 0 and bill_opens_with == "journal") else "Agst Ref"

            v = render_journal_voucher(row, args.alter_id_base + i, cr_to_debtor, round_off, cr_bill_type)
            if v is not None:
                vouchers.append(wrap_tally_message(v))

    envelope = wrap_envelope(vouchers)
    write_xml(out, envelope)

    print(f"Wrote {len(vouchers)} Journal vouchers")
    print(f"  -> {out}")
    print(f"  size: {out.stat().st_size:,} bytes")
    if skipped_zero:
        print(f"  skipped zero-amount: {skipped_zero}")
    if skipped_unmapped:
        unm = Counter(skipped_unmapped)
        print(f"  skipped unmapped modes: {len(skipped_unmapped)}")
        for m, c in unm.most_common():
            print(f"    {m}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
