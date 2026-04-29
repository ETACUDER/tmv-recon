"""Excel rows → Voucher objects, applying a ColumnMap."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Any
import pandas as pd

from tmv_recon.tally.models import Voucher, LedgerEntry
from .mapping import ColumnMap, Field, EntryMap
from .transforms import TRANSFORMS, to_date, to_amount, to_str


def _resolve(row: pd.Series, f: Field | None) -> Any:
    if f is None:
        return None
    if f.value is not None:
        return f.value
    if f.column is None:
        return f.default
    raw = row.iloc[f.column] if isinstance(f.column, int) else row.get(f.column)
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return f.default
    fn = TRANSFORMS.get(f.transform, to_str)
    out = fn(raw)
    return f.default if out is None or out == "" else out


def _resolve_str(row: pd.Series, f: Field | None, default: str = "") -> str:
    v = _resolve(row, f)
    return str(v) if v not in (None, "") else default


def _resolve_required(row: pd.Series, f: Field | None, name: str) -> Any:
    v = _resolve(row, f)
    if v in (None, ""):
        raise ValueError(f"Missing required field {name!r} in row {row.name}")
    return v


def _build_compound(df: pd.DataFrame, m: ColumnMap) -> list[Voucher]:
    if m.group_by is None:
        raise ValueError("compound mode requires group_by")
    if not m.entries:
        raise ValueError("compound mode requires entries[]")

    out: list[Voucher] = []
    # Group by group_by column. Stable by first-occurrence.
    keys = df.apply(lambda r: _resolve(r, m.group_by), axis=1)
    for _, idx in keys.groupby(keys, sort=False).groups.items():
        sub = df.loc[idx]
        head = sub.iloc[0]
        d = _resolve_required(head, m.date, "date")
        if not isinstance(d, date):
            d = to_date(d)
        v = Voucher(
            date=d,
            voucher_type=str(_resolve_required(head, m.voucher_type, "voucher_type")),
            voucher_number=str(_resolve(head, m.voucher_number) or ""),
            narration=_resolve_str(head, m.narration),
            reference=_resolve_str(head, m.reference),
            party_ledger=_resolve_str(head, m.party),
        )
        for _, row in sub.iterrows():
            for em in m.entries:
                ledger = str(_resolve_required(row, em.ledger, "entries.ledger"))
                amt = _resolve(row, em.amount)
                amt = to_amount(amt) if not isinstance(amt, (int, float)) else amt
                if amt is None or amt == 0:
                    continue
                if isinstance(em.is_deemed_positive, Field):
                    raw = _resolve(row, em.is_deemed_positive)
                    idp = bool(raw) and str(raw).strip().lower() not in ("0", "false", "no", "cr", "credit")
                else:
                    idp = bool(em.is_deemed_positive)
                # Apply Tally sign convention: Dr ⇒ negative, Cr ⇒ positive.
                signed = -abs(float(amt)) if idp else abs(float(amt))
                v.entries.append(LedgerEntry(
                    ledger=ledger, amount=signed,
                    is_deemed_positive=idp, is_party_ledger=em.is_party_ledger,
                ))
        out.append(v)
    return out


def _build_row_per_voucher(df: pd.DataFrame, m: ColumnMap) -> list[Voucher]:
    if not m.bank_ledger:
        raise ValueError("row_per_voucher mode requires bank_ledger")
    if m.signed_amount is None and m.debit_amount is None and m.credit_amount is None:
        raise ValueError("row_per_voucher needs signed_amount, debit_amount, or credit_amount")

    out: list[Voucher] = []
    auto_n = 0
    for _, row in df.iterrows():
        # Determine direction + amount.
        if m.signed_amount is not None:
            amt = to_amount(_resolve(row, m.signed_amount))
            if amt is None or amt == 0:
                continue
            outflow = amt < 0    # negative = money out of bank
            magnitude = abs(amt)
        else:
            dr = to_amount(_resolve(row, m.debit_amount)) if m.debit_amount else None
            cr = to_amount(_resolve(row, m.credit_amount)) if m.credit_amount else None
            if dr and dr != 0:
                outflow, magnitude = True, dr
            elif cr and cr != 0:
                outflow, magnitude = False, cr
            else:
                continue

        d = _resolve_required(row, m.date, "date")
        if not isinstance(d, date):
            d = to_date(d)

        contra = _resolve_str(row, m.contra_ledger) or m.default_contra_ledger
        auto_n += 1
        vnum = str(_resolve(row, m.voucher_number) or auto_n)

        if outflow:
            # Payment: contra Dr, bank Cr
            vtype = m.payment_voucher_type
            entries = [
                LedgerEntry(contra, -magnitude, is_deemed_positive=True),
                LedgerEntry(m.bank_ledger, magnitude, is_deemed_positive=False),
            ]
            party = contra
        else:
            # Receipt: bank Dr, contra Cr
            vtype = m.receipt_voucher_type
            entries = [
                LedgerEntry(m.bank_ledger, -magnitude, is_deemed_positive=True),
                LedgerEntry(contra, magnitude, is_deemed_positive=False),
            ]
            party = contra

        # Allow voucher_type column to override the inferred direction
        explicit_vtype = _resolve_str(row, m.voucher_type) if m.voucher_type else ""
        if explicit_vtype:
            vtype = explicit_vtype

        out.append(Voucher(
            date=d, voucher_type=vtype, voucher_number=vnum,
            narration=_resolve_str(row, m.narration),
            reference=_resolve_str(row, m.reference),
            party_ledger=party,
            entries=entries,
        ))
    return out


def build(df: pd.DataFrame, m: ColumnMap) -> list[Voucher]:
    if m.mode == "compound":
        return _build_compound(df, m)
    if m.mode == "row_per_voucher":
        return _build_row_per_voucher(df, m)
    raise ValueError(f"Unknown mode: {m.mode!r}")
