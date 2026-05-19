#!/usr/bin/env python3
"""Generate verbose Tally-export-style Sales vouchers for October 2025.

Output schema mirrors data/Transactions.xml (Tally native export): full status flags,
GST/buyer/consignee metadata, empty container lists, UTF-16 LE + BOM encoding.

Source: data/recon/canonical/invoice_oct2025_corrected.csv
Output: data/recon/output/sales_vouchers_oct2025_verbose.xml
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
DEFAULT_SRC = ROOT / "data" / "recon" / "canonical" / "invoice_oct2025_corrected.csv"
DEFAULT_OUT = ROOT / "data" / "recon" / "output" / "sales_vouchers_oct2025_verbose.xml"

COMPANY = "THE MANGAL VIEW RESIDENCY"
CMP_GSTIN = "08AABCJ1528Q1Z8"
CMP_STATE = "Rajasthan"
GUID_NAMESPACE = uuid.UUID("029dfefd-5996-4e71-8914-ec5a8528c655")

DEFAULT_PARTY_LEDGER = "Sundry Debtors"


def pick_party_ledger(business_source: str) -> str:
    return DEFAULT_PARTY_LEDGER


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


def gst_ledger(net: float, cgst: float, sgst: float) -> str:
    if net <= 0:
        return "SALE ACCOMODATION GST @ 12%"
    rate = round(((cgst + sgst) / net) * 100)
    if rate >= 17:
        return "SALE ACCOMODATION GST @ 18%"
    if rate >= 11:
        return "SALE ACCOMODATION GST @ 12%"
    return "SALE ACCOMODATION GST @ 5 %"


def make_guid(invoice_no: str) -> str:
    return str(uuid.uuid5(GUID_NAMESPACE, invoice_no))


# ---- common empty containers (appear in both VOUCHER and LEDGERENTRIES) ----
VOUCHER_EMPTY_LISTS = [
    "EWAYBILLDETAILS.LIST", "EXCLUDEDTAXATIONS.LIST", "OLDAUDITENTRIES.LIST",
    "ACCOUNTAUDITENTRIES.LIST", "AUDITENTRIES.LIST", "DUTYHEADDETAILS.LIST",
    "GSTADVADJDETAILS.LIST", "ALLINVENTORYENTRIES.LIST", "CONTRITRANS.LIST",
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
    "SERVICETAXDETAILS.LIST", "BANKALLOCATIONS.LIST", "BILLALLOCATIONS.LIST",
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

# Voucher-level status flags (key=value pairs, all No except IS*=Yes)
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
    ("USETRACKINGNUMBER", "No"), ("ISINVOICE", "Yes"), ("MFGJOURNAL", "No"),
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

# Ledger-entry-level flags
LEDGER_FLAGS_PARTY = [
    ("ISDEEMEDPOSITIVE", "Yes"),  # Sundry Debtors Dr
    ("LEDGERFROMITEM", "No"),
    ("REMOVEZEROENTRIES", "No"), ("ISPARTYLEDGER", "Yes"),
    ("GSTOVERRIDDEN", "No"), ("ISGSTASSESSABLEVALUEOVERRIDDEN", "No"),
    ("STRDISGSTAPPLICABLE", "No"), ("STRDGSTISPARTYLEDGER", "No"),
    ("STRDGSTISDUTYLEDGER", "No"), ("CONTENTNEGISPOS", "No"),
    ("ISLASTDEEMEDPOSITIVE", "Yes"), ("ISCAPVATTAXALTERED", "No"),
    ("ISCAPVATNOTCLAIMED", "No"),
]

LEDGER_FLAGS_INCOME = [
    ("ISDEEMEDPOSITIVE", "No"),  # Sale ledger / GST Cr
    ("LEDGERFROMITEM", "No"),
    ("REMOVEZEROENTRIES", "No"), ("ISPARTYLEDGER", "No"),
    ("GSTOVERRIDDEN", "No"), ("ISGSTASSESSABLEVALUEOVERRIDDEN", "No"),
    ("STRDISGSTAPPLICABLE", "No"), ("STRDGSTISPARTYLEDGER", "No"),
    ("STRDGSTISDUTYLEDGER", "No"), ("CONTENTNEGISPOS", "No"),
    ("ISLASTDEEMEDPOSITIVE", "No"), ("ISCAPVATTAXALTERED", "No"),
    ("ISCAPVATNOTCLAIMED", "No"),
]


def _bill_allocation_block(invoice_no: str, amount: float, bill_type: str = "New Ref") -> str:
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


def _round_off_flags(dr: bool) -> list[tuple[str, str]]:
    """Flag set for ROUND OFF entry. Dr=loss, Cr=gain. Non-party ledger."""
    base = list(LEDGER_FLAGS_INCOME if not dr else LEDGER_FLAGS_PARTY)
    # ROUND OFF is never a party ledger.
    return [(k, ("No" if k == "ISPARTYLEDGER" else v)) for k, v in base]


def emit_ledger_entry(name: str, amount: float, flags: list[tuple[str, str]],
                      bill_ref: str | None = None, bill_type: str = "New Ref") -> str:
    lines = [
        "            <LEDGERENTRIES.LIST>",
        '              <OLDAUDITENTRYIDS.LIST TYPE="Number">',
        "                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>",
        "              </OLDAUDITENTRYIDS.LIST>",
        f"              <LEDGERNAME>{xml_escape(name)}</LEDGERNAME>",
        "              <GSTCLASS>&#4; Not Applicable</GSTCLASS>",
    ]
    for k, v in flags:
        lines.append(f"              <{k}>{v}</{k}>")
    lines.append(f"              <AMOUNT>{amount:.2f}</AMOUNT>")
    for lst in LEDGER_EMPTY_LISTS:
        if lst == "BILLALLOCATIONS.LIST" and bill_ref:
            lines.append(_bill_allocation_block(bill_ref, amount, bill_type))
        else:
            lines.append(f"              <{lst}>              </{lst}>")
    lines.append("            </LEDGERENTRIES.LIST>")
    return "\n".join(lines)


def emit_voucher(row: dict, alter_id: int) -> str:
    invoice_no = row["Invoice #"].strip()
    invoice_date = fdate(row["Invoice date"])
    guest = (row.get("Guest Name") or "").strip() or "Unknown Guest"
    net = ffloat(row.get("Net Amount", "0"))
    cgst = ffloat(row.get("Tax Amount", "0"))
    sgst = ffloat(row.get("Tax Amount.1", "0"))
    gross = ffloat(row.get("Gross Amount", "0"))
    discount = ffloat(row.get("Discount Amount", "0"))
    adjustment = ffloat(row.get("Adjustment", "0"))
    # Total Payable is what we debit Sundry Debtors at (customer's actual obligation).
    total_payable = ffloat(row.get("Total Payable", "0")) or (gross - discount - adjustment)
    # ROUND OFF Dr entry absorbs the discount + adjustment so the voucher balances.
    round_off = gross - total_payable

    if gross <= 0:
        return ""

    income = gst_ledger(net, cgst, sgst)
    guid = make_guid(invoice_no)
    remote_id = f"{guid}-{alter_id:08x}"
    vch_key = f"{GUID_NAMESPACE}-0000b30e:{alter_id:08x}"
    narration = f"INVOICE NO:-{invoice_no}, {guest}"

    party_addr = guest.upper()
    party_name = pick_party_ledger(row.get("Business Source", ""))

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
        f"            <PARTYNAME>{xml_escape(party_name)}</PARTYNAME>",
        f'            <GSTREGISTRATION TAXTYPE="GST" TAXREGISTRATION="{CMP_GSTIN}">{CMP_STATE} Registration</GSTREGISTRATION>',
        f"            <CMPGSTIN>{CMP_GSTIN}</CMPGSTIN>",
        f"            <PARTYLEDGERNAME>{xml_escape(party_name)}</PARTYLEDGERNAME>",
        f"            <VOUCHERNUMBER>{xml_escape(invoice_no)}</VOUCHERNUMBER>",
        f"            <BASICBUYERNAME>{xml_escape(guest)}</BASICBUYERNAME>",
        "            <CMPGSTREGISTRATIONTYPE>Regular</CMPGSTREGISTRATIONTYPE>",
        f"            <REFERENCE>{xml_escape(invoice_no)}</REFERENCE>",
        f"            <PARTYMAILINGNAME>{xml_escape(party_name)}</PARTYMAILINGNAME>",
        f"            <CONSIGNEEMAILINGNAME>{xml_escape(guest)}</CONSIGNEEMAILINGNAME>",
        f"            <CONSIGNEESTATENAME>{CMP_STATE}</CONSIGNEESTATENAME>",
        f"            <CMPGSTSTATE>{CMP_STATE}</CMPGSTSTATE>",
        "            <CONSIGNEECOUNTRYNAME>India</CONSIGNEECOUNTRYNAME>",
        f"            <BASICBASEPARTYNAME>{xml_escape(party_name)}</BASICBASEPARTYNAME>",
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

    flags = [f"            <{k}>{v}</{k}>" for k, v in VOUCHER_FLAGS]

    ids = [
        f"            <EFFECTIVEDATE>{invoice_date}</EFFECTIVEDATE>",
        f"            <ALTERID> {alter_id}</ALTERID>",
        f"            <MASTERID> {alter_id}</MASTERID>",
        f"            <VOUCHERKEY>{19687271091400000 + alter_id}</VOUCHERKEY>",
        f"            <VOUCHERRETAINKEY>{alter_id}</VOUCHERRETAINKEY>",
        "            <VOUCHERNUMBERSERIES>Default</VOUCHERNUMBERSERIES>",
    ]
    # Reorder: EFFECTIVEDATE goes within flags block per sample (after ISOPTIONAL)
    # Easiest: insert EFFECTIVEDATE inline between flag groups via simple append at end
    # of flag section; followed by remaining flags and trailing IDs.

    empty_lists = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_EMPTY_LISTS]
    trailing_lists = [f"            <{lst}>            </{lst}>" for lst in VOUCHER_TRAILING_LISTS]

    # bill_opens_with comes from the canonical CSV (aggregator's pre-pass):
    #   "sales"   → Sales is the earliest event on this invoice → New Ref
    #   "journal" → an advance payment opened the bill earlier  → Agst Ref
    bill_opens_with = (row.get("bill_opens_with") or "sales").strip().lower()
    sd_bill_type = "New Ref" if bill_opens_with == "sales" else "Agst Ref"
    party_entry = emit_ledger_entry(
        party_name, -total_payable, LEDGER_FLAGS_PARTY,
        bill_ref=invoice_no, bill_type=sd_bill_type,
    )
    income_entry = emit_ledger_entry(income, net, LEDGER_FLAGS_INCOME)
    cgst_entry = emit_ledger_entry("CGST", cgst, LEDGER_FLAGS_INCOME)
    sgst_entry = emit_ledger_entry("SGST", sgst, LEDGER_FLAGS_INCOME)
    entries = [party_entry, income_entry, cgst_entry, sgst_entry]
    if abs(round_off) >= 0.005:
        # round_off > 0 means gross > total_payable (haircut/loss to us) -> Dr ROUND OFF.
        # round_off < 0 means we got more than billed (rare) -> Cr ROUND OFF.
        if round_off > 0:
            entries.append(
                emit_ledger_entry("ROUND OFF", -round_off, _round_off_flags(dr=True))
            )
        else:
            entries.append(
                emit_ledger_entry("ROUND OFF", -round_off, _round_off_flags(dr=False))
            )

    body = head + flags + ids + empty_lists + entries + trailing_lists + ["          </VOUCHER>"]

    return "\n".join(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(DEFAULT_SRC), help="canonical invoice CSV")
    ap.add_argument("--output", default=str(DEFAULT_OUT), help="output XML path")
    ap.add_argument("--alter-id-base", type=int, default=60000)
    args = ap.parse_args()
    src_csv = Path(args.input)
    out_xml = Path(args.output)
    if not src_csv.exists():
        print(f"ERROR: source CSV not found: {src_csv}", file=sys.stderr)
        return 1

    vouchers: list[str] = []
    skipped = 0
    alter_id_base = args.alter_id_base

    with src_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            voucher = emit_voucher(row, alter_id_base + i)
            if not voucher:
                skipped += 1
                continue
            vouchers.append(
                '        <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
                + voucher + "\n"
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

    out_xml.parent.mkdir(parents=True, exist_ok=True)
    # UTF-16 LE with BOM to match Tally native export
    out_xml.write_bytes(b"\xff\xfe" + envelope.encode("utf-16-le"))

    print(f"Wrote {len(vouchers)} Sales vouchers ({skipped} skipped zero-gross)")
    print(f"  -> {out_xml}")
    print(f"  size: {out_xml.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
