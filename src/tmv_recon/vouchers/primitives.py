"""Low-level XML rendering primitives — pure shape, no business logic.

These functions handle:
  * deterministic GUID generation,
  * the ENVELOPE wrapper,
  * one BILLALLOCATIONS.LIST block,
  * one (ALL)LEDGERENTRIES.LIST block,
  * UTF-16 LE+BOM file write.

Business decisions (which ledger, which bill type, what amount) live in
`sales.py` / `journal.py` and are passed in as arguments.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from .config import COMPANY, GUID_NAMESPACE
from .flags import LEDGER_EMPTY_LISTS


# ----- Helpers -----
def make_guid(seed: str) -> str:
    """Deterministic per-voucher GUID. Re-runs overwrite, never duplicate."""
    return str(uuid.uuid5(GUID_NAMESPACE, seed))


def fdate(s: str) -> str:
    """Parse a date string to Tally's YYYYMMDD format. Returns input unchanged on failure."""
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


# ----- XML blocks -----
def bill_allocation_block(invoice_no: str, amount: float, bill_type: str) -> str:
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


def ledger_entry_block(
    *,
    container_tag: str,                 # "LEDGERENTRIES.LIST" or "ALLLEDGERENTRIES.LIST"
    name: str,
    amount: float,
    flags: list[tuple[str, str]],
    bill_ref: str | None = None,
    bill_type: str = "New Ref",
) -> str:
    """Render one ledger entry (Sales uses LEDGERENTRIES.LIST, Journal uses ALL...)."""
    lines = [
        f"            <{container_tag}>",
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
            lines.append(bill_allocation_block(bill_ref, amount, bill_type))
        else:
            lines.append(f"              <{lst}>              </{lst}>")
    lines.append(f"            </{container_tag}>")
    return "\n".join(lines)


# ----- Envelope wrapper + file write -----
def wrap_envelope(tallymessages: list[str]) -> str:
    body = "\n".join(tallymessages)
    return (
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


def write_xml(out_path: Path, envelope_str: str) -> None:
    """Write XML to disk using UTF-16 LE + BOM (Tally native export encoding)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"\xff\xfe" + envelope_str.encode("utf-16-le"))


def wrap_tally_message(voucher_xml: str) -> str:
    return (
        '        <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        + voucher_xml + "\n"
        + "        </TALLYMESSAGE>"
    )
