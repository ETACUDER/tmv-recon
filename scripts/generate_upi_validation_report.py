"""Generate comprehensive UPI parsing validation report.

Validates:
- UTR duplicate rate (before/after aggregation)
- Null UTR rate by file
- Payment mode distribution
- Unit distribution
- Aggregation correctness
- Amount reconciliation

Output: data/recon/reports/upi_parse_validation.csv
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tmv_recon.etl.extract.payment import run_upi
from tmv_recon.config import ROOT

REPORT_DIR = ROOT / "data" / "recon" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def analyze_file(file_path: Path, df: pd.DataFrame) -> dict:
    """Analyze a single UPI file."""
    if df.empty:
        return None

    file_df = df[df['raw_path'].str.contains(file_path.name, na=False)]
    if file_df.empty:
        return None

    null_utr = file_df['utr'].isna() | (file_df['utr'] == '')
    non_null = file_df[~null_utr]

    return {
        'file': file_path.name,
        'total_rows': len(file_df),
        'null_utr_count': null_utr.sum(),
        'null_utr_rate': null_utr.sum() / len(file_df) if len(file_df) > 0 else 0,
        'unique_utrs': non_null['utr'].nunique() if len(non_null) > 0 else 0,
        'utr_dup_rate': 1 - (non_null['utr'].nunique() / len(non_null)) if len(non_null) > 0 else 0,
        'total_amount': file_df['amount_gross'].sum(),
        'total_settled': file_df['settled_amount'].sum(),
        'total_commission': file_df['commission'].sum(),
        'total_gst': file_df['gst'].sum(),
        'unit': file_df['unit'].iloc[0] if len(file_df) > 0 else '',
    }


def generate_validation_report():
    """Generate comprehensive validation report."""
    print("=" * 70)
    print("UPI PARSER VALIDATION REPORT")
    print("=" * 70)

    # Extract all UPI data
    print("\n[1/4] Extracting UPI data...")
    upi_raw, upi_agg = run_upi()

    if upi_raw.empty:
        print("ERROR: No data extracted")
        return 1

    # Overall statistics
    print("\n[2/4] Computing overall statistics...")
    null_utr = upi_raw['utr'].isna() | (upi_raw['utr'] == '')
    non_null = upi_raw[~null_utr]

    stats = {
        'Total raw transactions': len(upi_raw),
        'Total aggregated payments': len(upi_agg),
        'Null UTR count': null_utr.sum(),
        'Null UTR rate': f"{null_utr.sum() / len(upi_raw):.1%}",
        'Unique UTRs': non_null['utr'].nunique(),
        'UTR dup rate (before agg)': f"{1 - (non_null['utr'].nunique() / len(non_null)):.1%}",
        'High confidence payments': (upi_agg['confidence'] == 'high').sum(),
        'Low confidence payments': (upi_agg['confidence'] == 'low').sum(),
        'Total amount (raw)': f"₹{upi_raw['amount_gross'].sum():,.2f}",
        'Total amount (agg)': f"₹{upi_agg['amount_gross'].sum():,.2f}",
        'Amount reconciliation': 'PASS' if abs(upi_raw['amount_gross'].sum() - upi_agg['amount_gross'].sum()) < 1 else 'FAIL',
    }

    print("\nOverall Statistics:")
    for k, v in stats.items():
        print(f"  {k:.<40} {v}")

    # Per-file analysis
    print("\n[3/4] Analyzing per-file statistics...")
    base = ROOT / "meet-recording" / "data_sheets_historical" / "mangal all data sheet"
    patterns = ["UPI STATMENT", "PTM ROOFTOP", "F&B UPI"]
    files = []
    for pattern in patterns:
        dir_path = base / pattern
        if dir_path.exists():
            files.extend(dir_path.glob("*.xlsx"))

    file_stats = []
    for f in sorted(files):
        stat = analyze_file(f, upi_raw)
        if stat:
            file_stats.append(stat)

    df_file_stats = pd.DataFrame(file_stats)

    print(f"\nPer-file statistics ({len(df_file_stats)} files):")
    print(df_file_stats[['file', 'total_rows', 'null_utr_rate', 'utr_dup_rate', 'unit']].to_string(index=False))

    # Payment mode distribution
    print("\n[4/4] Computing distribution breakdowns...")
    mode_dist = upi_raw['payment_mode'].value_counts()
    print("\nPayment Mode Distribution:")
    for mode, count in mode_dist.head(10).items():
        print(f"  {mode:.<30} {count:>6} ({count/len(upi_raw):>6.1%})")

    # Unit distribution
    unit_dist = upi_raw['unit'].value_counts()
    print("\nUnit Distribution:")
    for unit, count in unit_dist.items():
        print(f"  {unit:.<30} {count:>6} ({count/len(upi_raw):>6.1%})")

    # Aggregation validation
    print("\nAggregation Validation:")
    max_txn = upi_agg['utr_txn_count'].max()
    avg_txn = upi_agg[upi_agg['confidence']=='high']['utr_txn_count'].mean()
    print(f"  Max transactions per UTR: {max_txn}")
    print(f"  Avg transactions per UTR: {avg_txn:.1f}")

    # Top aggregated UTRs
    top_utrs = upi_agg[upi_agg['confidence']=='high'].nlargest(5, 'utr_txn_count')
    print("\nTop 5 UTRs by transaction count:")
    print(top_utrs[['utr', 'utr_txn_count', 'amount_gross', 'settled_amount']].to_string(index=False))

    # Save reports
    print("\n" + "=" * 70)
    print("SAVING REPORTS")
    print("=" * 70)

    # File-level report
    report_file = REPORT_DIR / "upi_parse_validation.csv"
    df_file_stats.to_csv(report_file, index=False)
    print(f"✓ Per-file validation: {report_file}")

    # Overall summary
    summary_file = REPORT_DIR / "upi_parse_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("UPI PARSER VALIDATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
        f.write("\n" + "=" * 70 + "\n")
    print(f"✓ Summary report: {summary_file}")

    # Payment mode distribution
    mode_file = REPORT_DIR / "upi_payment_modes.csv"
    mode_dist.to_csv(mode_file, header=['count'])
    print(f"✓ Payment modes: {mode_file}")

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    # Critical checks
    print("\nCritical Checks:")
    checks = []

    # Check 1: UTR duplicate rate should be ~93%
    dup_rate_raw = 1 - (non_null['utr'].nunique() / len(non_null))
    check1 = "PASS" if 0.85 <= dup_rate_raw <= 0.95 else "FAIL"
    checks.append(f"  [{check1}] UTR duplicate rate ~93%: {dup_rate_raw:.1%}")

    # Check 2: Null UTR rate should be reasonable (< 60%)
    null_rate = null_utr.sum() / len(upi_raw)
    check2 = "PASS" if null_rate < 0.60 else "WARN"
    checks.append(f"  [{check2}] Null UTR rate < 60%: {null_rate:.1%}")

    # Check 3: Aggregation should reduce row count significantly
    reduction = 1 - (len(upi_agg) / len(upi_raw))
    check3 = "PASS" if reduction > 0.80 else "FAIL"
    checks.append(f"  [{check3}] Row reduction > 80%: {reduction:.1%}")

    # Check 4: Amount reconciliation
    amt_diff = abs(upi_raw['amount_gross'].sum() - upi_agg['amount_gross'].sum())
    check4 = "PASS" if amt_diff < 1 else "FAIL"
    checks.append(f"  [{check4}] Amount reconciliation: ₹{amt_diff:.2f} diff")

    for check in checks:
        print(check)

    all_pass = all("PASS" in c for c in checks)
    if all_pass:
        print("\n✓ ALL CRITICAL CHECKS PASSED")
        return 0
    else:
        print("\n⚠ SOME CHECKS FAILED/WARNED")
        return 1


if __name__ == "__main__":
    sys.exit(generate_validation_report())
