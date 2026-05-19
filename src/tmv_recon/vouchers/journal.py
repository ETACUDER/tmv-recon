"""Render one verbose Tally Journal voucher (payment-against-invoice).

Caller is responsible for the per-invoice walk: chronological sort,
remaining-payable tracking, and deciding cr_to_debtor + round_off + the
Cr-side bill type per split. This module just renders.
"""
from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape as xml_escape

from .config import CMP_GSTIN, CMP_STATE, ROUND_OFF_TOLERANCE
from .flags import (
    LEDGER_FLAGS_PARTY_CR,
    LEDGER_FLAGS_PARTY_DR,
    VOUCHER_EMPTY_LISTS_JOURNAL,
    VOUCHER_FLAGS_JOURNAL,
    VOUCHER_TRAILING_LISTS,
    round_off_flags,
)
from .ledgers import (
    NEW_REF_LEDGERS,
    ROUND_OFF,
    SUNDRY_DEBTORS,
    pick_payment_ledger,
)
from .primitives import (
    fdate,
    ffloat,
    ledger_entry_block,
    make_guid,
)
from .config import GUID_NAMESPACE


def render_journal_voucher(
    row: dict[str, Any],
    alter_id: int,
    cr_to_debtor: float,
    round_off: float,
    cr_bill_type: str = "Agst Ref",
) -> str | None:
    """Render one Journal voucher for a payment split.

    Args:
        row: payment canonical CSV row.
        alter_id: unique sequence id for VCHKEY/ALTERID/MASTERID + GUID seed.
        cr_to_debtor: amount Cr Sundry Debtors at (settles or opens this much of the bill).
        round_off: residual = Settlement - cr_to_debtor.
                   > 0 → gain (Cr ROUND OFF), < 0 → loss (Dr ROUND OFF).
        cr_bill_type: "New Ref" if this Journal is the earliest event on the invoice
                      (advance receipt opens bill); else "Agst Ref" (settles).
    """
    invoice_no = row["Invoice #"].strip()
    invoice_date = fdate(row["Invoice date"])
    raw_txn = (row.get("Transaction Date") or "").strip()
    voucher_date = fdate(raw_txn) if raw_txn else invoice_date
    if not voucher_date:
        voucher_date = invoice_date
    mode = row["Settlement/Particular"].strip()
    amount = ffloat(row["Settlement Amount"])
    guest = (row.get("Guest Name") or "").strip()

    if amount <= 0:
        return None

    payment_ledger = pick_payment_ledger(mode)
    if not payment_ledger:
        return None  # unmapped mode

    # Distinct GUIDs even for identical (invoice, mode, amount) splits.
    guid = make_guid(f"journal:{invoice_no}:{mode}:{amount}:{alter_id}")
    remote_id = f"{guid}-{alter_id:08x}"
    vch_key = f"{GUID_NAMESPACE}-0000c000:{alter_id:08x}"
    narration = f"BEING PAID THROUGH {mode.upper()} AGAINST INVOICE NO:{invoice_no}"
    if guest:
        narration += f" {guest.upper()}"

    head = [
        f'          <VOUCHER REMOTEID="{remote_id}" VCHKEY="{vch_key}" '
        f'VCHTYPE="Journal" ACTION="Create" OBJVIEW="Accounting Voucher View">',
        '            <OLDAUDITENTRYIDS.LIST TYPE="Number">',
        "              <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>",
        "            </OLDAUDITENTRYIDS.LIST>",
        f"            <DATE>{voucher_date}</DATE>",
        f"            <REFERENCEDATE>{voucher_date}</REFERENCEDATE>",
        f"            <VCHSTATUSDATE>{voucher_date}</VCHSTATUSDATE>",
        f"            <GUID>{guid}</GUID>",
        f"            <NARRATION>{xml_escape(narration)}</NARRATION>",
        "            <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>",
        f'            <GSTREGISTRATION TAXTYPE="GST" TAXREGISTRATION="{CMP_GSTIN}">{CMP_STATE} Registration</GSTREGISTRATION>',
        f"            <CMPGSTIN>{CMP_GSTIN}</CMPGSTIN>",
        f"            <PARTYLEDGERNAME>{xml_escape(payment_ledger)}</PARTYLEDGERNAME>",
        f"            <VOUCHERNUMBER>{xml_escape(invoice_no)}</VOUCHERNUMBER>",
        "            <CMPGSTREGISTRATIONTYPE>Regular</CMPGSTREGISTRATIONTYPE>",
        f"            <REFERENCE>{xml_escape(invoice_no)}</REFERENCE>",
        f"            <CMPGSTSTATE>{CMP_STATE}</CMPGSTSTATE>",
        "            <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>",
        "            <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>",
        "            <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>",
        "            <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>",
        "            <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>",
        "            <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>",
        "            <VCHSTATUSVOUCHERTYPE>Journal</VCHSTATUSVOUCHERTYPE>",
        f"            <VCHSTATUSTAXUNIT>{CMP_STATE} Registration</VCHSTATUSTAXUNIT>",
        "            <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>",
        "            <VCHENTRYMODE>As Voucher</VCHENTRYMODE>",
    ]
    flags_lines = [f"            <{k}>{v}</{k}>" for k, v in VOUCHER_FLAGS_JOURNAL]
    ids = [
        f"            <EFFECTIVEDATE>{voucher_date}</EFFECTIVEDATE>",
        f"            <ALTERID> {alter_id}</ALTERID>",
        f"            <MASTERID> {alter_id}</MASTERID>",
        f"            <VOUCHERKEY>{19687271091500000 + alter_id}</VOUCHERKEY>",
        f"            <VOUCHERRETAINKEY>{alter_id}</VOUCHERRETAINKEY>",
        "            <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>",
    ]
    empty = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_EMPTY_LISTS_JOURNAL]
    trailing = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_TRAILING_LISTS]

    le = lambda **kw: ledger_entry_block(container_tag="ALLLEDGERENTRIES.LIST", **kw)

    dr_bill_type = "New Ref" if payment_ledger in NEW_REF_LEDGERS else None
    entries = [
        le(name=payment_ledger, amount=-amount, flags=LEDGER_FLAGS_PARTY_DR,
           bill_ref=invoice_no if dr_bill_type else None, bill_type=dr_bill_type or "New Ref"),
    ]
    if cr_to_debtor > ROUND_OFF_TOLERANCE:
        entries.append(le(name=SUNDRY_DEBTORS, amount=cr_to_debtor,
                          flags=LEDGER_FLAGS_PARTY_CR, bill_ref=invoice_no, bill_type=cr_bill_type))
    if abs(round_off) >= ROUND_OFF_TOLERANCE:
        # round_off > 0 (paid > billed) → Cr ROUND OFF (gain), AMOUNT positive
        # round_off < 0 (paid < billed) → Dr ROUND OFF (loss), AMOUNT negative
        # ROUND OFF needs APPROPRIATEFOR pre-field so Tally accepts the entry.
        entries.append(le(name=ROUND_OFF, amount=round_off,
                          flags=round_off_flags(dr=round_off < 0),
                          pre_fields=[("APPROPRIATEFOR", "&#4; Not Applicable")]))

    return "\n".join(head + flags_lines + ids + empty + entries + trailing + ["          </VOUCHER>"])
