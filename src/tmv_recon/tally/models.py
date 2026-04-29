"""Tally domain models. Tally signs amounts: Dr=negative, Cr=positive
in voucher entries; ISDEEMEDPOSITIVE flag carries the side independently."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class LedgerEntry:
    ledger: str
    amount: float            # signed per Tally convention (Dr -ve, Cr +ve)
    is_deemed_positive: bool = True   # True => Dr, False => Cr
    is_party_ledger: bool = False


@dataclass
class Voucher:
    date: date
    voucher_type: str        # "Receipt" | "Payment" | "Journal" | "Sales" | "Purchase" | "Contra"
    voucher_number: str
    narration: str = ""
    reference: str = ""
    party_ledger: str = ""
    entries: list[LedgerEntry] = field(default_factory=list)


@dataclass
class Ledger:
    """Tally master. PARENT is the group (e.g. 'Sundry Debtors')."""
    name: str
    parent: str
    opening_balance: float = 0.0
    email: str = ""
    pincode: str = ""
    address: list[str] = field(default_factory=list)
