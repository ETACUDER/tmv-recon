# TMV Reconciliation System - Production Guide

**Date:** 2026-04-29  
**Status:** Production Ready  
**Version:** 2.0 (Phase 2 Complete)

---

## Quick Start

### 1. Monthly Data Collection

Collect from Urvashi/sources:
- **Agoda exports** → `data/booking/raw/AGODA*.xlsx`
- **UPI/PTM statements** → `data/payments/raw/PTM*.xlsx`
- **Bank statements** → `data/payments/raw/INDIAN_BANK*.xlsx`
- **EZee transaction detail** → `meet-recording/transaction_detail*.xlsx`

### 2. Run Pipeline

```bash
# Extract all sources
.venv/bin/python -m tmv_recon.etl.extract.booking
.venv/bin/python -m tmv_recon.etl.extract.payment
.venv/bin/python -m tmv_recon.etl.extract.invoice

# Generate vouchers
.venv/bin/python scripts/generate_sales_vouchers.py
.venv/bin/python scripts/generate_journal_samples.py

# Validate
.venv/bin/python -m pytest tests/test_validator.py -v
```

### 3. Review & Import

1. Review CSV reports in `data/recon/reports/`
2. Check unmatched records in `data/recon/unmatched/`
3. Import XMLs to Tally:
   - Gateway → Import → Vouchers
   - Select `data/recon/output/sales_vouchers_*.xml`
   - Select `data/recon/output/journal_vouchers_*.xml`

---

## System Architecture

```
Raw Excel Files (monthly dumps)
  ↓
┌─────────────────────────────────────┐
│ EXTRACT LAYER                       │
│ ├─ Agoda Parser (17 header variants)│
│ ├─ Bank Parser (row-21 headers)    │
│ ├─ UPI Parser (UTR aggregation)    │
│ └─ Invoice Parser (EZee detail)    │
└─────────────────────────────────────┘
  ↓
Canonical CSVs (bookings, payments, invoices)
  ↓
┌─────────────────────────────────────┐
│ TRANSFORM LAYER (Matcher)          │
│ ├─ Stage 1: Exact Match (invoice#, UTR)│
│ ├─ Stage 2: Fuzzy Match (name+date+amt)│
│ └─ Stage 3: Manual Queue (unmatched)   │
└─────────────────────────────────────┘
  ↓
Match CSVs (exact, fuzzy, unmatched)
  ↓
┌─────────────────────────────────────┐
│ LOAD LAYER (Voucher Generators)    │
│ ├─ Sales Vouchers (invoices)       │
│ ├─ Journal Vouchers (payments)     │
│ └─ Credit Notes (rate changes)     │
└─────────────────────────────────────┘
  ↓
Tally XML Files (ready for import)
  ↓
┌─────────────────────────────────────┐
│ VALIDATION LAYER                    │
│ ├─ Amount balance check (sum=0)    │
│ ├─ Ledger catalog verification     │
│ ├─ Ground truth comparison (100%)  │
│ └─ Duplicate detection (SQLite)    │
└─────────────────────────────────────┘
```

---

## Data Flow

### Input Files

| Source | Location | Format | Frequency |
|--------|----------|--------|-----------|
| Agoda | `meet-recording/.../AGODA/` | .xlsx (17 variants) | Monthly |
| UPI/PTM | `meet-recording/.../UPI*/` | .xlsx (8-9 cols) | Monthly |
| Bank | `meet-recording/.../INDIAN BANK*/` | .xlsx/.xls | Monthly |
| Invoice | `meet-recording/transaction_detail*.xlsx` | .xlsx (55 cols) | Ad-hoc |

### Canonical Output

| File | Records | Description |
|------|---------|-------------|
| `bookings.csv` | 3,476 | OTA reservations with commission |
| `upi_payments.csv` | 551 | Aggregated settlements (UTR dedup) |
| `bank_payments.csv` | 1,056 | Bank transactions with UTR |
| `invoice.csv` | 301 | EZee invoices |

### Match Output

