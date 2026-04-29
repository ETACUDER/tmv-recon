"""End-to-end round-trip test against the live Tally HTTP endpoint.

Steps:
  1. POST CREATE COMPANY ('TMV Recon Test')
  2. POST CREATE MASTERS (groups + ledgers needed for Sales + Journal)
  3. POST SALES VOUCHER (with canonical narration "INVOICE NO -25-26/T1 TEST GUEST")
  4. POST JOURNAL VOUCHER (with canonical narration "BEING PAID THROUGH UPI AGAINST INVOICE NO:25-26/T1 TEST GUEST")
  5. GET DAY BOOK and search the response for our narrations
  6. Print pass/fail per step.

Falls back to logging instructive errors (and which step failed) so we can
escalate to UI automation if XML company creation is rejected.

Usage:
    .venv/bin/python -m tmv_recon.tally.round_trip
"""
from __future__ import annotations
import sys
import time
from datetime import date
from xml.etree import ElementTree as ET

from tmv_recon.config import TALLY_HOST, TALLY_PORT
from tmv_recon.tally.http import post_xml

COMPANY = "TMV Recon Test"
INV_NO  = "25-26/T1"
INV_DATE = "20260428"
GUEST   = "TEST GUEST"
SALES_AMT_NET   = 5000.00
SALES_AMT_CGST  = 300.00     # 6%
SALES_AMT_SGST  = 300.00     # 6%
SALES_AMT_GROSS = 5600.00


def _envelope(header_id: str, body_payload: str, request: str = "Import",
              type_: str = "Data", desc: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"<ENVELOPE>\n"
        f"  <HEADER>\n"
        f"    <VERSION>1</VERSION>\n"
        f"    <TALLYREQUEST>{request}</TALLYREQUEST>\n"
        f"    <TYPE>{type_}</TYPE>\n"
        f"    <ID>{header_id}</ID>\n"
        f"  </HEADER>\n"
        f"  <BODY>\n"
        f"    <DESC>{desc}</DESC>\n"
        f"    <DATA>\n"
        f"{body_payload}"
        f"    </DATA>\n"
        f"  </BODY>\n"
        f"</ENVELOPE>\n"
    )


def _status(resp_xml: str) -> tuple[int, str]:
    """Parse <STATUS> and any <LINEERROR> from Tally response."""
    try:
        root = ET.fromstring(resp_xml)
        status = root.findtext("HEADER/STATUS") or "?"
        err = root.findtext("BODY/DATA/LINEERROR") or root.findtext(".//LINEERROR") or ""
        return int(status) if status.lstrip("-").isdigit() else 0, err
    except ET.ParseError as e:
        return -2, f"parse error: {e}"


def step(name: str):
    print(f"\n── {name}")


