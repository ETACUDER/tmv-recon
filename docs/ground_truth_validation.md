# Ground Truth Validation Tool

## Overview

Validates generated vouchers against actual Tally daybook data to ensure structural accuracy.

**Module:** `src/tmv_recon/etl/ground_truth.py`  
**CLI:** `tmv-recon-test`  
**Tests:** `tests/test_ground_truth.py`

## Features

### Comparison Metrics

1. **Voucher Type Match** (25% weight)
   - Exact match: Sales, Journal, Purchase, Receipt, Credit Note
   - Target: 95%+ match rate

2. **Ledger Names Match** (35% weight)
   - Exact string match of all ledger names in voucher
   - Target: 100% match rate

3. **Amount Match** (30% weight)
   - Within ₹1 tolerance for rounding
   - Target: 98%+ match rate

4. **Narration Pattern Match** (10% weight)
   - Regex-based pattern matching
   - Invoice number extraction
   - Fuzzy word similarity (80% threshold)
   - Target: 95%+ match rate

### Matching Strategy

1. **Invoice Number Match** (Priority 1)
   - Extracts invoice numbers from narration/reference/voucher number
   - Patterns: `25-26/####`, `INVOICE NO:-25-26/####`, etc.

2. **Amount + Date Match** (Priority 2)
   - Amount within ₹1
   - Date within ±3 days

3. **Highest Similarity Score** (Fallback)
   - Compares all vouchers and picks best match

### XML Parsing

Handles both Tally voucher entry types:
- `LEDGERENTRIES.LIST` - Sales, Purchase, Credit Note
- `ALLLEDGERENTRIES.LIST` - Journal, Receipt

**Robust parsing:**
- Cleans invalid control characters (`\x00-\x1F`)
- Removes invalid entity references (`&#4;`)
- Handles malformed Tally XML exports

## Usage

### CLI Command

```bash
# Compare generated vouchers against baseline
tmv-recon-test \
  --baseline data/tally/raw_xml/daybook_FY25-26.xml \
  --generated data/recon/output/ \
  --date-range 2026-03-01:2026-03-31 \
  --report data/recon/reports/ground_truth_diff.csv

# Single file comparison
tmv-recon-test \
  --baseline daybook.xml \
  --generated vouchers_march.xml \
  --report diff.csv \
  --summary summary.txt
```

### Parameters

- `--baseline` - Path to Tally daybook XML (ground truth)
- `--generated` - Path to generated XML file or directory
- `--date-range` - Optional date filter `YYYY-MM-DD:YYYY-MM-DD`
- `--report` - Output CSV path (required)
- `--summary` - Output text summary path (optional, defaults to report.txt)

### Exit Codes

- `0` - Validation passed (≥95% average score)
- `1` - Validation failed (< 95% average score or no matches)

## Output Reports

### CSV Report

Detailed line-by-line comparison:

```csv
Actual Voucher No,Generated Voucher No,Actual Date,Generated Date,Match Score,Voucher Type Match,Ledger Names Match,Amount Match,Narration Match,Differences
25-26/6453,25-26/6453,2026-03-31,2026-03-31,100.00%,Yes,Yes,Yes,Yes,
25-26/6454,25-26/6454,2026-03-31,2026-03-31,95.00%,Yes,Yes,Yes,No,Narration: 'INVOICE NO:-25-26/6454' != 'INV: 25-26/6454'
```

### Text Summary

High-level statistics and acceptance criteria:

```
================================================================================
GROUND TRUTH VALIDATION REPORT
================================================================================

OVERVIEW
--------------------------------------------------------------------------------
Total actual vouchers:     60
Total generated vouchers:  58
Matched vouchers:          57
Unmatched actual:          3
Unmatched generated:       1

MATCH QUALITY
--------------------------------------------------------------------------------
Average match score:       97.5%
Acceptable matches (≥95%): 55 (96.5%)

COMPONENT MATCH RATES
--------------------------------------------------------------------------------
Voucher type:    57/57 (100.0%) [Target: 95%]
Ledger names:    57/57 (100.0%) [Target: 100%]
Amounts (±₹1):   56/57 (98.2%) [Target: 98%]
Narration:       54/57 (94.7%) [Target: 95%]

VOUCHER TYPE DISTRIBUTION
--------------------------------------------------------------------------------
Type                     Actual  Generated      Match
--------------------------------------------------------------------------------
Sales                        22         21          ✗
Journal                      22         22          ✓
Purchase                     11         11          ✓
Receipt                       3          3          ✓
Credit Note                   2          1          ✗

ACCEPTANCE CRITERIA
--------------------------------------------------------------------------------
✓ PASS   Voucher type match ≥95%        (Actual: 100.0%)
✓ PASS   Ledger name match 100%         (Actual: 100.0%)
✓ PASS   Amount match ≥98%              (Actual: 98.2%)
✗ FAIL   Narration match ≥95%           (Actual: 94.7%)

================================================================================
```

