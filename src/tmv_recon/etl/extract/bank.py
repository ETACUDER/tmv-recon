"""Extract bank statements → canonical Payment model.

Sources: Indian Bank statements in Excel format (.xlsx, .xls)
Location: meet-recording/data_sheets_historical/mangal all data sheet/INDIAN BANK*/

Per discovery (docs/discovery-2026-04-29-excel-structure.md Section 4.2):
- Headers at row 21 (not row 0) — search first 30 rows for "Value Date"
- 3 column variants: 5, 6, 8 columns (all parseable)
- Metadata in rows 0-20 (account number, date range, cleared balance)
- Skip "Balance brought forward" (BALANCE B/F) row
- Balance suffix "CR"/"DR" needs removal
- Blank amounts = 0
- UTR in column "Chq No/REF No/UTR No" or extract from Description via regex

Outputs:
- data/recon/canonical/bank_payments.csv (mapped to Payment model)
- data/recon/reports/bank_parse_validation.csv (parsing report)
"""
from __future__ import annotations
import re
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from tmv_recon.config import ROOT
from tmv_recon.etl.models import Payment
from ._common import write_canonical

# Source directory paths
BANK_DIRS = [
    ROOT / "meet-recording/data_sheets_historical/mangal all data sheet/INDIAN BANK",
    ROOT / "meet-recording/data_sheets_historical/mangal all data sheet/INDIAN BANK ROOFTOP",
]

# UTR extraction patterns
# Example: "NEFT/YESB/YESBN12025070105404991/ONE 97 COM/"
UTR_FROM_DESC = re.compile(r'/([A-Z]{4}[A-Z0-9]{12,25})/', re.I)


@dataclass
class BankStatementMetadata:
    """Metadata extracted from rows 0-20."""
    account_number: str = ""
    customer_name: str = ""
    ifsc_code: str = ""
    branch_name: str = ""
    statement_date: str = ""
    cleared_balance: str = ""
    date_range: str = ""
    file_path: str = ""


def find_header_row(df_raw: pd.DataFrame, max_search: int = 60) -> int | None:
    """Search first max_search rows for header containing date and amount columns.

    Returns row index or None if not found.

    Handles multiple formats:
    1. Standard: "Value Date" column (rows ~21)
    2. Alternate: "Date" + "Transaction Details" (rows ~36)
    3. Compact: "Txn Date" + "Description" (rows ~12)
    """
    for i in range(min(max_search, len(df_raw))):
        row_values = df_raw.iloc[i].values
        row_str = ' '.join([str(x) for x in row_values if pd.notna(x)])
        row_str_lower = row_str.lower()

        # Format 1: "Value Date"
        if 'Value Date' in row_str or 'value date' in row_str_lower:
            return i

        # Format 2: "Date" and "Transaction Details" (14-col variant)
        if 'Date' in row_str and 'Transaction Details' in row_str:
            return i

        # Format 3: "Txn Date" + "Description" (compact variant)
        # Check for presence of date-related and amount columns
        has_date = any(x in row_str_lower for x in ['txn date', 'date'])
        has_desc = any(x in row_str_lower for x in ['description', 'narration'])
        has_amount = any(x in row_str_lower for x in ['debit amount', 'credit amount', 'debit', 'credit'])

        if has_date and (has_desc or has_amount):
            return i

    return None


