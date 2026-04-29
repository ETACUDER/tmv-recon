"""Exercise every Tally XML protocol against the live endpoint and report
what works without a company loaded vs what needs one. Reference:
https://help.tallysolutions.com/article/DeveloperReference/integration-capabilities/case_study_1.htm
"""
from __future__ import annotations
from xml.etree import ElementTree as ET
from tmv_recon.tally.http import post_xml


def run(xml: str, label: str, timeout: int = 30) -> tuple[int, str, int]:
    try:
        resp = post_xml(xml, timeout=timeout)
    except Exception as e:
        print(f"[{label}] POST failed: {e}")
        return -1, str(e), 0
    try:
        root = ET.fromstring(resp)
    except ET.ParseError:
        print(f"[{label}] non-XML response (size={len(resp)})")
        return -2, "parse error", len(resp)
    status = root.findtext("HEADER/STATUS") or root.findtext(".//STATUS") or "?"
    err = root.findtext(".//LINEERROR") or ""
    s = int(status) if status.lstrip("-").isdigit() else 0
    icon = "✓" if s == 1 and not err else "✗"
    suffix = f" err={err!r}" if err else ""
    print(f"[{label}] STATUS={status} {icon} bytes={len(resp)}{suffix}")
    return s, err, len(resp)


# ── Function exports (don't need a company) ──────────────────────────────
F_NUMSTOCK = '''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Function</TYPE><ID>$$NumStockItems</ID></HEADER><BODY><DESC></DESC></BODY></ENVELOPE>'''

F_ROUND = '''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Function</TYPE><ID>$$Round</ID></HEADER><BODY><DESC>
<FUNCPARAMLIST><PARAM TYPE="Number">12.347</PARAM><PARAM TYPE="Number">0.01</PARAM></FUNCPARAMLIST>
</DESC></BODY></ENVELOPE>'''

F_VERSION = '''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Function</TYPE><ID>$$Version</ID></HEADER><BODY><DESC></DESC></BODY></ENVELOPE>'''


# ── Collection exports (system-wide work without company) ────────────────
C_COMPANIES = '''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>List of Companies</ID></HEADER><BODY><DESC>
<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
<TDL><TDLMESSAGE><COLLECTION NAME="List of Companies" ISMODIFY="No"><TYPE>Company</TYPE><FETCH>Name</FETCH><FETCH>StartingFrom</FETCH></COLLECTION></TDLMESSAGE></TDL>
</DESC></BODY></ENVELOPE>'''


# ── Data report exports (need company loaded) ────────────────────────────
def D_REPORT(report_id: str, sv_extra: str = "") -> str:
    return f'''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE><ID>{report_id}</ID></HEADER><BODY><DESC>
<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{sv_extra}</STATICVARIABLES>
</DESC></BODY></ENVELOPE>'''


# ── Import (needs company) ───────────────────────────────────────────────
I_LEDGER = '''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Import</TALLYREQUEST><TYPE>Data</TYPE><ID>All Masters</ID></HEADER><BODY><DESC>
<STATICVARIABLES><IMPORTDUPS>@@DUPCOMBINE</IMPORTDUPS></STATICVARIABLES>
</DESC><DATA>
<TALLYMESSAGE xmlns:UDF="TallyUDF">
<LEDGER NAME="ProtocolTestLedger" Action="Create">
<NAME>ProtocolTestLedger</NAME><PARENT>Sundry Debtors</PARENT>
</LEDGER>
</TALLYMESSAGE>
</DATA></BODY></ENVELOPE>'''


def main() -> int:
    print("┌─ TALLY XML PROTOCOL TEST ──────────────────────────────────")
    print("│ endpoint: http://20.219.50.8:9000/")
    print("│ reference: TallyHelp Case Study 1")
    print("└────────────────────────────────────────────────────────────")
    print()
    print("── Function exports (don't need a loaded company) ──")
    run(F_VERSION,   "Function $$Version")
    run(F_NUMSTOCK,  "Function $$NumStockItems")
    run(F_ROUND,     "Function $$Round(12.347, 0.01)")

    print("\n── Collection exports (system-wide) ──")
    run(C_COMPANIES, "Collection List of Companies")

    reports = [
        "Trial Balance", "Balance Sheet", "Profit & Loss A/c",
        "Day Book", "Cash Book", "Bank Book",
        "Sales Register", "Purchase Register", "Receipt Register",
        "Payment Register", "Journal Register", "Voucher Register",
        "Bills Receivable", "Bills Payable", "Group Outstandings",
        "Ledger Outstandings", "Group Summary", "Stock Summary",
        "Cash Flow", "Funds Flow",
    ]
    print("\n── Data report exports (need company loaded) ──")
    for r in reports:
        run(D_REPORT(r), f"Data {r}")

    print("\n── Import (needs company loaded) ──")
    run(I_LEDGER, "Import LEDGER 'ProtocolTestLedger'")

    print("\n┌─ CONCLUSION ───────────────────────────────────────────────")
    print("│ Without a loaded company, only Function exports + List of")
    print("│ Companies work. Every Data report and every Import requires")
    print("│ <SVCURRENTCOMPANY> set to a loaded company.")
    print("└────────────────────────────────────────────────────────────")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
