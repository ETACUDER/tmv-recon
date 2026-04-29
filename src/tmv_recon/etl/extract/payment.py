"""Extract payment streams → canonical_payment.csv + canonical_bank_txn.csv.

Sources:
- PTM raw 123-col Paytm dumps (data/payments/raw/PTM*.xlsx) — primary
- Indian Bank statements (data/payments/processed/*Statement Of Account*) — bank-side
- UPI historical 8-col simplified format (meet-recording/data_sheets_historical/...)

Per discovery (_discovery_payments.md, Section 4.3 Requirements):
- PTM IDs are Excel-quoted (leading ') — strip on read
- Settled = Amount - Commission - GST exact; GST = 18% × Commission
- Bank statements: header at row 21-22, account in metadata block, Description carries UTR
- Skip processed/ PTM files (lossy 8-col subset)
- UPI files: 93% duplicate UTR rate → aggregate by UTR before join
- UPI null UTR rate: 54% (March 2026) → flag low confidence, use txn_id/order_id fallback

Outputs:
- data/recon/canonical/payment.csv        (PTM transactions - raw)
- data/recon/canonical/upi_payments.csv   (UPI aggregated by UTR)
- data/recon/canonical/bank.csv           (bank statement lines)
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import pandas as pd
from decimal import Decimal

from tmv_recon.config import ROOT
from ._common import strip_excel_quoted, write_canonical

PTM_RAW_DIR = ROOT / "data" / "payments" / "raw"
PROCESSED_DIR = ROOT / "data" / "payments" / "processed"
UPI_HISTORICAL_BASE = ROOT / "meet-recording" / "data_sheets_historical" / "mangal all data sheet"

# Useful PTM cols (subset of 123 — per discovery)
PTM_COLS = [
    "Transaction_ID", "Order_ID", "Transaction_Date", "Updated_Date",
    "Status", "Amount", "Commission", "GST",
    "Payout_ID", "UTR_No.", "Payout_Date", "Settled_Date",
    "Payment_Mode", "Issuing_Bank", "Settled_Amount",
    "Customer_VPA", "RRN", "Card_Scheme",
    "Credit/Debit_Card_Last_4_Digits", "ARN", "UDF2", "MID",
]

# UPI simplified format (8-9 columns)
UPI_COLS = [
    "Transaction_Date", "Updated_Date", "Amount", "Commission", "GST",
    "Settled_Amount", "UTR_No.", "Settled_Date", "Payment_Mode", "Issuing_Bank"
]

UTR_REGEX = re.compile(r"NEFT/[A-Z]+/([A-Z0-9]+)/", re.I)
RRN_FROM_UPI = re.compile(r"BY UPI[^/]*/([0-9]{12})/", re.I)


# ── PTM ──────────────────────────────────────────────────────────────────

def _detect_unit_from_path(p: Path) -> str:
    s = str(p).lower()
    if "rooftop" in s or "jkp" in s:    return "rooftop"
    if "f&b" in s or "fb" in s:          return "f&b"
    return "front_office"


def extract_ptm(path: Path) -> pd.DataFrame:
    """Extract 123-column PTM format."""
    df = pd.read_excel(path, sheet_name=0, dtype=object)
    keep = [c for c in PTM_COLS if c in df.columns]
    df = df[keep].copy()
    # Strip Excel-quoted leading '
    for c in df.columns:
        df[c] = df[c].map(strip_excel_quoted)
    # Coerce numerics
    for c in ("Amount", "Commission", "GST", "Settled_Amount"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # Coerce dates
    for c in ("Transaction_Date", "Updated_Date", "Payout_Date", "Settled_Date"):
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    df["unit"] = _detect_unit_from_path(path)
    df["raw_path"] = str(path.relative_to(ROOT))
    df = df.rename(columns={
        "Transaction_ID": "txn_id",
        "Order_ID": "order_id",
        "Transaction_Date": "txn_dt",
        "Updated_Date": "updated_dt",
        "Status": "status",
        "Amount": "amount_gross",
        "Commission": "commission",
        "GST": "gst",
        "Payout_ID": "payout_id",
        "UTR_No.": "utr",
        "Payout_Date": "payout_dt",
        "Settled_Date": "settled_dt",
        "Payment_Mode": "payment_mode",
        "Issuing_Bank": "issuing_bank",
        "Settled_Amount": "settled_amount",
        "Customer_VPA": "customer_vpa",
        "RRN": "rrn",
        "Card_Scheme": "card_scheme",
        "Credit/Debit_Card_Last_4_Digits": "card_last4",
        "ARN": "arn",
        "UDF2": "pos_guest_name",
        "MID": "merchant_id",
    })
    return df


def extract_upi(path: Path) -> pd.DataFrame:
    """Extract 8-9 column simplified UPI format from historical data.

    Handles 4 column variants:
    - Standard: Transaction_Date (8 cols)
    - Updated: Updated_Date instead of Transaction_Date (8 cols)
    - With Bank: +Issuing_Bank (9 cols)
    - Corrupted: Unnamed columns (skip)
    """
    df = pd.read_excel(path, sheet_name=0, dtype=object)

    # Detect corrupted file (no proper headers)
    if 'Unnamed' in str(df.columns[0]):
        print(f"    WARNING: Corrupted headers in {path.name}, skipping")
        return pd.DataFrame()

    # Normalize column variants
    if 'Updated_Date' in df.columns and 'Transaction_Date' not in df.columns:
        df = df.rename(columns={'Updated_Date': 'Transaction_Date'})

    keep = [c for c in UPI_COLS if c in df.columns]
    df = df[keep].copy()

    # Strip Excel-quoted leading '
    for c in df.columns:
        df[c] = df[c].map(strip_excel_quoted)

    # Remove summary rows (TOTAL, etc.)
    if 'Transaction_Date' in df.columns:
        df = df[~df['Transaction_Date'].astype(str).str.upper().str.contains('TOTAL', na=False)]

    # Coerce numerics
    for c in ("Amount", "Commission", "GST", "Settled_Amount"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Coerce dates
    for c in ("Transaction_Date", "Settled_Date"):
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    # Parse payment mode
    if 'Payment_Mode' in df:
        df['Payment_Mode'] = df['Payment_Mode'].astype(str).str.upper().str.strip()

    # Detect unit from path
    df["unit"] = _detect_unit_from_path(path)
    df["raw_path"] = str(path.relative_to(ROOT) if ROOT in path.parents else path)

    # Normalize column names
    df = df.rename(columns={
        "Transaction_Date": "txn_dt",
        "Amount": "amount_gross",
        "Commission": "commission",
        "GST": "gst",
        "Settled_Amount": "settled_amount",
        "UTR_No.": "utr",
        "Settled_Date": "settled_dt",
        "Payment_Mode": "payment_mode",
        "Issuing_Bank": "issuing_bank",
    })

    return df


def aggregate_by_utr(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate UPI payments by UTR to handle Paytm batch settlements.

    Critical: 93% duplicate UTR rate in raw data.
    Strategy (per Section 4.3):
    - Group by non-null UTR only
    - Sum: transaction_amount, commission, gst, settled_amount
    - Take earliest settled_date per UTR
    - Preserve first payment_mode, unit (should be consistent per UTR)
    - Count transactions per UTR

    Returns:
        DataFrame with one row per unique UTR + separate rows for null UTRs
    """
    if df.empty:
        return df

    # Separate null UTR rows (keep as-is, low confidence)
    null_utr = df[df['utr'].isna() | (df['utr'] == '')].copy()
    null_utr['utr_txn_count'] = 1
    null_utr['confidence'] = 'low'  # No UTR = can't match to bank

    # Aggregate non-null UTR rows
    has_utr = df[df['utr'].notna() & (df['utr'] != '')].copy()

    if has_utr.empty:
        return null_utr

    agg_dict = {
        'amount_gross': 'sum',
        'commission': 'sum',
        'gst': 'sum',
        'settled_amount': 'sum',
        'settled_dt': 'first',  # Earliest settlement date
        'txn_dt': 'first',      # Earliest transaction date
        'payment_mode': 'first',
        'issuing_bank': 'first',
        'unit': 'first',
        'raw_path': lambda x: '|'.join(x.unique()),  # Join multiple source files
    }

    aggregated = has_utr.groupby('utr', as_index=False).agg(agg_dict)
    aggregated['utr_txn_count'] = has_utr.groupby('utr').size().values
    aggregated['confidence'] = 'high'  # Has UTR = can match to bank

    # Combine aggregated + null UTR rows
    result = pd.concat([aggregated, null_utr], ignore_index=True)

    return result