def extract_metadata(df_raw: pd.DataFrame, file_path: Path) -> BankStatementMetadata:
    """Extract metadata from rows 0-20.

    Expected structure:
    - Row 6: Account Number : 7223534417
    - Row 14: Statement Date :Fri Aug 08 14:03:50 IST 2025
    - Row 15: Cleared Balance :894825.55
    - Row 19: Statement of Account from 01/07/2025 to 31/07/2025
    """
    meta = BankStatementMetadata(file_path=str(file_path))

    for i in range(min(25, len(df_raw))):
        row_values = df_raw.iloc[i].values
        row_str = '|'.join([str(x) if pd.notna(x) else '' for x in row_values])

        # Account Number
        if m := re.search(r'Account Number\s*:\s*(\d+)', row_str, re.I):
            meta.account_number = m.group(1).strip()

        # Customer name (row 8 typically)
        if i >= 8 and i <= 12 and not re.search(r'[:|@]', row_str):
            # Non-metadata row, likely customer name
            clean = row_str.replace('|', '').strip()
            if len(clean) > 5 and not meta.customer_name:
                meta.customer_name = clean[:100]

        # IFSC Code
        if m := re.search(r'IFSC CODE\s*:\s*([A-Z0-9]+)', row_str, re.I):
            meta.ifsc_code = m.group(1).strip()

        # Branch (row 2)
        if i == 2:
            clean = row_str.replace('|', '').strip()
            if clean and not re.search(r'[:|@]', clean):
                meta.branch_name = clean[:100]

        # Statement Date
        if m := re.search(r'Statement Date\s*:\s*(.+?)(?:\||$)', row_str, re.I):
            meta.statement_date = m.group(1).strip()

        # Cleared Balance
        if m := re.search(r'Cleared Balance\s*:\s*([\d.,]+)', row_str, re.I):
            meta.cleared_balance = m.group(1).strip()

        # Date Range
        if m := re.search(r'from\s+(\d{2}/\d{2}/\d{4})\s+to\s+(\d{2}/\d{2}/\d{4})', row_str, re.I):
            meta.date_range = f"{m.group(1)} to {m.group(2)}"

    return meta


def clean_balance_suffix(balance_str: str) -> tuple[Decimal | None, str]:
    """Parse balance with CR/DR suffix and currency prefix.

    Examples:
        "894825.55CR" → (Decimal("894825.55"), "CR")
        "1234.56DR" → (Decimal("1234.56"), "DR")
        "470414.15 CR" → (Decimal("470414.15"), "CR")
        "INR 672,698.44" → (Decimal("672698.44"), "")

    Returns (amount, type) where type is "CR", "DR", or ""
    """
    if pd.isna(balance_str) or not balance_str:
        return None, ""

    s = str(balance_str).strip()
    balance_type = ""

    # Remove currency prefix (INR, USD, etc.)
    s = re.sub(r'^[A-Z]{3}\s+', '', s, flags=re.I)

    # Extract CR/DR suffix
    if m := re.search(r'\s*(CR|DR)\s*$', s, re.I):
        balance_type = m.group(1).upper()
        s = s[:m.start()].strip()

    # Parse numeric
    s = s.replace(',', '')  # Remove thousand separators
    try:
        return Decimal(s), balance_type
    except (InvalidOperation, ValueError):
        return None, balance_type


def parse_amount(val: Any) -> Decimal:
    """Parse amount field, handle blank = 0."""
    if pd.isna(val) or val == '':
        return Decimal(0)
    try:
        s = str(val).replace(',', '').strip()
        return Decimal(s) if s else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def parse_date_str(val: Any) -> date | None:
    """Parse date from various formats: DD/MM/YYYY, DD Mon YYYY, YYYY-MM-DD HH:MM:SS."""
    if pd.isna(val) or not val:
        return None
    try:
        # Handle Excel date objects
        if isinstance(val, (pd.Timestamp, date)):
            return val.date() if isinstance(val, pd.Timestamp) else val

        # Parse string formats
        s = str(val).strip()

        # Format: DD/MM/YYYY
        if m := re.match(r'(\d{2})/(\d{2})/(\d{4})', s):
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(year, month, day)

        # Format: DD Mon YYYY (e.g., "01 Jan 2026")
        if m := re.match(r'(\d{2})\s+([A-Za-z]+)\s+(\d{4})', s):
            # Use pandas to parse
            return pd.to_datetime(s, format='%d %b %Y', errors='coerce').date()

        # Format: YYYY-MM-DD HH:MM:SS (e.g., "2026-03-01 00:00:00")
        if m := re.match(r'(\d{4})-(\d{2})-(\d{2})', s):
            return pd.to_datetime(s, errors='coerce').date()

    except (ValueError, AttributeError):
        pass
    return None