def run() -> int:
    failures = 0

    # ── 1. Create company ───────────────────────────────────────────────
    step("1. Create company")
    body = (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        f'        <COMPANY NAME="{COMPANY}" ACTION="Create">\n'
        f"          <NAME>{COMPANY}</NAME>\n"
        f"          <STARTINGFROM>20250401</STARTINGFROM>\n"
        f"          <BOOKSFROM>20250401</BOOKSFROM>\n"
        f"          <ENDINGFROM>20260331</ENDINGFROM>\n"
        f"          <BASECURRENCYSYMBOL>Rs.</BASECURRENCYSYMBOL>\n"
        f"          <FORMALNAME>Indian Rupees</FORMALNAME>\n"
        f"          <COUNTRYNAME>India</COUNTRYNAME>\n"
        f"          <STATENAME>Rajasthan</STATENAME>\n"
        "        </COMPANY>\n"
        "      </TALLYMESSAGE>\n"
    )
    xml = _envelope("All Masters", body)
    try:
        resp = post_xml(xml, host=TALLY_HOST, port=TALLY_PORT, timeout=30)
        s, err = _status(resp)
        print(f"   STATUS={s}  err={err!r}")
        if s != 1:
            print("   ⚠ XML company creation rejected. Fallback path:")
            print("     RDP and create a company manually (F3 → Create Company), then re-run.")
            print("   Continuing with rest of round-trip — assumes a company is already loaded.")
    except Exception as e:
        print(f"   POST failed: {e}")
        failures += 1

    time.sleep(2)

    # ── 2. Create masters (groups already in chart-of-accounts; just ledgers) ──
    step("2. Create master ledgers")
    sv = (f"<STATICVARIABLES>"
          f"<IMPORTDUPS>@@DUPCOMBINE</IMPORTDUPS>"
          f"<SVCURRENTCOMPANY>{COMPANY}</SVCURRENTCOMPANY>"
          f"</STATICVARIABLES>")

    LEDGERS = [
        ("Sundry Debtors_Test",       "Sundry Debtors"),
        ("SALE ACCOMODATION GST 12%", "Sales Accounts"),
        ("CGST",                      "Duties & Taxes"),
        ("SGST",                      "Duties & Taxes"),
        ("CARD UPI PAYTM",            "Bank Accounts"),
    ]
    bodies = []
    for name, parent in LEDGERS:
        bodies.append(
            '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
            f'        <LEDGER NAME="{name}" ACTION="Create">\n'
            f"          <NAME>{name}</NAME>\n"
            f"          <PARENT>{parent}</PARENT>\n"
            "        </LEDGER>\n"
            "      </TALLYMESSAGE>\n"
        )
    xml = _envelope("All Masters", "".join(bodies), desc=sv)
    try:
        resp = post_xml(xml, host=TALLY_HOST, port=TALLY_PORT, timeout=30)
        s, err = _status(resp)
        # IMPORTRESULT counters
        try:
            r = ET.fromstring(resp)
            created = r.findtext(".//CREATED") or "?"
            altered = r.findtext(".//ALTERED") or "?"
            ignored = r.findtext(".//IGNORED") or "?"
            errors  = r.findtext(".//ERRORS") or "?"
            print(f"   STATUS={s}  CREATED={created} ALTERED={altered} IGNORED={ignored} ERRORS={errors}  err={err!r}")
        except ET.ParseError:
            print(f"   STATUS={s}  err={err!r}  raw_excerpt={resp[:200]!r}")
        if s != 1:
            failures += 1
    except Exception as e:
        print(f"   POST failed: {e}")
        failures += 1

    time.sleep(1)

    # ── 3. Post sample Sales voucher ─────────────────────────────────────
    step("3. Post Sales voucher")
    sales_narration = f"INVOICE NO -{INV_NO} {GUEST}"
    sales_body = (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        '        <VOUCHER VCHTYPE="Sales" ACTION="Create">\n'
        f"          <DATE>{INV_DATE}</DATE>\n"
        "          <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>\n"
        f"          <VOUCHERNUMBER>{INV_NO}</VOUCHERNUMBER>\n"
        f"          <NARRATION>{sales_narration}</NARRATION>\n"
        f"          <PARTYLEDGERNAME>Sundry Debtors_Test</PARTYLEDGERNAME>\n"
        # Dr Party
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>Sundry Debtors_Test</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        "            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        f"            <AMOUNT>-{SALES_AMT_GROSS:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        # Cr Sales
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>SALE ACCOMODATION GST 12%</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        f"            <AMOUNT>{SALES_AMT_NET:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        # Cr CGST
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>CGST</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        f"            <AMOUNT>{SALES_AMT_CGST:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        # Cr SGST
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>SGST</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        f"            <AMOUNT>{SALES_AMT_SGST:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        "        </VOUCHER>\n"
        "      </TALLYMESSAGE>\n"
    )
    xml = _envelope("Vouchers", sales_body, desc=sv)
    try:
        resp = post_xml(xml, host=TALLY_HOST, port=TALLY_PORT, timeout=30)
        s, err = _status(resp)
        try:
            r = ET.fromstring(resp)
            created = r.findtext(".//CREATED") or "?"
            errors  = r.findtext(".//ERRORS") or "?"
            print(f"   STATUS={s}  CREATED={created} ERRORS={errors}  err={err!r}")
        except ET.ParseError:
            print(f"   STATUS={s}  err={err!r}  raw_excerpt={resp[:200]!r}")
        if s != 1: failures += 1
    except Exception as e:
        print(f"   POST failed: {e}")
        failures += 1

    time.sleep(1)

    # ── 4. Post sample Journal voucher (payment) ─────────────────────────
    step("4. Post Journal voucher")
    journal_narration = f"BEING PAID THROUGH UPI AGAINST INVOICE NO:{INV_NO} {GUEST}"
    journal_body = (
        '      <TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
        '        <VOUCHER VCHTYPE="Journal" ACTION="Create">\n'
        f"          <DATE>{INV_DATE}</DATE>\n"
        "          <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>\n"
        f"          <VOUCHERNUMBER>{INV_NO}</VOUCHERNUMBER>\n"
        f"          <NARRATION>{journal_narration}</NARRATION>\n"
        # Dr Bank
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>CARD UPI PAYTM</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n"
        f"            <AMOUNT>-{SALES_AMT_GROSS:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        # Cr Sundry Debtors
        "          <ALLLEDGERENTRIES.LIST>\n"
        "            <LEDGERNAME>Sundry Debtors_Test</LEDGERNAME>\n"
        "            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n"
        "            <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\n"
        f"            <AMOUNT>{SALES_AMT_GROSS:.2f}</AMOUNT>\n"
        "          </ALLLEDGERENTRIES.LIST>\n"
        "        </VOUCHER>\n"
        "      </TALLYMESSAGE>\n"
    )
    xml = _envelope("Vouchers", journal_body, desc=sv)
    try:
        resp = post_xml(xml, host=TALLY_HOST, port=TALLY_PORT, timeout=30)
        s, err = _status(resp)
        try:
            r = ET.fromstring(resp)
            created = r.findtext(".//CREATED") or "?"
            errors  = r.findtext(".//ERRORS") or "?"
            print(f"   STATUS={s}  CREATED={created} ERRORS={errors}  err={err!r}")
        except ET.ParseError:
            print(f"   STATUS={s}  err={err!r}  raw_excerpt={resp[:200]!r}")
        if s != 1: failures += 1
    except Exception as e:
        print(f"   POST failed: {e}")
        failures += 1

    time.sleep(1)

    # ── 5. Pull Day Book and search for our narrations ──────────────────
    step("5. Pull Day Book")
    daybook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<ENVELOPE>\n"
        "  <HEADER>\n"
        "    <VERSION>1</VERSION>\n"
        "    <TALLYREQUEST>Export</TALLYREQUEST>\n"
        "    <TYPE>Data</TYPE>\n"
        "    <ID>Day Book</ID>\n"
        "  </HEADER>\n"
        "  <BODY>\n"
        "    <DESC>\n"
        "      <STATICVARIABLES>\n"
        "        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>\n"
        f"        <SVCURRENTCOMPANY>{COMPANY}</SVCURRENTCOMPANY>\n"
        "        <SVFROMDATE>20250401</SVFROMDATE>\n"
        "        <SVTODATE>20260331</SVTODATE>\n"
        "      </STATICVARIABLES>\n"
        "    </DESC>\n"
        "  </BODY>\n"
        "</ENVELOPE>\n"
    )
    try:
        resp = post_xml(daybook_xml, host=TALLY_HOST, port=TALLY_PORT, timeout=60)
        ok_sales = sales_narration in resp
        ok_journal = journal_narration in resp
        print(f"   response size: {len(resp)} bytes")
        print(f"   sales narration found:    {'✓' if ok_sales else '✗'}  {sales_narration!r}")
        print(f"   journal narration found:  {'✓' if ok_journal else '✗'}  {journal_narration!r}")
        if not (ok_sales and ok_journal):
            failures += 1
            # Show a snippet so we can diagnose
            print(f"   first 600 chars of Day Book response:")
            print("   " + resp[:600].replace("\n", "\n   "))
    except Exception as e:
        print(f"   POST failed: {e}")
        failures += 1

    print(f"\n{'='*50}")
    if failures == 0:
        print(f"✓ ROUND-TRIP OK — Tally narrations come back exactly as posted")
    else:
        print(f"✗ {failures} step(s) failed")
    return failures


if __name__ == "__main__":
    sys.exit(run())