# ── Bank statement ────────────────────────────────────────────────────────

def _read_with_header_search(path: Path) -> tuple[pd.DataFrame, dict]:
    """Indian Bank export: header is around row 21-22. Find row containing 'Description'."""
    raw = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
    meta: dict[str, str] = {}
    header_row = None
    for i, row in raw.iterrows():
        cells = [str(c) if c is not None and not (isinstance(c, float) and pd.isna(c)) else "" for c in row]
        joined = " | ".join(cells).strip()
        if not joined:
            continue
        # header detection
        if any("description" in c.lower() for c in cells) and any("balance" in c.lower() for c in cells):
            header_row = i
            break
        # capture metadata key:value pairs from earlier rows
        m = re.match(r"\s*([A-Za-z\s/]+?)\s*[:#]\s*(.+)", joined)
        if m:
            k = m.group(1).strip().lower()
            v = m.group(2).strip()
            if "account number" in k:
                meta["account_number"] = re.sub(r"\D", "", v)[:16]
            elif "customer" in k:
                meta["customer"] = v
            elif "ifsc" in k:
                meta["ifsc"] = v.split()[0]
            elif "from" in k and "to" in k:
                meta["period"] = v

    if header_row is None:
        raise ValueError(f"could not find header row in {path}")
    df = pd.read_excel(path, sheet_name=0, header=header_row, dtype=object)
    df = df.dropna(how="all").reset_index(drop=True)
    return df, meta