def extract_utr(description: str, ref_col: str) -> str:
    """Extract UTR from Description or use ref_col.

    Priority:
    1. Use ref_col if not blank
    2. Extract from description using regex: /UTR_NUMBER/

    Examples from Description:
        "BY TRANSFER NEFT/YESB/YESBN12025070105404991/ONE 97 COM/"
        → "YESBN12025070105404991"
    """
    # Use ref_col if available
    if ref_col and str(ref_col).strip():
        return str(ref_col).strip()

    # Extract from description
    if description and isinstance(description, str):
        if m := UTR_FROM_DESC.search(description):
            return m.group(1).upper()

    return ""


def detect_column_variant(df: pd.DataFrame) -> str:
    """Identify which of 4 column variants this is.

    Variants:
    - 5 cols: Value Date, Description, Debit Amount, Credit Amount, Balance
    - 6 cols: + Chq No/REF No/UTR No
    - 8 cols: + Post Date, Remitter Branch
    - 14 cols: Date, Transaction Details, Debits, Credits, Balance (alternate format)
    """
    cols = len(df.columns)
    has_utr_col = any('ref' in str(c).lower() or 'utr' in str(c).lower() for c in df.columns)
    has_post_date = any('post date' in str(c).lower() for c in df.columns)
    has_transaction_details = any('transaction details' in str(c).lower() for c in df.columns)

    if cols >= 14 or has_transaction_details:
        return "14-col (alternate)"
    elif cols >= 8 or has_post_date:
        return "8-col (full)"
    elif has_utr_col:
        return "6-col (standard)"
    else:
        return "5-col (minimal)"