| File | Purpose |
|------|---------|
| `exact_matches.csv` | High confidence (invoice#, UTR exact) |
| `fuzzy_matches.csv` | Medium confidence (name+date+amount) |
| `unmatched/*.csv` | Manual review queue with reason codes |

### Tally XML Output

| File | Vouchers | Type |
|------|----------|------|
| `sales_vouchers_*.xml` | N | Sales (LEDGERENTRIES.LIST) |
| `journal_vouchers_*.xml` | M | Journal (ALLLEDGERENTRIES.LIST) |

---

## Monthly Workflow

### Week 1: Data Collection (Day 1-2)

1. **Request files from Urvashi:**
   - Agoda monthly export
   - PTM statements (Front Office, Rooftop, F&B)
   - Bank statements (Main + Rooftop)
   - EZee transaction detail

2. **Place files in correct directories:**
   ```bash
   mkdir -p data/booking/raw/
   mkdir -p data/payments/raw/
   # Copy files
   ```

### Week 1: Extraction (Day 2-3)

```bash
# Extract all sources
.venv/bin/python -m tmv_recon.etl.extract.booking
# Output: 3,476 bookings → data/recon/canonical/bookings.csv

.venv/bin/python -m tmv_recon.etl.extract.payment
# Output: 551 aggregated payments → data/recon/canonical/upi_payments.csv

# Check validation reports
cat data/recon/reports/agoda_parse_validation.csv
cat data/recon/reports/upi_parse_validation.csv
```

### Week 1: Matching (Day 3-4)

```bash
# Run 3-stage matcher
.venv/bin/python -m tmv_recon.etl.recon

# Review match summary
cat data/recon/reports/match_summary.txt

# Expected results:
# - Exact matches: ~95% (invoice ↔ booking)
# - Fuzzy matches: ~80% (payment ↔ invoice)
# - Unmatched: <5% (manual review)
```

### Week 1: Manual Review (Day 4-5)

Review unmatched records:

```bash
# Check unmatched invoices
cat data/recon/unmatched/invoices.csv
# Reason codes: NO_JOIN_KEY, AMOUNT_MISMATCH, DATE_OUT_RANGE

# Check unmatched payments
cat data/recon/unmatched/payments.csv

# Fix data quality issues:
# - Add missing invoice numbers
# - Correct guest name typos
# - Adjust date ranges
# Re-run matcher
```

### Week 2: Voucher Generation (Day 1-2)

```bash
# Generate Sales vouchers
.venv/bin/python scripts/generate_sales_vouchers.py
# Output: data/recon/output/sales_vouchers_2026-04-29.xml

# Generate Journal vouchers
.venv/bin/python scripts/generate_journal_samples.py
# Output: data/recon/output/journal_vouchers_2026-04-29.xml

# Validate
.venv/bin/python -m pytest tests/test_validator.py -v
```

### Week 2: Tally Import (Day 2-3)

1. **Backup Tally data** (always!)
2. **Import Sales vouchers:**
   - Gateway → Import → Vouchers
   - Select `sales_vouchers_*.xml`
   - Review IMPORTRESULT (CREATED, ERRORS)
3. **Import Journal vouchers:**
   - Same process
4. **Verify in Tally:**
   - Gateway → Reports → Day Book
   - Check voucher count, amounts
   - Run Pending Bills report

### Week 2: Reconciliation (Day 3-5)

1. **Compare:**
   - Generated voucher totals vs manual entry
   - Bank statement totals vs Tally
   - Pending Bills report vs unmatched queue

2. **Adjustments:**
   - Create manual vouchers for unmatched items
   - Fix any import errors
   - Document exceptions

---

## Data Quality Checks

### Pre-Import Validation

Run before generating XML:

```python
from tmv_recon.etl.validator import (
    validate_amount_balance,
    validate_ledger_exists,
    validate_gst_calculation
)

# All vouchers must pass:
# ✓ Amount balance (sum = 0)
# ✓ Ledger exists in catalog
# ✓ GST calculation (net + cgst + sgst = gross ±₹1)
```

### Post-Import Verification

```bash
# Compare generated vs actual Tally data
.venv/bin/python -m tmv_recon.etl.ground_truth \
  --baseline data/tally/raw_xml/daybook_current.xml \
  --generated data/recon/output/ \
  --report data/recon/reports/verification.csv

# Target: 95%+ match on all criteria
```

---

## Troubleshooting

### Parser Errors

**Issue:** "Unrecognized columns found"

```bash
# Check validation report
cat data/recon/reports/agoda_parse_validation.csv

# Add new column mappings to:
# src/tmv_recon/etl/extract/booking.py
# COLUMN_NORMALIZER dict
```

**Issue:** "Bank statement header not found"

```bash
# Parser searches rows 12-60 for "Value Date"
# If custom format, update:
# src/tmv_recon/etl/extract/bank.py
# HEADER_SIGNATURES list
```

### Matcher Issues

**Issue:** Low match rate (<80%)

```bash
# Check date ranges alignment
# Invoices from April 2025, bookings from August 2025 → no overlap

# Adjust date window:
# src/tmv_recon/etl/recon.py
# DATE_WINDOW_DAYS = 7  # increase to 14
```

**Issue:** High false positives

```bash
# Tighten fuzzy match thresholds:
# CONFIDENCE_THRESHOLD = 0.6  # increase to 0.75
# NAME_SIMILARITY_MIN = 0.7   # increase to 0.8
```

### Voucher Generation Errors

**Issue:** "Ledger not found in catalog"

```bash
# Pull fresh ledger list from Tally
curl -X POST http://20.219.50.8:9000/ \
  -H 'Content-Type: text/xml' \
  --data '@scripts/ledger_list_request.xml' \
  > data/tally/raw_xml/ledgers_current.xml

# Update catalog path in validator
```

**Issue:** "Amount validation failed"

```bash
# Check GST calculation
# Expected: net + cgst + sgst = gross (±₹1)
# If fails, check:
# - GST rate (5% vs 18%)
# - Rounding errors
# - Data quality (nulls, negatives)
```

---

## Performance

### Benchmark (Monthly Batch ~300 Records)

| Component | Time | Records/sec |
|-----------|------|-------------|
| Agoda parser | 45s | 77/s |
| UPI parser | 12s | 365/s |
| Bank parser | 8s | 132/s |
| Matcher | 3s | 100/s |
| Voucher gen | 2s | 150/s |
| **Total** | **70s** | **~4/s** |

### Optimization Tips

- Run parsers in parallel (independent)
- Use `.venv/bin/python -O` for production (skip asserts)
- Increase `BATCH_SIZE` for large datasets
- Cache ledger catalog (don't reload each run)

---

## Error Codes

### Parser Errors

| Code | Meaning | Action |
|------|---------|--------|
| `HEADER_NOT_FOUND` | No recognized columns | Add variant to normalizer |
| `DATE_PARSE_FAILED` | Invalid date format | Add format to parser |
| `AMOUNT_INVALID` | Non-numeric amount | Check source data quality |
| `CORRUPTED_FILE` | Excel read error | Re-download file |

### Matcher Reason Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| `NO_JOIN_KEY` | Missing invoice#/UTR | Add to source data |
| `AMOUNT_MISMATCH` | Amounts don't align | Check commission, GST |
| `DATE_OUT_RANGE` | Dates > 90 days apart | Verify booking vs payment dates |
| `MULTIPLE_CANDIDATES` | 1→many match | Manual review |

### Validation Errors

| Error | Severity | Fix |
|-------|----------|-----|
| `AMOUNT_NOT_BALANCED` | ERROR | Check entry signs |
| `LEDGER_NOT_FOUND` | ERROR | Update catalog or map to Suspense |
| `GST_MISMATCH` | WARNING | Verify rate (5% vs 18%) |
| `NARRATION_TOO_LONG` | ERROR | Truncate to 255 chars |

---

## Maintenance

### Weekly

- Clear temp files: `data/recon/temp/`
- Archive old outputs: `data/recon/archive/`
- Check disk space (canonical CSVs grow ~5MB/month)

### Monthly

- Update ledger catalog from Tally
- Review validation reports for new patterns
- Update parser column mappings as needed
- Backup `imported_vouchers.db`

### Quarterly

- Run ground truth comparison on 3-month sample
- Update fuzzy match thresholds based on accuracy
- Review and clean manual review queue
- Update documentation with new edge cases

---

## Support

**Issues:** https://github.com/anthropics/claude-code/issues (if relevant)

**Logs:**
- Parser: `data/recon/reports/*_validation.csv`
- Matcher: `data/recon/reports/match_summary.txt`
- Validator: `data/recon/reports/validation_summary.txt`

**Tally VM:**
- keysrv status: `curl http://20.219.50.8:9001/info`
- Tally ping: `curl http://20.219.50.8:9000/`
- VM deallocate: `az vm deallocate --resource-group windows-test --name win-test-01`

---

**Last Updated:** 2026-04-29  
**Next Review:** 2026-05-29
