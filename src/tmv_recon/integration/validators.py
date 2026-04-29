"""Pre-import validation. Catch problems before sending to Tally."""
from __future__ import annotations
from dataclasses import dataclass
from tmv_recon.tally.models import Voucher


@dataclass
class Issue:
    severity: str   # "error" | "warning"
    voucher_index: int
    message: str


def validate(vouchers: list[Voucher], *, known_ledgers: set[str] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    for i, v in enumerate(vouchers):
        if not v.voucher_type:
            issues.append(Issue("error", i, "voucher_type is empty"))
        if not v.date:
            issues.append(Issue("error", i, "date is empty"))
        if not v.entries:
            issues.append(Issue("error", i, "no ledger entries"))
            continue
        total = sum(e.amount for e in v.entries)
        if abs(total) > 0.01:
            issues.append(Issue("error", i, f"Dr/Cr unbalanced (sum={total:.2f})"))
        for e in v.entries:
            if not e.ledger:
                issues.append(Issue("error", i, "entry has empty ledger name"))
            if known_ledgers is not None and e.ledger and e.ledger not in known_ledgers:
                issues.append(Issue("warning", i, f"ledger {e.ledger!r} not in known set"))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(x.severity == "error" for x in issues)