def parse_bank_statement(file_path: Path) -> tuple[list[Payment], BankStatementMetadata, dict[str, Any]]:
    """Parse single bank statement file.

    Returns:
        (payments, metadata, stats)
    """
    # Read raw for header detection
    # Handle both .xlsx and .xls files
    try:
        df_raw = pd.read_excel(file_path, header=None, dtype=object, engine='openpyxl')
    except Exception:
        # Try with xlrd for .xls files (if available)
        try:
            df_raw = pd.read_excel(file_path, header=None, dtype=object, engine='xlrd')
        except Exception:
            # Last resort: convert .xls to .xlsx using any available engine
            try:
                df_raw = pd.read_excel(file_path, header=None, dtype=object)
            except Exception as e:
                raise ValueError(f"Cannot read {file_path.name}: {e}")

    # Find header row
    header_row = find_header_row(df_raw)
    if header_row is None:
        raise ValueError(f"Could not find header row with 'Value Date' in first 30 rows: {file_path.name}")

    # Extract metadata
    metadata = extract_metadata(df_raw, file_path)

    # Re-read with proper header
    try:
        df = pd.read_excel(file_path, header=header_row, dtype=object, engine='openpyxl')
    except Exception:
        try:
            df = pd.read_excel(file_path, header=header_row, dtype=object, engine='xlrd')
        except Exception:
            df = pd.read_excel(file_path, header=header_row, dtype=object)

    # Detect column variant
    variant = detect_column_variant(df)

    # Standardize column names (case-insensitive matching)
    col_map = {}
    for col in df.columns:
        col_lower = str(col).lower().replace(' ', '')
        if 'valuedate' in col_lower or 'txndate' in col_lower or (col_lower == 'date' and 'value_date' not in col_map.values()):
            col_map[col] = 'value_date'
        elif 'postdate' in col_lower:
            col_map[col] = 'post_date'
        elif 'description' in col_lower or 'narration' in col_lower or 'transactiondetails' in col_lower:
            col_map[col] = 'description'
        elif 'chequeno' in col_lower or 'chqno' in col_lower or 'ref' in col_lower or 'utr' in col_lower:
            col_map[col] = 'ref_no'
        elif 'debit' in col_lower:
            col_map[col] = 'debit_amount'
        elif 'credit' in col_lower:
            col_map[col] = 'credit_amount'
        elif 'balance' in col_lower:
            col_map[col] = 'balance'
        elif 'remitter' in col_lower or 'branch' in col_lower:
            col_map[col] = 'remitter_branch'

    df = df.rename(columns=col_map)

    # Skip "Balance brought forward" rows
    if 'description' in df.columns:
        df = df[~df['description'].astype(str).str.contains('BALANCE B/F', case=False, na=False)]

    # Parse into Payment objects
    payments = []
    stats = {
        'file': file_path.name,
        'variant': variant,
        'header_row': header_row,
        'total_rows': len(df),
        'parsed_count': 0,
        'with_utr': 0,
        'credit_sum': Decimal(0),
        'debit_sum': Decimal(0),
        'skipped_rows': 0,
    }

    for idx, row in df.iterrows():
        # Skip empty rows
        if pd.isna(row.get('value_date')) and pd.isna(row.get('description')):
            stats['skipped_rows'] += 1
            continue

        # Parse fields
        txn_date = parse_date_str(row.get('value_date'))
        if not txn_date:
            # Skip rows without valid date
            stats['skipped_rows'] += 1
            continue

        description = str(row.get('description', ''))
        ref_no = str(row.get('ref_no', ''))

        debit_amt = parse_amount(row.get('debit_amount'))
        credit_amt = parse_amount(row.get('credit_amount'))

        # Determine gross_amount (receipt = credit, payment = debit)
        gross_amount = credit_amt if credit_amt > 0 else -debit_amt

        # Extract UTR
        utr = extract_utr(description, ref_no)

        # Create Payment object
        payment = Payment(
            payment_id=f"bank_{metadata.account_number}_{idx}",
            source="bank",
            unit="rooftop" if "rooftop" in str(file_path).lower() else "front_office",
            txn_date=txn_date,
            settled_date=txn_date,  # For bank, settled = transaction date
            gross_amount=gross_amount,
            commission=Decimal(0),  # Bank statements don't show commission
            commission_gst=Decimal(0),
            settled_amount=gross_amount,
            utr=utr,
            payment_mode="BANK_TRANSFER" if "NEFT" in description or "RTGS" in description else "",
            issuing_bank="",
            customer_vpa="",
            invoice_no="",
            matched_invoice_no="",
            raw_path=str(file_path.relative_to(ROOT)),
        )

        payments.append(payment)
        stats['parsed_count'] += 1

        if utr:
            stats['with_utr'] += 1

        if credit_amt > 0:
            stats['credit_sum'] += credit_amt
        if debit_amt > 0:
            stats['debit_sum'] += debit_amt

    return payments, metadata, stats


