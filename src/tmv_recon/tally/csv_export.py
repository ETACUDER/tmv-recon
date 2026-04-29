"""Flat CSV export for human review / Excel inspection."""
from __future__ import annotations
import csv
from pathlib import Path
from .models import Voucher


def write(vouchers: list[Voucher], out: str | Path) -> Path:
    p = Path(out)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "VoucherType", "VoucherNo", "Party",
                    "Ledger", "Dr/Cr", "Amount", "Narration", "Reference"])
        for v in vouchers:
            for e in v.entries:
                w.writerow([
                    v.date.isoformat(), v.voucher_type, v.voucher_number, v.party_ledger,
                    e.ledger, "Dr" if e.is_deemed_positive else "Cr",
                    f"{abs(e.amount):.2f}", v.narration, v.reference,
                ])
    return p
