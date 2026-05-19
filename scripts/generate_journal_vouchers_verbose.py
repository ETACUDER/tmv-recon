#!/usr/bin/env python3
"""Generate verbose Tally-export-style Journal vouchers from payment canonical CSV.

Pattern (Journal, "As Voucher" entry mode):
    Dr  <payment_ledger>     -amount  (ISDEEMEDPOSITIVE=Yes)
    Cr  Sundry Debtors       +amount  (ISDEEMEDPOSITIVE=No)
with BILLALLOCATIONS.LIST on both entries referencing the invoice #.

Mapping (Settlement/Particular -> Tally ledger):
    Cash          -> SANDEEP SHARMA IMP A/C.
    UPI           -> CARD / UPI / PAYTM / G PAY
    Credit Card   -> CARD / UPI / PAYTM / G PAY
    Debit Card    -> CARD / UPI / PAYTM / G PAY
    Agoda         -> AGODA SDR
    Booking.com   -> BOOKING.COM SDR
    Goibibo       -> GOIBIBO / MAKE MY TRIP

Output: UTF-16 LE + BOM XML matching Tally native Journal voucher schema.
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "data" / "recon" / "canonical" / "payment_apr2026.csv"
DEFAULT_OUT = ROOT / "data" / "recon" / "output" / "journal_vouchers_apr2026_verbose.xml"

COMPANY = "THE MANGAL VIEW RESIDENCY"
CMP_GSTIN = "08AABCJ1528Q1Z8"
CMP_STATE = "Rajasthan"
GUID_NAMESPACE = uuid.UUID("029dfefd-5996-4e71-8914-ec5a8528c655")

PARTY_DEBTOR = "Sundry Debtors"

MODE_TO_LEDGER = {
    "CASH": "SANDEEP SHARMA IMP A/C.",
    "UPI": "CARD / UPI / PAYTM / G PAY",
    "CREDIT CARD": "CARD / UPI / PAYTM / G PAY",
    "DEBIT CARD": "CARD / UPI / PAYTM / G PAY",
    "AGODA": "AGODA SDR",
    "BOOKING.COM": "BOOKING.COM SDR",
    "GOIBIBO": "GOIBIBO / MAKE MY TRIP",
}

# OTA receivable ledgers — these get a fresh "New Ref" bill on the Dr side
# (we are now owed by the OTA platform).
OTA_LEDGERS = {"AGODA SDR", "BOOKING.COM SDR", "GOIBIBO / MAKE MY TRIP"}


def pick_payment_ledger(mode: str) -> str | None:
    """Return target Tally ledger; None if unmapped (caller skips)."""
    key = (mode or "").strip().upper()
    return MODE_TO_LEDGER.get(key)


def fdate(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    return s


def ffloat(s: str) -> float:
    s = (s or "").strip()
    if not s or s.lower() == "nan":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def make_guid(seed: str) -> str:
    return str(uuid.uuid5(GUID_NAMESPACE, seed))


# Voucher-level empty containers (Journal has fewer than Sales)
VOUCHER_EMPTY_LISTS = [
    "EWAYBILLDETAILS.LIST", "EXCLUDEDTAXATIONS.LIST", "OLDAUDITENTRIES.LIST",
    "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "DUTYHEADDETAILS.LIST",
    "GSTADVADJDETAILS.LIST", "CONTRITRANS.LIST",
    "EWAYBILLERRORLIST.LIST", "IRNERRORLIST.LIST", "HARYANAVAT.LIST",
    "SUPPLEMENTARYDUTYHEADDETAILS.LIST", "INVOICEDELNOTES.LIST",
    "INVOICEORDERLIST.LIST", "INVOICEINDENTLIST.LIST", "ATTENDANCEENTRIES.LIST",
    "ORIGINVOICEDETAILS.LIST", "INVOICEEXPORTLIST.LIST",
]

VOUCHER_TRAILING_LISTS = [
    "GST.LIST", "STKJRNLADDLCOSTDETAILS.LIST", "GSTBUYERADDRESS.LIST",
    "GSTCONSIGNEEADDRESS.LIST", "PAYROLLMODEOFPAYMENT.LIST", "ATTDRECORDS.LIST",
    "GSTEWAYCONSIGNORADDRESS.LIST", "GSTEWAYCONSIGNEEADDRESS.LIST",
    "TEMPGSTRATEDETAILS.LIST", "TEMPGSTADVADJUSTED.LIST",
]

LEDGER_EMPTY_LISTS = [
    "SERVICETAXDETAILS.LIST", "BANKALLOCATIONS.LIST",
    "INTERESTCOLLECTION.LIST", "OLDAUDITENTRIES.LIST",
    "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "INPUTCRALLOCS.LIST",
    "DUTYHEADDETAILS.LIST", "EXCISEDUTYHEADDETAILS.LIST", "RATEDETAILS.LIST",
    "SUMMARYALLOCS.LIST", "CENVATDUTYALLOCATIONS.LIST", "STPYMTDETAILS.LIST",
    "EXCISEPAYMENTALLOCATIONS.LIST", "TAXBILLALLOCATIONS.LIST",
    "TAXOBJECTALLOCATIONS.LIST", "TDSEXPENSEALLOCATIONS.LIST",
    "VATSTATUTORYDETAILS.LIST", "COSTTRACKALLOCATIONS.LIST",
    "REFVOUCHERDETAILS.LIST", "INVOICEWISEDETAILS.LIST", "VATITCDETAILS.LIST",
    "ADVANCETAXDETAILS.LIST", "TAXTYPEALLOCATIONS.LIST",
]

VOUCHER_FLAGS = [
    ("DIFFACTUALQTY", "No"), ("ISMSTFROMSYNC", "No"), ("ISDELETED", "No"),
    ("ISSECURITYONWHENENTERED", "No"), ("ASORIGINAL", "No"), ("AUDITED", "No"),
    ("ISCOMMONPARTY", "No"), ("FORJOBCOSTING", "No"), ("ISOPTIONAL", "No"),
    ("USEFOREXCISE", "No"), ("ISFORJOBWORKIN", "No"),
    ("ALLOWCONSUMPTION", "No"), ("USEFORINTEREST", "No"),
    ("USEFORGAINLOSS", "No"), ("USEFORGODOWNTRANSFER", "No"),
    ("USEFORCOMPOUND", "No"), ("USEFORSERVICETAX", "No"),
    ("ISREVERSECHARGEAPPLICABLE", "No"), ("ISSYSTEM", "No"),
    ("ISFETCHEDONLY", "No"), ("ISGSTOVERRIDDEN", "No"),
    ("ISCANCELLED", "No"), ("ISONHOLD", "No"), ("ISSUMMARY", "No"),
    ("ISECOMMERCESUPPLY", "No"), ("ISBOENOTAPPLICABLE", "No"),
    ("ISGSTSECSEVENAPPLICABLE", "No"), ("IGNOREEINVVALIDATION", "No"),
    ("CMPGSTISOTHTERRITORYASSESSEE", "No"),
    ("PARTYGSTISOTHTERRITORYASSESSEE", "No"), ("IRNJSONEXPORTED", "No"),
    ("IRNCANCELLED", "No"), ("IGNOREGSTCONFLICTINMIG", "No"),
    ("ISOPBALTRANSACTION", "No"), ("IGNOREGSTFORMATVALIDATION", "No"),
    ("ISELIGIBLEFORITC", "Yes"), ("IGNOREGSTOPTIONALUNCERTAIN", "No"),
    ("UPDATESUMMARYVALUES", "No"), ("ISEWAYBILLAPPLICABLE", "No"),
    ("ISDELETEDRETAINED", "No"), ("ISNULL", "No"), ("ISEXCISEVOUCHER", "No"),
    ("EXCISETAXOVERRIDE", "No"), ("USEFORTAXUNITTRANSFER", "No"),
    ("ISEXER1NOPOVERWRITE", "No"), ("ISEXF2NOPOVERWRITE", "No"),
    ("ISEXER3NOPOVERWRITE", "No"), ("IGNOREPOSVALIDATION", "No"),
    ("EXCISEOPENING", "No"), ("USEFORFINALPRODUCTION", "No"),
    ("ISTDSOVERRIDDEN", "No"), ("ISTCSOVERRIDDEN", "No"),
    ("ISTDSTCSCASHVCH", "No"), ("INCLUDEADVPYMTVCH", "No"),
    ("ISSUBWORKSCONTRACT", "No"), ("ISVATOVERRIDDEN", "No"),
    ("IGNOREORIGVCHDATE", "No"), ("ISVATPAIDATCUSTOMS", "No"),
    ("ISDECLAREDTOCUSTOMS", "No"), ("VATADVANCEPAYMENT", "No"),
    ("VATADVPAY", "No"), ("ISCSTDELCAREDGOODSSALES", "No"),
    ("ISVATRESTAXINV", "No"), ("ISSERVICETAXOVERRIDDEN", "No"),
    ("ISISDVOUCHER", "No"), ("ISEXCISEOVERRIDDEN", "No"),
    ("ISEXCISESUPPLYVCH", "No"), ("GSTNOTEXPORTED", "No"),
    ("IGNOREGSTINVALIDATION", "No"), ("ISGSTREFUND", "No"),
    ("OVRDNEWAYBILLAPPLICABILITY", "No"), ("ISVATPRINCIPALACCOUNT", "No"),
    ("VCHSTATUSISVCHNUMUSED", "No"), ("VCHGSTSTATUSISINCLUDED", "No"),
    ("VCHGSTSTATUSISUNCERTAIN", "No"), ("VCHGSTSTATUSISEXCLUDED", "No"),
    ("VCHGSTSTATUSISAPPLICABLE", "No"),
    ("VCHGSTSTATUSISGSTR2BRECONCILED", "No"),
    ("VCHGSTSTATUSISGSTR2BONLYINPORTAL", "No"),
    ("VCHGSTSTATUSISGSTR2BONLYINBOOKS", "No"),
    ("VCHGSTSTATUSISGSTR2BMISMATCH", "No"),
    ("VCHGSTSTATUSISGSTR2BINDIFFPERIOD", "No"),
    ("VCHGSTSTATUSISRETEFFDATEOVERRDN", "No"),
    ("VCHGSTSTATUSISOVERRDN", "No"),
    ("VCHGSTSTATUSISSTATINDIFFDATE", "No"),
    ("VCHGSTSTATUSISRETINDIFFDATE", "No"),
    ("VCHGSTSTATUSMAINSECTIONEXCLUDED", "No"),
    ("VCHGSTSTATUSISBRANCHTRANSFEROUT", "No"),
    ("VCHGSTSTATUSISSYSTEMSUMMARY", "No"),
    ("VCHSTATUSISUNREGISTEREDRCM", "No"), ("VCHSTATUSISOPTIONAL", "No"),
    ("VCHSTATUSISCANCELLED", "No"), ("VCHSTATUSISDELETED", "No"),
    ("VCHSTATUSISOPENINGBALANCE", "No"), ("VCHSTATUSISFETCHEDONLY", "No"),
    ("VCHGSTSTATUSISOPTIONALUNCERTAIN", "No"),
    ("VCHSTATUSISREACCEPTFORHSNDONE", "No"),
    ("VCHSTATUSISREACCEPHSNSIXONEDONE", "No"),
    ("PAYMENTLINKHASMULTIREF", "No"), ("ISSHIPPINGWITHINSTATE", "No"),
    ("ISOVERSEASTOURISTTRANS", "No"), ("ISDESIGNATEDZONEPARTY", "No"),
    ("HASCASHFLOW", "No"), ("ISPOSTDATED", "No"),
    ("USETRACKINGNUMBER", "No"), ("ISINVOICE", "No"),
    ("MFGJOURNAL", "No"),
    ("HASDISCOUNTS", "No"), ("ASPAYSLIP", "No"), ("ISCOSTCENTRE", "No"),
    ("ISSTXNONREALIZEDVCH", "No"), ("ISEXCISEMANUFACTURERON", "No"),
    ("ISBLANKCHEQUE", "No"), ("ISVOID", "No"), ("ORDERLINESTATUS", "No"),
    ("VATISAGNSTCANCSALES", "No"), ("VATISPURCEXEMPTED", "No"),
    ("ISVATRESTAXINVOICE", "No"), ("VATISASSESABLECALCVCH", "No"),
    ("ISVATDUTYPAID", "Yes"), ("ISDELIVERYSAMEASCONSIGNEE", "No"),
    ("ISDISPATCHSAMEASCONSIGNOR", "No"), ("ISDELETEDVCHRETAINED", "No"),
    ("VCHONLYADDLINFOUPDATED", "No"), ("CHANGEVCHMODE", "No"),
    ("RESETIRNQRCODE", "No"),
]

LEDGER_FLAGS_DR = [  # payment ledger Dr side
    ("ISDEEMEDPOSITIVE", "Yes"), ("LEDGERFROMITEM", "No"),
    ("REMOVEZEROENTRIES", "No"), ("ISPARTYLEDGER", "Yes"),
    ("GSTOVERRIDDEN", "No"), ("ISGSTASSESSABLEVALUEOVERRIDDEN", "No"),
    ("STRDISGSTAPPLICABLE", "No"), ("STRDGSTISPARTYLEDGER", "No"),
    ("STRDGSTISDUTYLEDGER", "No"), ("CONTENTNEGISPOS", "No"),
    ("ISLASTDEEMEDPOSITIVE", "Yes"), ("ISCAPVATTAXALTERED", "No"),
    ("ISCAPVATNOTCLAIMED", "No"),
]

LEDGER_FLAGS_CR = [  # Sundry Debtors Cr side
    ("ISDEEMEDPOSITIVE", "No"), ("LEDGERFROMITEM", "No"),
    ("REMOVEZEROENTRIES", "No"), ("ISPARTYLEDGER", "Yes"),
    ("GSTOVERRIDDEN", "No"), ("ISGSTASSESSABLEVALUEOVERRIDDEN", "No"),
    ("STRDISGSTAPPLICABLE", "No"), ("STRDGSTISPARTYLEDGER", "No"),
    ("STRDGSTISDUTYLEDGER", "No"), ("CONTENTNEGISPOS", "No"),
    ("ISLASTDEEMEDPOSITIVE", "No"), ("ISCAPVATTAXALTERED", "No"),
    ("ISCAPVATNOTCLAIMED", "No"),
]


def emit_bill_allocation(invoice_no: str, amount: float, bill_type: str) -> str:
    return (
        "              <BILLALLOCATIONS.LIST>\n"
        f"                <NAME>{xml_escape(invoice_no)}</NAME>\n"
        f"                <BILLTYPE>{bill_type}</BILLTYPE>\n"
        "                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\n"
        f"                <AMOUNT>{amount:.2f}</AMOUNT>\n"
        "                <INTERESTCOLLECTION.LIST>              </INTERESTCOLLECTION.LIST>\n"
        "                <STBILLCATEGORIES.LIST>              </STBILLCATEGORIES.LIST>\n"
        "              </BILLALLOCATIONS.LIST>"
    )


def emit_ledger_entry(name: str, amount: float, flags: list[tuple[str, str]],
                      invoice_no: str, bill_type: str | None) -> str:
    lines = [
        "            <ALLLEDGERENTRIES.LIST>",
        '              <OLDAUDITENTRYIDS.LIST TYPE="Number">',
        "                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>",
        "              </OLDAUDITENTRYIDS.LIST>",
        f"              <LEDGERNAME>{xml_escape(name)}</LEDGERNAME>",
        "              <GSTCLASS>&#4; Not Applicable</GSTCLASS>",
    ]
    for k, v in flags:
        lines.append(f"              <{k}>{v}</{k}>")
    lines.append(f"              <AMOUNT>{amount:.2f}</AMOUNT>")
    lines.append("              <SERVICETAXDETAILS.LIST>              </SERVICETAXDETAILS.LIST>")
    lines.append("              <BANKALLOCATIONS.LIST>              </BANKALLOCATIONS.LIST>")
    if bill_type:
        lines.append(emit_bill_allocation(invoice_no, amount, bill_type))
    else:
        lines.append("              <BILLALLOCATIONS.LIST>              </BILLALLOCATIONS.LIST>")
    for lst in LEDGER_EMPTY_LISTS[2:]:  # already emitted ServiceTax + Bank
        if lst == "BILLALLOCATIONS.LIST":
            continue  # handled above
        lines.append(f"              <{lst}>              </{lst}>")
    lines.append("            </ALLLEDGERENTRIES.LIST>")
    return "\n".join(lines)


def emit_voucher(row: dict, alter_id: int) -> str | None:
    invoice_no = row["Invoice #"].strip()
    invoice_date = fdate(row["Invoice date"])
    mode = row["Settlement/Particular"].strip()
    amount = ffloat(row["Settlement Amount"])
    guest = (row.get("Guest Name") or "").strip()

    if amount <= 0:
        return None

    payment_ledger = pick_payment_ledger(mode)
    if not payment_ledger:
        return None  # unmapped mode

    # Include alter_id so identical (invoice, mode, amount) splits remain distinct GUIDs.
    guid = make_guid(f"journal:{invoice_no}:{mode}:{amount}:{alter_id}")
    remote_id = f"{guid}-{alter_id:08x}"
    vch_key = f"{GUID_NAMESPACE}-0000c000:{alter_id:08x}"
    vch_number = invoice_no
    narration = f"BEING PAID THROUGH {mode.upper()} AGAINST INVOICE NO:{invoice_no}"
    if guest:
        narration += f" {guest.upper()}"

    head = [
        f'          <VOUCHER REMOTEID="{remote_id}" VCHKEY="{vch_key}" '
        f'VCHTYPE="Journal" ACTION="Create" OBJVIEW="Accounting Voucher View">',
        '            <OLDAUDITENTRYIDS.LIST TYPE="Number">',
        "              <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>",
        "            </OLDAUDITENTRYIDS.LIST>",
        f"            <DATE>{invoice_date}</DATE>",
        f"            <REFERENCEDATE>{invoice_date}</REFERENCEDATE>",
        f"            <VCHSTATUSDATE>{invoice_date}</VCHSTATUSDATE>",
        f"            <GUID>{guid}</GUID>",
        f"            <NARRATION>{xml_escape(narration)}</NARRATION>",
        "            <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>",
        f'            <GSTREGISTRATION TAXTYPE="GST" TAXREGISTRATION="{CMP_GSTIN}">{CMP_STATE} Registration</GSTREGISTRATION>',
        f"            <CMPGSTIN>{CMP_GSTIN}</CMPGSTIN>",
        f"            <PARTYLEDGERNAME>{xml_escape(payment_ledger)}</PARTYLEDGERNAME>",
        f"            <VOUCHERNUMBER>{xml_escape(vch_number)}</VOUCHERNUMBER>",
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
    flags = [f"            <{k}>{v}</{k}>" for k, v in VOUCHER_FLAGS]
    ids = [
        f"            <EFFECTIVEDATE>{invoice_date}</EFFECTIVEDATE>",
        f"            <ALTERID> {alter_id}</ALTERID>",
        f"            <MASTERID> {alter_id}</MASTERID>",
        f"            <VOUCHERKEY>{19687271091500000 + alter_id}</VOUCHERKEY>",
        f"            <VOUCHERRETAINKEY>{alter_id}</VOUCHERRETAINKEY>",
        "            <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>",
    ]
    empty = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_EMPTY_LISTS]
    trailing = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_TRAILING_LISTS]

    # Dr side: OTA platform gets New Ref (we now owe-from-OTA), others skip bill alloc.
    dr_bill_type = "New Ref" if payment_ledger in OTA_LEDGERS else None
    # Cr side: always Agst Ref to settle the Sundry Debtors bill created by Sales.
    dr_entry = emit_ledger_entry(payment_ledger, -amount, LEDGER_FLAGS_DR, invoice_no, dr_bill_type)
    cr_entry = emit_ledger_entry(PARTY_DEBTOR, amount, LEDGER_FLAGS_CR, invoice_no, "Agst Ref")

    return "\n".join(head + flags + ids + empty + [dr_entry, cr_entry] + trailing + ["          </VOUCHER>"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_SRC))
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    ap.add_argument("--alter-id-base", type=int, default=80000)
    args = ap.parse_args()
    src = Path(args.input)
    out = Path(args.output)
    if not src.exists():
        print(f"ERROR: source CSV not found: {src}", file=sys.stderr)
        return 1

    vouchers: list[str] = []
    skipped_unmapped: list[str] = []
    skipped_zero = 0

    with src.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            amount = ffloat(row["Settlement Amount"])
            if amount <= 0:
                skipped_zero += 1
                continue
            mode = (row["Settlement/Particular"] or "").strip()
            if not pick_payment_ledger(mode):
                skipped_unmapped.append(mode)
                continue
            v = emit_voucher(row, args.alter_id_base + i)
            if v:
                vouchers.append(
                    '        <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
                    + v + "\n"
                    + "        </TALLYMESSAGE>"
                )

    body = "\n".join(vouchers)
    envelope = (
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <TALLYREQUEST>Import Data</TALLYREQUEST>\n"
        "  </HEADER>\n"
        "  <BODY>\n"
        "    <IMPORTDATA>\n"
        "      <REQUESTDESC>\n"
        "        <REPORTNAME>All Masters</REPORTNAME>\n"
        "        <STATICVARIABLES>\n"
        f"          <SVCURRENTCOMPANY>{xml_escape(COMPANY)}</SVCURRENTCOMPANY>\n"
        "        </STATICVARIABLES>\n"
        "      </REQUESTDESC>\n"
        "      <REQUESTDATA>\n"
        f"{body}\n"
        "      </REQUESTDATA>\n"
        "    </IMPORTDATA>\n"
        "  </BODY>\n"
        "</ENVELOPE>\n"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\xff\xfe" + envelope.encode("utf-16-le"))

    print(f"Wrote {len(vouchers)} Journal vouchers")
    print(f"  -> {out}")
    print(f"  size: {out.stat().st_size:,} bytes")
    if skipped_zero:
        print(f"  skipped zero-amount: {skipped_zero}")
    if skipped_unmapped:
        from collections import Counter
        unm = Counter(skipped_unmapped)
        print(f"  skipped unmapped modes: {len(skipped_unmapped)}")
        for m, c in unm.most_common():
            print(f"    {m}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