def extract_bank(path: Path) -> pd.DataFrame:
    df, meta = _read_with_header_search(path)
    # Standardize columns we care about
    rename_map = {}
    for c in df.columns:
        cl = str(c).lower().replace(" ", "").replace(".", "")
        if "valuedate" in cl: rename_map[c] = "value_date"
        elif "postdate" in cl: rename_map[c] = "post_date"
        elif "description" in cl or "narration" in cl: rename_map[c] = "description"
        elif "chq" in cl or "ref" in cl or "utr" in cl: rename_map[c] = "ref_no"
        elif "debit" in cl: rename_map[c] = "debit"
        elif "credit" in cl: rename_map[c] = "credit"
        elif "balance" in cl: rename_map[c] = "balance"
        elif "remitter" in cl: rename_map[c] = "remitter_branch"
    df = df.rename(columns=rename_map)
    keep = [c for c in ("value_date","post_date","description","ref_no","debit","credit","balance","remitter_branch") if c in df.columns]
    df = df[keep].copy()
    if "value_date" in df:
        df["value_date"] = pd.to_datetime(df["value_date"], errors="coerce")
    for c in ("debit", "credit"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    if "balance" in df:
        df["balance"] = df["balance"].astype(str).str.replace(r"[A-Za-z]", "", regex=True)
        df["balance"] = pd.to_numeric(df["balance"], errors="coerce")
    # Drop rows with no value_date AND no debit AND no credit (often footer)
    if "value_date" in df and "debit" in df and "credit" in df:
        m = df["value_date"].notna() | (df["debit"] != 0) | (df["credit"] != 0)
        df = df[m].reset_index(drop=True)

    # Extract UTR / RRN from description
    df["utr_extracted"] = df["description"].astype(str).str.extract(UTR_REGEX, expand=False)
    df["rrn_extracted"] = df["description"].astype(str).str.extract(RRN_FROM_UPI, expand=False)

    # Backfill ref_no with extracted utr if blank
    if "ref_no" in df:
        df["ref_no"] = df["ref_no"].fillna("").astype(str).str.strip()
        df.loc[df["ref_no"] == "", "ref_no"] = df["utr_extracted"]

    df["account_number"] = meta.get("account_number", "")
    df["customer"]       = meta.get("customer", "")
    df["raw_path"]       = str(path.relative_to(ROOT))
    df["unit"]           = "rooftop" if "rooftop" in str(path).lower() else "main"
    return df


# ── Driver ────────────────────────────────────────────────────────────────

def run_ptm() -> pd.DataFrame:
    """Extract 123-column PTM raw files."""
    files = sorted(p for p in PTM_RAW_DIR.glob("*.xlsx"))
    if not files:
        return pd.DataFrame()
    out: list[pd.DataFrame] = []
    for p in files:
        try:
            df = extract_ptm(p)
            print(f"  PTM {p.name}: {len(df)} rows")
            out.append(df)
        except Exception as e:
            print(f"  PTM {p.name}: FAIL — {e}")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def run_upi() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract 8-9 column UPI historical files.

    Returns:
        (raw_df, aggregated_df) - raw transactions and UTR-aggregated
    """
    # Find all UPI files in historical data
    patterns = ["UPI STATMENT", "PTM ROOFTOP", "F&B UPI"]
    files = []
    for pattern in patterns:
        dir_path = UPI_HISTORICAL_BASE / pattern
        if dir_path.exists():
            files.extend(dir_path.glob("*.xlsx"))

    if not files:
        print("  No UPI files found")
        return pd.DataFrame(), pd.DataFrame()

    out: list[pd.DataFrame] = []
    for p in sorted(files):
        try:
            df = extract_upi(p)
            if not df.empty:
                print(f"  UPI {p.name[:50]}: {len(df)} rows")
                out.append(df)
        except Exception as e:
            print(f"  UPI {p.name}: FAIL — {e}")

    if not out:
        return pd.DataFrame(), pd.DataFrame()

    raw = pd.concat(out, ignore_index=True)

    # Aggregate by UTR
    aggregated = aggregate_by_utr(raw)

    return raw, aggregated


def run_bank() -> pd.DataFrame:
    """Extract Indian Bank statements."""
    pat = re.compile(r"statement.*account|indian.*bank|bank.*rooftop", re.I)
    files = [p for p in PROCESSED_DIR.glob("*") if p.suffix.lower() in {".xlsx", ".xls"} and pat.search(p.name)]
    out: list[pd.DataFrame] = []
    for p in sorted(files):
        try:
            df = extract_bank(p)
            print(f"  BANK {p.name}: {len(df)} rows")
            out.append(df)
        except Exception as e:
            print(f"  BANK {p.name}: FAIL — {e}")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main() -> int:
    print("=" * 60)
    print("Payment Extraction Pipeline")
    print("=" * 60)

    # PTM (123-col format)
    print("\n[1/3] PTM (123-col raw):")
    ptm = run_ptm()
    if not ptm.empty:
        csv = write_canonical(ptm, "payment")
        print(f"  ✓ Wrote {csv}")
        print(f"  ✓ {len(ptm)} rows ({(ptm['status']=='SUCCESS').sum()} success)")
        # Verify formula
        delta = (ptm["amount_gross"].fillna(0) - ptm["commission"].fillna(0) - ptm["gst"].fillna(0) - ptm["settled_amount"].fillna(0)).abs()
        print(f"  ✓ Settled = Amount-Comm-GST: {(delta < 0.01).sum()}/{len(ptm)} reconciled")

    # UPI (8-9 col historical)
    print("\n[2/3] UPI (8-9 col historical):")
    upi_raw, upi_agg = run_upi()
    if not upi_raw.empty:
        # Save raw
        csv_raw = write_canonical(upi_raw, "upi_raw")
        print(f"  ✓ Wrote {csv_raw}")
        print(f"  ✓ {len(upi_raw)} raw transactions")

        # Save aggregated
        csv_agg = write_canonical(upi_agg, "upi_payments")
        print(f"  ✓ Wrote {csv_agg}")
        print(f"  ✓ {len(upi_agg)} aggregated payments")

        # Validation stats
        null_utr = upi_raw['utr'].isna() | (upi_raw['utr'] == '')
        null_rate = null_utr.sum() / len(upi_raw)
        unique_utr = upi_raw[~null_utr]['utr'].nunique()
        non_null_count = (~null_utr).sum()
        dup_rate = 1 - (unique_utr / non_null_count) if non_null_count > 0 else 0

        print(f"\n  Validation:")
        print(f"    - Null UTR rate: {null_rate:.1%} ({null_utr.sum()}/{len(upi_raw)})")
        print(f"    - UTR duplicate rate (before agg): {dup_rate:.1%}")
        print(f"    - Unique UTRs: {unique_utr}")
        print(f"    - High confidence (has UTR): {(upi_agg['confidence']=='high').sum()}")
        print(f"    - Low confidence (no UTR): {(upi_agg['confidence']=='low').sum()}")

        # Payment mode breakdown
        if 'payment_mode' in upi_raw.columns:
            modes = upi_raw['payment_mode'].value_counts()
            print(f"\n  Payment modes:")
            for mode, count in modes.items():
                print(f"    - {mode}: {count} ({count/len(upi_raw):.1%})")

        # Unit breakdown
        if 'unit' in upi_raw.columns:
            units = upi_raw['unit'].value_counts()
            print(f"\n  Units:")
            for unit, count in units.items():
                print(f"    - {unit}: {count} ({count/len(upi_raw):.1%})")

    # Bank statements
    print("\n[3/3] BANK:")
    bank = run_bank()
    if not bank.empty:
        csv = write_canonical(bank, "bank")
        print(f"  ✓ Wrote {csv}")
        print(f"  ✓ {len(bank)} rows")
        print(f"  ✓ With extracted UTR: {bank['utr_extracted'].notna().sum()}")

    print("\n" + "=" * 60)
    print("Extraction complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