## Python API

```python
from tmv_recon.etl.ground_truth import (
    parse_tally_vouchers,
    parse_generated_vouchers,
    compare_vouchers,
    find_best_match,
    filter_vouchers_by_date,
    generate_diff_report,
    generate_summary_report
)
from datetime import date

# Parse vouchers
actual_vouchers = parse_tally_vouchers("daybook.xml")
generated_vouchers = parse_generated_vouchers("generated.xml")

# Filter by date
actual_vouchers = filter_vouchers_by_date(
    actual_vouchers, 
    date(2026, 3, 1), 
    date(2026, 3, 31)
)

# Match and compare
comparisons = []
used_indices = set()

for actual in actual_vouchers:
    best_match, score, idx = find_best_match(
        actual, 
        generated_vouchers, 
        used_indices
    )
    
    if best_match:
        used_indices.add(idx)
        comparison = compare_vouchers(actual, best_match)
        comparisons.append(comparison)

# Generate reports
generate_diff_report(
    comparisons, 
    actual_vouchers, 
    generated_vouchers, 
    "diff.csv"
)

generate_summary_report(
    comparisons, 
    actual_vouchers, 
    generated_vouchers, 
    "summary.txt"
)

# Check acceptance
avg_score = sum(c.match_score for c in comparisons) / len(comparisons)
print(f"Validation: {'PASS' if avg_score >= 0.95 else 'FAIL'}")
```

## Demo Script

Test the validation tool with actual data:

```bash
python scripts/demo_ground_truth_validation.py
```

This script:
1. Parses 60 actual vouchers from daybook
2. Uses same file as generated (100% match test)
3. Generates comparison reports
4. Validates acceptance criteria

## Acceptance Criteria

Per requirements document (Section 6):

| Metric | Target | Weight |
|--------|--------|--------|
| Voucher type match | ≥95% | 25% |
| Ledger name match | 100% | 35% |
| Amount match (±₹1) | ≥98% | 30% |
| Narration pattern | ≥95% | 10% |
| **Overall** | **≥95%** | **100%** |

## Test Coverage

Run tests:

```bash
pytest tests/test_ground_truth.py -v
```

Test cases:
- `test_extract_invoice_no` - Invoice number extraction
- `test_compare_narrations` - Fuzzy narration matching
- `test_voucher_totals` - Debit/credit calculations
- `test_compare_vouchers_perfect_match` - 100% match
- `test_compare_vouchers_amount_tolerance` - ±₹1 tolerance
- `test_compare_vouchers_type_mismatch` - Type validation
- `test_compare_vouchers_ledger_mismatch` - Ledger validation
- `test_find_best_match_invoice_number` - Matching strategy
- `test_filter_vouchers_by_date` - Date filtering
- `test_parse_real_daybook` - Integration test (60 vouchers)

## Known Issues

### Tally XML Quirks

1. **Invalid character references** - `&#4;` in CSTFORMISSUETYPE fields
   - **Solution:** Cleaned during parsing

2. **Control characters** - `\x05` in STATKEY fields
   - **Solution:** Removed during parsing

3. **Mixed entry types** - Some vouchers use LEDGERENTRIES.LIST, others use ALLLEDGERENTRIES.LIST
   - **Solution:** Parser checks both types

### Narration Matching

- Minor formatting differences acceptable (whitespace, case)
- Invoice number must match if present
- Word similarity threshold: 80%

## Future Enhancements

1. **Partial ledger matching** - Credit for subset matches
2. **Date range smart defaults** - Auto-detect from baseline
3. **HTML report output** - Visual diff viewer
4. **Batch validation** - Compare multiple months in one run
5. **Performance optimization** - Parallel processing for large files

## Related Files

- `src/tmv_recon/etl/ground_truth.py` - Core module
- `src/tmv_recon/integration/cli_test.py` - CLI entry point
- `tests/test_ground_truth.py` - Test suite
- `scripts/demo_ground_truth_validation.py` - Demo script
- `docs/discovery-2026-04-29-requirements.md` - Section 6: Testing Strategy
