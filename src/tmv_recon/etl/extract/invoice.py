"""Extract EZ sheet → canonical_invoice.csv (one row per Invoice #).

Per discovery (_discovery_invoices.md):
- 1399 rows of line-items; 304 invoices, 393 folios, 1:1 folio↔invoice
- Net + CGST + SGST = Gross verified per invoice
- GST 12% (CGST 6 + SGST 6) on accommodation; some 18% on extra-person
- Tax Name has 3 spellings — normalize
- 198 rows have no Invoice # (cancellations) — exclude
- Settlement Amount on payment lines is negative

Outputs `data/recon/canonical/invoice.csv`.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

from tmv_recon.config import ROOT
from ._common import normalize_invoice_no, write_canonical

EZ_PATH = ROOT / "data" / "invoices" / "raw" / "transaction_detail20250428.xlsx"


def _norm_tax_name(s):
    if not isinstance(s, str): return s
    t = s.upper().replace(" ", "")
    if "CGST" in t: return "CGST"
    if "SGST" in t: return "SGST"
    if "IGST" in t: return "IGST"
    return s


def _stringy(v) -> str:
    """Convert a numeric-looking value to its int-string when possible, else str().
    Handles `6803.0` → `"6803"`, `6803-1` → `"6803-1"`, NaN → `""`."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)
    s = str(v).strip()
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def _safe_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try: return pd.to_datetime(v, errors="coerce").date().isoformat()
    except Exception: return None


def run() -> pd.DataFrame:
    if not EZ_PATH.exists():
        raise FileNotFoundError(f"missing {EZ_PATH}")
    df = pd.read_excel(EZ_PATH, sheet_name=0)
    print(f"  read {len(df)} rows × {len(df.columns)} cols")

    # Filter: keep only rows with an Invoice #
    df = df[df["Invoice #"].notna()].copy()
    df["invoice_no"] = df["Invoice #"].astype(str).map(normalize_invoice_no)
    df = df[df["invoice_no"].notna()].copy()
    print(f"  after Invoice # filter: {len(df)} rows, {df['invoice_no'].nunique()} unique invoices")

    # Normalize tax name (CGST 6% / CGST @ 9% → CGST)
    if "Tax Name" in df.columns:
        df["Tax Name"] = df["Tax Name"].map(_norm_tax_name)
    if "Tax Name.1" in df.columns:
        df["Tax Name.1"] = df["Tax Name.1"].map(_norm_tax_name)

    # Group by invoice_no
    grouped = df.groupby("invoice_no", sort=False)

    rows: list[dict] = []
    for inv, g in grouped:
        head = g.iloc[0]

        # Sums across all line items in this invoice
        net = pd.to_numeric(g["Net Amount"], errors="coerce").sum()
        cgst = sgst = 0.0
        if "Tax Name" in g.columns:
            cgst += pd.to_numeric(g.loc[g["Tax Name"] == "CGST", "Tax Amount"], errors="coerce").sum()
            sgst += pd.to_numeric(g.loc[g["Tax Name"] == "SGST", "Tax Amount"], errors="coerce").sum()
        if "Tax Name.1" in g.columns:
            cgst += pd.to_numeric(g.loc[g["Tax Name.1"] == "CGST", "Tax Amount.1"], errors="coerce").sum()
            sgst += pd.to_numeric(g.loc[g["Tax Name.1"] == "SGST", "Tax Amount.1"], errors="coerce").sum()
        gross = pd.to_numeric(g["Gross Amount"], errors="coerce").sum()
        gst_rate = ((cgst + sgst) / net * 100) if net else None

        # Settlement: sum of NEGATIVE Settlement Amount values (payments) → positive
        settlement = -pd.to_numeric(g["Settlement Amount"], errors="coerce").fillna(0)
        settlement_paid = float(settlement[settlement > 0].sum())
        # Settlement modes: distinct non-null Settlement/Particular values
        modes = []
        if "Settlement/Particular" in g.columns:
            modes = sorted({str(x) for x in g["Settlement/Particular"].dropna() if str(x).strip()})

        # Folio numbers in this invoice (usually 1)
        folios = sorted({_stringy(f) for f in g["Folio #"].dropna()})

        # Use earliest non-null date as invoice date if Invoice date missing
        inv_date = _safe_date(head.get("Invoice date")) or _safe_date(g["Transaction Date"].dropna().min())
        arrival = _safe_date(head.get("Arrival"))
        # Departure column is named "Dept."
        dept = _safe_date(head.get("Dept."))

        rows.append({
            "invoice_no":         inv,
            "invoice_date":       inv_date,
            "folio_nos":          ",".join(folios),
            "reservation_no":     _stringy(head.get("Reservation #")),
            "guest_name":         str(head.get("Guest Name") or "").strip(),
            "bill_to_name":       str(head.get("Bill To Name") or "").strip(),
            "travel_agent":       str(head.get("Travel Agent") or "").strip(),
            "business_source":    str(head.get("Business Source") or "").strip(),
            "travel_agent_voucher": str(head.get("Travel Agent Voucher #") or "").strip(),
            "company_gstin":      str(head.get("RegNo.") or "").strip(),
            "transaction_type":   str(head.get("Transaction") or "").strip(),
            "arrival":            arrival,
            "departure":          dept,
            "room_type":          str(head.get("Room Type") or "").strip(),
            "rate_type":          str(head.get("Rate Type") or "").strip(),
            "room_no":            _stringy(head.get("Room #")),
            "net_amount":         round(float(net), 2),
            "cgst":               round(float(cgst), 2),
            "sgst":               round(float(sgst), 2),
            "gst_rate":           round(float(gst_rate), 2) if gst_rate is not None else None,
            "gross_amount":       round(float(gross), 2),
            "settlement_amount":  round(settlement_paid, 2),
            "settlement_modes":   ",".join(modes),
            "folio_status":       str(head.get("Folio Status") or "").strip(),
            "raw_path":           str(EZ_PATH.relative_to(ROOT)),
        })

    out = pd.DataFrame(rows)
    return out


def main() -> int:
    out = run()
    if out.empty:
        return 1
    csv = write_canonical(out, "invoice")
    print(f"\nwrote {csv} — {len(out)} invoices")
    # Sanity check
    delta = (out["net_amount"] + out["cgst"] + out["sgst"] - out["gross_amount"]).abs()
    print(f"  Net + CGST + SGST = Gross: {(delta < 0.01).sum()}/{len(out)} invoices reconciled")
    print(f"  GST rate distribution:")
    for rate, n in out["gst_rate"].value_counts().head(5).items():
        print(f"    {rate}%: {n}")
    print(f"  by travel_agent (top 5):")
    for ta, n in out["travel_agent"].fillna("(none)").value_counts().head(5).items():
        print(f"    {ta or '(direct)'}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
