"""Build Tally XML import payloads.

Reference shapes (see docs/tally-integration.md):
- Voucher import: ENVELOPE > HEADER(TALLYREQUEST=Import,TYPE=Data,ID=Vouchers)
                + BODY > DATA > TALLYMESSAGE > VOUCHER
- Master import: ID=All Masters, TALLYMESSAGE contains LEDGER/GROUP entries.
"""
from __future__ import annotations
from datetime import date
from xml.sax.saxutils import escape
from .models import Voucher, Ledger


def _x(s: str) -> str: return escape(s or "")
def _d(d: date) -> str: return d.strftime("%Y%m%d")


def voucher_message(v: Voucher) -> str:
    entries = []
    for e in v.entries:
        flags = ""
        if e.is_party_ledger:
            flags += "          <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        entries.append(
            "        <ALLLEDGERENTRIES.LIST>\n"
            f"          <LEDGERNAME>{_x(e.ledger)}</LEDGERNAME>\n"
            f"          <ISDEEMEDPOSITIVE>{'Yes' if e.is_deemed_positive else 'No'}</ISDEEMEDPOSITIVE>\n"
            f"{flags}"
            f"          <AMOUNT>{e.amount:.2f}</AMOUNT>\n"
            "        </ALLLEDGERENTRIES.LIST>"
        )
    party = f"        <PARTYLEDGERNAME>{_x(v.party_ledger)}</PARTYLEDGERNAME>\n" if v.party_ledger else ""
    ref = f"        <REFERENCE>{_x(v.reference)}</REFERENCE>\n" if v.reference else ""
    return (
        '    <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'      <VOUCHER VCHTYPE="{_x(v.voucher_type)}" ACTION="Create">\n'
        f"        <DATE>{_d(v.date)}</DATE>\n"
        f"        <VOUCHERTYPENAME>{_x(v.voucher_type)}</VOUCHERTYPENAME>\n"
        f"        <VOUCHERNUMBER>{_x(v.voucher_number)}</VOUCHERNUMBER>\n"
        f"        <NARRATION>{_x(v.narration)}</NARRATION>\n"
        f"{ref}{party}"
        + "\n".join(entries) + "\n"
        "      </VOUCHER>\n"
        "    </TALLYMESSAGE>"
    )


def vouchers_envelope(vouchers: list[Voucher], company: str = "") -> str:
    sv = (f"<STATICVARIABLES><SVCURRENTCOMPANY>{_x(company)}</SVCURRENTCOMPANY></STATICVARIABLES>"
          if company else "")
    body = "\n".join(voucher_message(v) for v in vouchers)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <VERSION>1</VERSION>\n"
        "    <TALLYREQUEST>Import</TALLYREQUEST>\n"
        "    <TYPE>Data</TYPE>\n"
        "    <ID>Vouchers</ID>\n"
        "  </HEADER>\n"
        f"  <BODY>\n    <DESC>{sv}</DESC>\n    <DATA>\n{body}\n    </DATA>\n  </BODY>\n"
        "</ENVELOPE>\n"
    )


def ledger_message(l: Ledger) -> str:
    addr = ""
    if l.address:
        addr = '        <ADDRESS.LIST TYPE="String">\n' + \
               "".join(f"          <ADDRESS>{_x(a)}</ADDRESS>\n" for a in l.address) + \
               "        </ADDRESS.LIST>\n"
    extras = ""
    if l.opening_balance:
        extras += f"        <OPENINGBALANCE>{l.opening_balance:.2f}</OPENINGBALANCE>\n"
    if l.email:
        extras += f"        <EMAIL>{_x(l.email)}</EMAIL>\n"
    if l.pincode:
        extras += f"        <PINCODE>{_x(l.pincode)}</PINCODE>\n"
    return (
        '    <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'      <LEDGER NAME="{_x(l.name)}" Action="Create">\n'
        f"        <NAME>{_x(l.name)}</NAME>\n"
        f"        <PARENT>{_x(l.parent)}</PARENT>\n"
        f"{addr}{extras}"
        "      </LEDGER>\n"
        "    </TALLYMESSAGE>"
    )


def masters_envelope(ledgers: list[Ledger], company: str = "", dup: str = "@@DUPCOMBINE") -> str:
    """dup: @@DUPCOMBINE | @@DUPIGNORE | @@DUPMODIFY"""
    sv_parts = [f"<IMPORTDUPS>{dup}</IMPORTDUPS>"]
    if company:
        sv_parts.append(f"<SVCURRENTCOMPANY>{_x(company)}</SVCURRENTCOMPANY>")
    sv = "<STATICVARIABLES>" + "".join(sv_parts) + "</STATICVARIABLES>"
    body = "\n".join(ledger_message(l) for l in ledgers)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <VERSION>1</VERSION>\n"
        "    <TALLYREQUEST>Import</TALLYREQUEST>\n"
        "    <TYPE>Data</TYPE>\n"
        "    <ID>All Masters</ID>\n"
        "  </HEADER>\n"
        f"  <BODY>\n    <DESC>{sv}</DESC>\n    <DATA>\n{body}\n    </DATA>\n  </BODY>\n"
        "</ENVELOPE>\n"
    )
