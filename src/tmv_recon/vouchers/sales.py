"""Render one verbose Tally Sales voucher.

Input: a canonical-invoice record (dict with keys matching invoice_<m><y>.csv).
Output: a single TALLYMESSAGE XML string (no envelope wrapper).
"""
from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape as xml_escape

from .config import CMP_GSTIN, CMP_STATE, ROUND_OFF_TOLERANCE
from .flags import (
    LEDGER_FLAGS_INCOME_CR,
    LEDGER_FLAGS_PARTY_DR,
    VOUCHER_EMPTY_LISTS_SALES,
    VOUCHER_FLAGS_SALES,
    VOUCHER_TRAILING_LISTS,
    round_off_flags,
)
from .ledgers import (
    CGST,
    ROUND_OFF,
    SGST,
    SUNDRY_DEBTORS,
    pick_sales_ledger,
)
from .primitives import (
    fdate,
    ffloat,
    ledger_entry_block,
    make_guid,
)
from .config import GUID_NAMESPACE


def render_sales_voucher(row: dict[str, Any], alter_id: int) -> str | None:
    """Render one Sales voucher from a canonical invoice row.

    Returns None if the invoice has zero/negative gross (skipped).
    """
    invoice_no = row["Invoice #"].strip()
    invoice_date = fdate(row["Invoice date"])
    guest = (row.get("Guest Name") or "").strip() or "Unknown Guest"
    net = ffloat(row.get("Net Amount", "0"))
    cgst = ffloat(row.get("Tax Amount", "0"))
    sgst = ffloat(row.get("Tax Amount.1", "0"))
    gross = ffloat(row.get("Gross Amount", "0"))
    discount = ffloat(row.get("Discount Amount", "0"))
    adjustment = ffloat(row.get("Adjustment", "0"))
    total_payable = ffloat(row.get("Total Payable", "0")) or (gross - discount - adjustment)
    round_off = gross - total_payable  # +ve means EZee charged less than Gross (haircut/loss)

    if gross <= 0:
        return None

    # bill_opens_with controls the Sundry Debtors bill type:
    #   "sales"   → Sales is the earliest event → New Ref (opens bill)
    #   "journal" → an advance payment opened first → Agst Ref (consumes advance)
    bill_opens_with = (row.get("bill_opens_with") or "sales").strip().lower()
    sd_bill_type = "New Ref" if bill_opens_with == "sales" else "Agst Ref"

    income_ledger = pick_sales_ledger(net, cgst, sgst)
    guid = make_guid(invoice_no)
    remote_id = f"{guid}-{alter_id:08x}"
    vch_key = f"{GUID_NAMESPACE}-0000b30e:{alter_id:08x}"
    narration = f"INVOICE NO:-{invoice_no}, {guest}"
    party_addr = guest.upper()

    head = [
        f'          <VOUCHER REMOTEID="{remote_id}" VCHKEY="{vch_key}" '
        f'VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">',
        '            <BASICBUYERADDRESS.LIST TYPE="String">',
        f"              <BASICBUYERADDRESS>{xml_escape(party_addr)}</BASICBUYERADDRESS>",
        "            </BASICBUYERADDRESS.LIST>",
        '            <OLDAUDITENTRYIDS.LIST TYPE="Number">',
        "              <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>",
        "            </OLDAUDITENTRYIDS.LIST>",
        f"            <DATE>{invoice_date}</DATE>",
        f"            <REFERENCEDATE>{invoice_date}</REFERENCEDATE>",
        f"            <VCHSTATUSDATE>{invoice_date}</VCHSTATUSDATE>",
        f"            <GUID>{guid}</GUID>",
        "            <GSTREGISTRATIONTYPE>Unregistered/Consumer</GSTREGISTRATIONTYPE>",
        "            <VATDEALERTYPE>Regular</VATDEALERTYPE>",
        f"            <STATENAME>{CMP_STATE}</STATENAME>",
        f"            <NARRATION>{xml_escape(narration)}</NARRATION>",
        "            <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>",
        f"            <PLACEOFSUPPLY>{CMP_STATE}</PLACEOFSUPPLY>",
        "            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>",
        f"            <PARTYNAME>{xml_escape(SUNDRY_DEBTORS)}</PARTYNAME>",
        f'            <GSTREGISTRATION TAXTYPE="GST" TAXREGISTRATION="{CMP_GSTIN}">{CMP_STATE} Registration</GSTREGISTRATION>',
        f"            <CMPGSTIN>{CMP_GSTIN}</CMPGSTIN>",
        f"            <PARTYLEDGERNAME>{xml_escape(SUNDRY_DEBTORS)}</PARTYLEDGERNAME>",
        f"            <VOUCHERNUMBER>{xml_escape(invoice_no)}</VOUCHERNUMBER>",
        f"            <BASICBUYERNAME>{xml_escape(guest)}</BASICBUYERNAME>",
        "            <CMPGSTREGISTRATIONTYPE>Regular</CMPGSTREGISTRATIONTYPE>",
        f"            <REFERENCE>{xml_escape(invoice_no)}</REFERENCE>",
        f"            <PARTYMAILINGNAME>{xml_escape(SUNDRY_DEBTORS)}</PARTYMAILINGNAME>",
        f"            <CONSIGNEEMAILINGNAME>{xml_escape(guest)}</CONSIGNEEMAILINGNAME>",
        f"            <CONSIGNEESTATENAME>{CMP_STATE}</CONSIGNEESTATENAME>",
        f"            <CMPGSTSTATE>{CMP_STATE}</CMPGSTSTATE>",
        "            <CONSIGNEECOUNTRYNAME>India</CONSIGNEECOUNTRYNAME>",
        f"            <BASICBASEPARTYNAME>{xml_escape(SUNDRY_DEBTORS)}</BASICBASEPARTYNAME>",
        "            <NUMBERINGSTYLE>Manual</NUMBERINGSTYLE>",
        "            <CSTFORMISSUETYPE>&#4; Not Applicable</CSTFORMISSUETYPE>",
        "            <CSTFORMRECVTYPE>&#4; Not Applicable</CSTFORMRECVTYPE>",
        "            <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>",
        "            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>",
        "            <VCHSTATUSTAXADJUSTMENT>Default</VCHSTATUSTAXADJUSTMENT>",
        "            <VCHSTATUSVOUCHERTYPE>Sales</VCHSTATUSVOUCHERTYPE>",
        f"            <VCHSTATUSTAXUNIT>{CMP_STATE} Registration</VCHSTATUSTAXUNIT>",
        "            <VCHGSTCLASS>&#4; Not Applicable</VCHGSTCLASS>",
        "            <VCHENTRYMODE>Accounting Invoice</VCHENTRYMODE>",
    ]

    flags_lines = [f"            <{k}>{v}</{k}>" for k, v in VOUCHER_FLAGS_SALES]
    ids = [
        f"            <EFFECTIVEDATE>{invoice_date}</EFFECTIVEDATE>",
        f"            <ALTERID> {alter_id}</ALTERID>",
        f"            <MASTERID> {alter_id}</MASTERID>",
        f"            <VOUCHERKEY>{19687271091400000 + alter_id}</VOUCHERKEY>",
        f"            <VOUCHERRETAINKEY>{alter_id}</VOUCHERRETAINKEY>",
        "            <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>",
    ]
    empty = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_EMPTY_LISTS_SALES]
    trailing = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_TRAILING_LISTS]

    le = lambda **kw: ledger_entry_block(container_tag="LEDGERENTRIES.LIST", **kw)
    entries = [
        le(name=SUNDRY_DEBTORS, amount=-total_payable, flags=LEDGER_FLAGS_PARTY_DR,
           bill_ref=invoice_no, bill_type=sd_bill_type),
        le(name=income_ledger, amount=net, flags=LEDGER_FLAGS_INCOME_CR),
        le(name=CGST, amount=cgst, flags=LEDGER_FLAGS_INCOME_CR),
        le(name=SGST, amount=sgst, flags=LEDGER_FLAGS_INCOME_CR),
    ]
    if abs(round_off) >= ROUND_OFF_TOLERANCE:
        # round_off > 0 → Dr ROUND OFF (loss), AMOUNT negative
        # round_off < 0 → Cr ROUND OFF (gain), AMOUNT positive (= -round_off)
        entries.append(le(name=ROUND_OFF, amount=-round_off, flags=round_off_flags(dr=round_off > 0)))

    body = head + flags_lines + ids + empty + entries + trailing + ["          </VOUCHER>"]
    return "\n".join(body)
