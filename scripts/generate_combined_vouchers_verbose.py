#!/usr/bin/env python3
"""Generate ONE combined Tally XML containing Sales + Journal vouchers,
ordered per-invoice chronologically so Tally processes the bill-opener
before any settler within a single import operation.

Per invoice, emission order is:
  - If bill_opens_with == "journal":
      Journal split #1 (earliest)  → opens bill via New Ref
      Sales voucher                 → consumes via Agst Ref
      Journal splits #2..N          → settle remainder via Agst Ref
  - If bill_opens_with == "sales":
      Sales voucher                 → opens bill via New Ref
      Journal splits (in Txn-Date order) → settle via Agst Ref

Result: a single import, all bills resolve, Sundry Debtors closes per invoice.
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
from tmv_recon.vouchers.sales import render_sales_voucher
from tmv_recon.vouchers.journal import render_journal_voucher


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--invoices", required=True, help="canonical invoice CSV")
    ap.add_argument("--payments", required=True, help="canonical payment CSV")
    ap.add_argument("--output", required=True, help="output XML path")
    ap.add_argument("--sales-alter-id-base", type=int, default=70000)
    ap.add_argument("--journal-alter-id-base", type=int, default=80000)
    args = ap.parse_args()

    inv_csv = Path(args.invoices)
    pay_csv = Path(args.payments)
    out = Path(args.output)
    if not inv_csv.exists() or not pay_csv.exists():
        print("ERROR: invoice or payment CSV not found", file=sys.stderr)
        return 1

    # ---- load invoices ----
    invoice_rows: list[dict] = list(csv.DictReader(inv_csv.open("r", encoding="utf-8")))
    invoice_by_no: dict[str, dict] = {r["Invoice #"]: r for r in invoice_rows}
    total_payable_by_inv: dict[str, float] = {
        r["Invoice #"]: ffloat(r.get("Total Payable") or r.get("Gross Amount", "0"))
        for r in invoice_rows
    }
    opens_with_by_inv: dict[str, str] = {
        r["Invoice #"]: (r.get("bill_opens_with") or "sales").strip().lower()
        for r in invoice_rows
    }

    # ---- load + group payments by invoice, sorted by Transaction Date ----
    pay_rows: list[dict] = list(csv.DictReader(pay_csv.open("r", encoding="utf-8")))
    pay_groups: dict[str, list[tuple[int, dict]]] = {}
    for i, row in enumerate(pay_rows):
        pay_groups.setdefault(row["Invoice #"].strip(), []).append((i, row))
    for grp in pay_groups.values():
        grp.sort(key=lambda ir: (ir[1].get("Transaction Date") or "", ir[0]))

    # ---- ordered emission per invoice ----
    vouchers_xml: list[str] = []
    skipped_zero = 0
    skipped_unmapped: list[str] = []
    sales_emitted = 0
    journal_emitted = 0

    # Process invoices in their CSV order (which is already in Invoice-date order
    # for the per-month canonical). Stable enough.
    for sales_idx, inv_row in enumerate(invoice_rows):
        invoice_no = inv_row["Invoice #"].strip()
        gross = ffloat(inv_row.get("Gross Amount", "0"))
        if gross <= 0:
            continue
        bill_opens_with = opens_with_by_inv.get(invoice_no, "sales")
        total_payable = total_payable_by_inv.get(invoice_no, 0.0)
        remaining = total_payable
        splits = pay_groups.get(invoice_no, [])
        n = len(splits)

        # --- decide per-invoice emission order ---
        events: list[tuple[str, int]] = []  # ("sales", -1) or ("journal", split_idx)
        if bill_opens_with == "journal" and splits:
            events.append(("journal", 0))            # opener
            events.append(("sales", -1))             # consumer
            for k in range(1, n):
                events.append(("journal", k))        # subsequent settlers
        else:
            events.append(("sales", -1))
            for k in range(n):
                events.append(("journal", k))

        for kind, k in events:
            if kind == "sales":
                v = render_sales_voucher(inv_row, args.sales_alter_id_base + sales_idx)
                if v:
                    vouchers_xml.append(wrap_tally_message(v))
                    sales_emitted += 1
            else:
                i, prow = splits[k]
                amount = ffloat(prow["Settlement Amount"])
                if amount <= 0:
                    skipped_zero += 1
                    continue
                mode = (prow["Settlement/Particular"] or "").strip()
                if not pick_payment_ledger(mode):
                    skipped_unmapped.append(mode)
                    continue
                is_last = k == n - 1
                if not is_last:
                    cr_to_debtor = min(amount, max(remaining, 0.0))
                    round_off = 0.0
                    remaining -= cr_to_debtor
                else:
                    cr_to_debtor = max(remaining, 0.0)
                    round_off = amount - cr_to_debtor
                    remaining = 0.0
                cr_bill_type = "New Ref" if (k == 0 and bill_opens_with == "journal") else "Agst Ref"
                jv = render_journal_voucher(
                    prow, args.journal_alter_id_base + i,
                    cr_to_debtor, round_off, cr_bill_type,
                )
                if jv:
                    vouchers_xml.append(wrap_tally_message(jv))
                    journal_emitted += 1

    envelope = wrap_envelope(vouchers_xml)
    write_xml(out, envelope)

    print(f"Wrote {len(vouchers_xml)} vouchers into {out}")
    print(f"  Sales: {sales_emitted}  Journal: {journal_emitted}")
    print(f"  size: {out.stat().st_size:,} bytes")
    if skipped_zero:
        print(f"  skipped zero-amount payments: {skipped_zero}")
    if skipped_unmapped:
        for m, c in Counter(skipped_unmapped).most_common():
            print(f"  skipped unmapped mode '{m}': {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
