"""Declarative column-mapping schema.

Two modes:
  * row-per-voucher (bank-statement style): each row → one Receipt/Payment.
    Either a `signed_amount` column or separate `debit/credit` columns.
  * compound (journal/sales/purchase style): rows grouped by `group_by` →
    one voucher per group, each row → one LedgerEntry.

Mappings are dicts (or YAML); see `presets/`.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
import yaml
from pathlib import Path

Mode = Literal["row_per_voucher", "compound"]


@dataclass
class Field:
    """Reference an Excel column or a fixed value."""
    column: str | int | None = None    # header name or 0-based index
    value: Any = None                  # fixed override (overrides column)
    transform: str = "string"          # 'date' | 'amount' | 'string'
    required: bool = False
    default: Any = None

    @classmethod
    def parse(cls, spec: Any) -> "Field":
        if isinstance(spec, Field):
            return spec
        if isinstance(spec, dict):
            return cls(**spec)
        # bare string/int → column reference
        return cls(column=spec)


@dataclass
class EntryMap:
    """Build one LedgerEntry per row (compound mode)."""
    ledger: Field
    amount: Field                      # signed: Dr negative, Cr positive (Tally convention)
    is_deemed_positive: bool | Field = True   # True ⇒ Dr
    is_party_ledger: bool = False


@dataclass
class ColumnMap:
    mode: Mode

    voucher_type: Field                # e.g. fixed "Payment" or column-driven
    date: Field

    voucher_number: Field | None = None
    narration: Field | None = None
    reference: Field | None = None
    party: Field | None = None

    # ── compound mode ──
    group_by: Field | None = None      # column whose value groups rows into one voucher
    entries: list[EntryMap] = field(default_factory=list)

    # ── row_per_voucher mode (bank-statement style) ──
    bank_ledger: str = ""              # fixed bank ledger name
    debit_amount: Field | None = None  # filled when money goes OUT of bank → Payment
    credit_amount: Field | None = None # filled when money comes IN → Receipt
    signed_amount: Field | None = None # alternative: single column, sign indicates direction
    contra_ledger: Field | None = None # other-side ledger column (else falls back to default)
    default_contra_ledger: str = "Suspense"

    # voucher type per direction (row-per-voucher); ignored in compound
    payment_voucher_type: str = "Payment"
    receipt_voucher_type: str = "Receipt"


def _parse_field(d: dict, key: str) -> Field | None:
    if key not in d or d[key] is None:
        return None
    return Field.parse(d[key])


def _parse_entry(d: dict) -> EntryMap:
    idp = d.get("is_deemed_positive", True)
    return EntryMap(
        ledger=Field.parse(d["ledger"]),
        amount=Field.parse(d["amount"]),
        is_deemed_positive=Field.parse(idp) if isinstance(idp, (dict, str, int)) and not isinstance(idp, bool) else bool(idp),
        is_party_ledger=bool(d.get("is_party_ledger", False)),
    )


def from_dict(d: dict) -> ColumnMap:
    return ColumnMap(
        mode=d["mode"],
        voucher_type=Field.parse(d["voucher_type"]),
        date=Field.parse(d["date"]),
        voucher_number=_parse_field(d, "voucher_number"),
        narration=_parse_field(d, "narration"),
        reference=_parse_field(d, "reference"),
        party=_parse_field(d, "party"),
        group_by=_parse_field(d, "group_by"),
        entries=[_parse_entry(e) for e in d.get("entries", [])],
        bank_ledger=d.get("bank_ledger", ""),
        debit_amount=_parse_field(d, "debit_amount"),
        credit_amount=_parse_field(d, "credit_amount"),
        signed_amount=_parse_field(d, "signed_amount"),
        contra_ledger=_parse_field(d, "contra_ledger"),
        default_contra_ledger=d.get("default_contra_ledger", "Suspense"),
        payment_voucher_type=d.get("payment_voucher_type", "Payment"),
        receipt_voucher_type=d.get("receipt_voucher_type", "Receipt"),
    )


def from_yaml(path: str | Path) -> ColumnMap:
    return from_dict(yaml.safe_load(Path(path).read_text()))


def load_preset(name: str) -> ColumnMap:
    """Load bundled preset by name (e.g. 'bank_statement', 'sales_register')."""
    p = Path(__file__).parent / "presets" / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"No preset: {name}")
    return from_yaml(p)