def validate_all_bank_files() -> pd.DataFrame:
    """Parse all bank files and generate validation report.

    Returns DataFrame with per-file statistics.
    """
    all_payments = []
    validation_rows = []

    for bank_dir in BANK_DIRS:
        if not bank_dir.exists():
            print(f"Warning: {bank_dir} not found, skipping")
            continue

        # Find all Excel files
        files = list(bank_dir.glob("*.xlsx")) + list(bank_dir.glob("*.xls"))

        for file_path in sorted(files):
            print(f"Parsing: {file_path.name}")

            try:
                payments, metadata, stats = parse_bank_statement(file_path)

                # Add to global list
                all_payments.extend(payments)

                # Build validation row
                validation_rows.append({
                    'file': file_path.name,
                    'account_number': metadata.account_number,
                    'date_range': metadata.date_range,
                    'cleared_balance': metadata.cleared_balance,
                    'column_variant': stats['variant'],
                    'header_row': stats['header_row'],
                    'total_rows': stats['total_rows'],
                    'parsed_rows': stats['parsed_count'],
                    'skipped_rows': stats['skipped_rows'],
                    'utr_count': stats['with_utr'],
                    'utr_rate': f"{stats['with_utr']/max(stats['parsed_count'],1)*100:.1f}%",
                    'credit_sum': float(stats['credit_sum']),
                    'debit_sum': float(stats['debit_sum']),
                    'status': 'SUCCESS',
                })

                print(f"  ✓ {stats['parsed_count']} payments, {stats['with_utr']} with UTR ({stats['variant']})")

            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                validation_rows.append({
                    'file': file_path.name,
                    'account_number': '',
                    'date_range': '',
                    'cleared_balance': '',
                    'column_variant': '',
                    'header_row': -1,
                    'total_rows': 0,
                    'parsed_rows': 0,
                    'skipped_rows': 0,
                    'utr_count': 0,
                    'utr_rate': '0%',
                    'credit_sum': 0,
                    'debit_sum': 0,
                    'status': f'FAILED: {str(e)[:100]}',
                })

    # Convert payments to DataFrame
    if all_payments:
        payment_dicts = []
        for p in all_payments:
            payment_dicts.append({
                'payment_id': p.payment_id,
                'source': p.source,
                'unit': p.unit,
                'txn_date': p.txn_date,
                'settled_date': p.settled_date,
                'gross_amount': float(p.gross_amount) if p.gross_amount else None,
                'commission': float(p.commission) if p.commission else None,
                'commission_gst': float(p.commission_gst) if p.commission_gst else None,
                'settled_amount': float(p.settled_amount) if p.settled_amount else None,
                'utr': p.utr,
                'payment_mode': p.payment_mode,
                'issuing_bank': p.issuing_bank,
                'customer_vpa': p.customer_vpa,
                'invoice_no': p.invoice_no,
                'matched_invoice_no': p.matched_invoice_no,
                'raw_path': p.raw_path,
            })

        df_payments = pd.DataFrame(payment_dicts)

        # Save canonical payments
        canonical_csv = write_canonical(df_payments, "bank_payments")
        print(f"\n✓ Saved {len(df_payments)} bank payments to {canonical_csv}")
    else:
        print("\n⚠ No payments parsed")

    # Save validation report
    df_validation = pd.DataFrame(validation_rows)
    report_dir = ROOT / "data/recon/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_csv = report_dir / "bank_parse_validation.csv"
    df_validation.to_csv(report_csv, index=False)
    print(f"✓ Validation report: {report_csv}")

    return df_validation


def main() -> int:
    """CLI entry point."""
    print("=" * 80)
    print("Bank Statement Parser")
    print("=" * 80)
    print()

    validation_df = validate_all_bank_files()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {len(validation_df)}")
    print(f"Successful: {(validation_df['status'] == 'SUCCESS').sum()}")
    print(f"Failed: {(validation_df['status'] != 'SUCCESS').sum()}")
    print()

    # Variant breakdown
    if 'column_variant' in validation_df.columns:
        print("Column Variants:")
        variant_counts = validation_df[validation_df['status'] == 'SUCCESS']['column_variant'].value_counts()
        for variant, count in variant_counts.items():
            print(f"  {variant}: {count} files")

    print()
    print(f"Total payments: {validation_df['parsed_rows'].sum()}")
    print(f"Total credits: ₹{validation_df['credit_sum'].sum():,.2f}")
    print(f"Total debits: ₹{validation_df['debit_sum'].sum():,.2f}")
    print(f"UTR extraction rate: {validation_df['utr_count'].sum()}/{validation_df['parsed_rows'].sum()} ({validation_df['utr_count'].sum()/max(validation_df['parsed_rows'].sum(),1)*100:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
