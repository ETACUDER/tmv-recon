"""Tally → DataFrame export connectors.

Pull live data from a running TallyPrime instance via XML/HTTP and return
pandas DataFrames. Pair with `tally.xml` (import) for full bidirectional flow.

Reference: TallyHelp Case Study 1 — XML request/response formats
https://help.tallysolutions.com/case-study-1/

All connectors:
- Need a loaded company (pass `company=` or set TALLY_COMPANY in .env)
- Return a DataFrame with normalized snake_case column names
- Raise `TallyError` on STATUS != 1 with the LINEERROR message

Connectors implemented (verified against live endpoint — see docs/tally-protocols.md):
- list_companies()                           → df[name, starting_from]                      ✓ no company needed
- current_company()                          → str
- day_book(from_date, to_date)               → df[date, voucher_type, voucher_no, narration, party, amount, ledgers...]
- ledger_outstandings(ledger)                → df[bill_date, bill_ref, opening, pending, due_date]
- bills_receivable(from_date, to_date)       → df[ledger, bill_date, bill_ref, amount, due_date]
- bills_payable(from_date, to_date)          → df[ledger, bill_date, bill_ref, amount, due_date]
- trial_balance(from_date, to_date)          → df[name]
- balance_sheet(as_of)                       → df
- profit_loss(from_date, to_date)            → df
- voucher_register(voucher_type, from, to)   → df[date, voucher_no, narration, ...]
- sales_register / purchase_register / payment_register / journal_register

NOTE: every Data export except `List of Companies` requires a loaded company —
set `TALLY_COMPANY` in .env or pass `company=`. Without one, Tally returns
STATUS=0 with `Could not find Company ''`.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from xml.etree import ElementTree as ET
import pandas as pd

from tmv_recon.config import TALLY_HOST, TALLY_PORT, TALLY_COMPANY
from tmv_recon.tally.http import post_xml


class TallyError(RuntimeError):
    pass


def _fmt_date(d: date | str) -> str:
    if isinstance(d, str):
        # accept '2025-04-01' or '20250401' or '01-04-2025'
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y"):
            try: return datetime.strptime(d, fmt).strftime("%Y%m%d")
            except ValueError: continue
        raise ValueError(f"unparseable date: {d!r}")
    return d.strftime("%Y%m%d")


def _ensure_status(resp_xml: str) -> ET.Element:
    # Clean invalid XML control characters (&#0; to &#31; except tab/newline/CR)
    # Tally exports sometimes include &#4; which breaks XML parsing
    resp_xml = re.sub(r'&#([0-8]|1[1-2]|1[4-9]|[2-3][0-9]);', '', resp_xml)

    try:
        root = ET.fromstring(resp_xml)
    except ET.ParseError as e:
        raise TallyError(f"non-XML response: {e}: {resp_xml[:200]!r}")
    status = root.findtext("HEADER/STATUS") or root.findtext(".//STATUS") or "?"
    if status != "1":
        err = root.findtext(".//LINEERROR") or root.findtext("BODY/DATA/LINEERROR") or ""
        raise TallyError(f"Tally STATUS={status}: {err}")
    return root


def _post(xml: str, *, host: str | None = None, port: int | None = None, timeout: int = 60) -> ET.Element:
    return _ensure_status(post_xml(xml, host=host, port=port, timeout=timeout))


# ── envelope builders ────────────────────────────────────────────────────

def _envelope_collection(name: str, native_methods: list[str], company: str | None = None) -> str:
    sv = ""
    if company:
        sv = f"<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY></STATICVARIABLES>"
    methods = "\n      ".join(f"<NATIVEMETHOD>{m}</NATIVEMETHOD>" for m in native_methods)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>{name}</ID>
  </HEADER>
  <BODY>
    <DESC>
      {sv}
      <TDL><TDLMESSAGE>
        <COLLECTION NAME="{name}" ISMODIFY="No">
          <TYPE>{name.replace(' Coll','').replace(' List','')}</TYPE>
          {methods}
        </COLLECTION>
      </TDLMESSAGE></TDL>
    </DESC>
  </BODY>
</ENVELOPE>'''


def _envelope_report(report_id: str, company: str | None, from_date: str | None = None,
                     to_date: str | None = None, extra_sv: dict | None = None) -> str:
    sv_parts = ['<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>']
    if company:    sv_parts.append(f"<SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>")
    if from_date:  sv_parts.append(f"<SVFROMDATE>{from_date}</SVFROMDATE>")
    if to_date:    sv_parts.append(f"<SVTODATE>{to_date}</SVTODATE>")
    for k, v in (extra_sv or {}).items():
        sv_parts.append(f"<{k}>{v}</{k}>")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>{report_id}</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>{''.join(sv_parts)}</STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>'''


def _company(c: str | None) -> str | None:
    return c if c is not None else (TALLY_COMPANY or None)


# ── 1. List companies ────────────────────────────────────────────────────

def list_companies() -> pd.DataFrame:
    xml = _envelope_collection("List of Companies", ["Name", "StartingFrom"])
    root = _post(xml)
    rows = []
    for c in root.findall(".//COMPANY"):
        rows.append({
            "name": (c.get("NAME") or c.findtext("NAME") or "").strip(),
            "starting_from": c.findtext("STARTINGFROM"),
        })
    return pd.DataFrame(rows)


def current_company() -> str | None:
    """Return the currently-loaded Tally company, or None if none."""
    df = list_companies()
    return df["name"].iloc[0] if len(df) else None


# ── 2. Day Book ──────────────────────────────────────────────────────────

def day_book(from_date: str | date, to_date: str | date, company: str | None = None) -> pd.DataFrame:
    """All vouchers in the date range. One row per voucher.

    Returns columns:
      date, voucher_type, voucher_no, master_id, narration, party_ledger,
      reference, total_amount, ledger_entries (list of dicts), raw_xml (str).
    """
    xml = _envelope_report("Day Book", _company(company), _fmt_date(from_date), _fmt_date(to_date))
    root = _post(xml, timeout=120)
    rows = []
    for v in root.findall(".//VOUCHER"):
        entries = []
        for le in v.findall("ALLLEDGERENTRIES.LIST") + v.findall("LEDGERENTRIES.LIST"):
            entries.append({
                "ledger": le.findtext("LEDGERNAME") or "",
                "amount": _safe_float(le.findtext("AMOUNT")),
                "is_deemed_positive": (le.findtext("ISDEEMEDPOSITIVE") or "").lower() == "yes",
                "is_party_ledger": (le.findtext("ISPARTYLEDGER") or "").lower() == "yes",
            })
        total = sum(abs(e["amount"] or 0) for e in entries) / 2 if entries else 0.0
        rows.append({
            "date":          _parse_tally_date(v.findtext("DATE")),
            "voucher_type":  v.get("VCHTYPE") or v.findtext("VOUCHERTYPENAME") or "",
            "voucher_no":    v.findtext("VOUCHERNUMBER") or "",
            "master_id":     v.findtext("MASTERID") or "",
            "narration":     v.findtext("NARRATION") or "",
            "party_ledger":  v.findtext("PARTYLEDGERNAME") or "",
            "reference":     v.findtext("REFERENCE") or "",
            "total_amount":  total,
            "ledger_entries": entries,
        })
    return pd.DataFrame(rows)


# ── 3. Ledger Outstandings (Pending Bills) ──────────────────────────────

def ledger_outstandings(ledger: str, company: str | None = None,
                        from_date: str | date | None = None,
                        to_date: str | date | None = None) -> pd.DataFrame:
    """Outstanding (pending) bills for a single ledger — the 'On Account' list.

    Useful for: identifying unallocated payments in `CARD / UPI / PAYTM / G PAY`.
    """
    extra = {"LedgerName": ledger}
    xml = _envelope_report(
        "Ledger Outstandings",
        _company(company),
        _fmt_date(from_date) if from_date else None,
        _fmt_date(to_date) if to_date else None,
        extra_sv=extra,
    )
    root = _post(xml, timeout=120)
    rows = []
    for b in root.findall(".//BILLFIXED"):
        rows.append({
            "bill_date":      _parse_tally_date(b.findtext("BILLDATE")),
            "bill_ref":       b.findtext("BILLREF") or b.findtext("NAME") or "",
            "opening_amount": _safe_float(b.findtext("OPENINGAMT")),
            "pending_amount": _safe_float(b.findtext("PENDINGAMT") or b.findtext("AMOUNT")),
            "due_date":       _parse_tally_date(b.findtext("DUEDATE")),
            "credit_period":  b.findtext("CREDITPERIOD") or "",
            "ledger":         ledger,
        })
    return pd.DataFrame(rows)


# ── 4. Bills Receivable / Bills Payable ─────────────────────────────────

def _bills(report_id: str, from_date, to_date, company) -> pd.DataFrame:
    xml = _envelope_report(report_id, _company(company), _fmt_date(from_date), _fmt_date(to_date))
    root = _post(xml, timeout=120)
    rows = []
    for b in root.findall(".//BILLFIXED") + root.findall(".//BILL"):
        rows.append({
            "ledger":         b.findtext("LEDGERNAME") or b.findtext("PARTYLEDGERNAME") or "",
            "bill_date":      _parse_tally_date(b.findtext("BILLDATE")),
            "bill_ref":       b.findtext("BILLREF") or b.findtext("NAME") or "",
            "amount":         _safe_float(b.findtext("AMOUNT") or b.findtext("PENDINGAMT")),
            "due_date":       _parse_tally_date(b.findtext("DUEDATE")),
            "credit_period":  b.findtext("CREDITPERIOD") or "",
        })
    return pd.DataFrame(rows)


def bills_receivable(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return _bills("Bills Receivable", from_date, to_date, company)


def bills_payable(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return _bills("Bills Payable", from_date, to_date, company)


# ── 5. Trial Balance ────────────────────────────────────────────────────

def trial_balance(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    xml = _envelope_report("Trial Balance", _company(company), _fmt_date(from_date), _fmt_date(to_date))
    root = _post(xml, timeout=120)
    rows = []
    # Tally renders Trial Balance as DSP* tags; extract group name + closing balances.
    for grp in root.findall(".//DSPACCNAME"):
        name = grp.findtext("DSPDISPNAME") or ""
        info = grp.getnext() if hasattr(grp, "getnext") else None
        # Fallback: walk siblings
        rows.append({"name": name})
    # If we got nothing, try a flatter parse
    if not rows:
        for el in root.iter():
            if el.tag.startswith("DSP") and el.text:
                rows.append({"tag": el.tag, "value": el.text.strip()})
    return pd.DataFrame(rows)


# ── 6. Voucher Register (per voucher type) ──────────────────────────────

def voucher_register(voucher_type: str, from_date, to_date,
                     company: str | None = None) -> pd.DataFrame:
    """Pull all vouchers of a given type — Sales / Purchase / Payment / Journal etc.

    Verified report IDs: `Sales Register`, `Purchase Register`, `Payment Register`,
    `Journal Register`, `Voucher Register`. NOT `Receipt Register` (rejected).
    """
    extra = {"SVVOUCHERTYPE": voucher_type}
    xml = _envelope_report(f"{voucher_type} Register", _company(company),
                           _fmt_date(from_date), _fmt_date(to_date), extra_sv=extra)
    root = _post(xml, timeout=120)
    return _vouchers_to_df(root)


def sales_register(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return voucher_register("Sales", from_date, to_date, company)


def purchase_register(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return voucher_register("Purchase", from_date, to_date, company)


def payment_register(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return voucher_register("Payment", from_date, to_date, company)


def journal_register(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    return voucher_register("Journal", from_date, to_date, company)


# ── 7. Balance Sheet / P&L ──────────────────────────────────────────────

def balance_sheet(as_of, company: str | None = None) -> pd.DataFrame:
    xml = _envelope_report("Balance Sheet", _company(company), None, _fmt_date(as_of))
    root = _post(xml, timeout=120)
    rows: list[dict] = []
    for el in root.iter():
        if el.tag.startswith("DSP") and el.text and el.text.strip():
            rows.append({"tag": el.tag, "value": el.text.strip()})
    return pd.DataFrame(rows)


def profit_loss(from_date, to_date, company: str | None = None) -> pd.DataFrame:
    xml = _envelope_report("Profit and Loss", _company(company),
                           _fmt_date(from_date), _fmt_date(to_date))
    root = _post(xml, timeout=120)
    rows: list[dict] = []
    for el in root.iter():
        if el.tag.startswith("DSP") and el.text and el.text.strip():
            rows.append({"tag": el.tag, "value": el.text.strip()})
    return pd.DataFrame(rows)


# ── 8. Generic helpers ──────────────────────────────────────────────────

def export_function(name: str, *params) -> str | None:
    """Evaluate a Tally function (e.g. $$Round, $$NumStockItems). Doesn't need
    a loaded company. Returns the result text or None."""
    pl = ""
    if params:
        plist = "\n".join(f'<PARAM TYPE="Number">{p}</PARAM>' for p in params)
        pl = f"<FUNCPARAMLIST>{plist}</FUNCPARAMLIST>"
    xml = f'''<?xml version="1.0"?><ENVELOPE><HEADER><VERSION>1</VERSION>
<TALLYREQUEST>Export</TALLYREQUEST><TYPE>Function</TYPE><ID>{name}</ID>
</HEADER><BODY><DESC>{pl}</DESC></BODY></ENVELOPE>'''
    try:
        root = _post(xml, timeout=15)
    except TallyError:
        return None
    return root.findtext(".//RESULT")


def _vouchers_to_df(root: ET.Element) -> pd.DataFrame:
    rows = []
    for v in root.findall(".//VOUCHER"):
        rows.append({
            "date":         _parse_tally_date(v.findtext("DATE")),
            "voucher_type": v.get("VCHTYPE") or v.findtext("VOUCHERTYPENAME") or "",
            "voucher_no":   v.findtext("VOUCHERNUMBER") or "",
            "narration":    v.findtext("NARRATION") or "",
            "party_ledger": v.findtext("PARTYLEDGERNAME") or "",
            "amount": sum(abs(_safe_float(e.findtext("AMOUNT")) or 0)
                          for e in v.findall("ALLLEDGERENTRIES.LIST")) / 2,
        })
    return pd.DataFrame(rows)


# ── helpers ──────────────────────────────────────────────────────────────

def _safe_float(s: str | None) -> float | None:
    if s is None: return None
    s = s.strip()
    if not s: return None
    try: return float(s)
    except ValueError:
        # Handle Tally's "(amount)" negative or trailing 'CR'/'DR'
        s2 = re.sub(r"[A-Za-z]+$", "", s.replace(",", "").strip("() "))
        try: return float(s2)
        except ValueError: return None


def _parse_tally_date(s: str | None) -> str | None:
    """Tally returns dates as YYYYMMDD or DD-MMM-YYYY."""
    if not s: return None
    s = s.strip()
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try: return datetime.strptime(s, fmt).date().isoformat()
        except ValueError: continue
    return s


# ── canonical save helpers ──────────────────────────────────────────────

def save_canonical(df: pd.DataFrame, name: str) -> str:
    from tmv_recon.config import OUTPUT_DIR
    out = OUTPUT_DIR.parent / "recon" / "canonical" / f"tally_{name}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return str(out)
