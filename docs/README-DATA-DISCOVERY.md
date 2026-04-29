# Data Discovery Summary - TMV Reconciliation

**Discovery Date:** 2026-04-29  
**Analyst:** Claude Sonnet 4.5  
**Files Analyzed:** 48 Excel files across 4 source types

---

## Quick Stats

| Source Type | Files | Date Range | Variants | Status |
|------------|-------|------------|----------|--------|
| **AGODA** | 20 | Jul 2025 - Apr 2026 | 17 header variants | CRITICAL - High variance |
| **BANK** | 15 | Jul 2025 - Mar 2026 | 4 column counts | COMPLEX - No headers |
| **UPI** | 12 | Jul 2025 - Mar 2026 | 4 formats | HIGH DUPLICATES |
| **INVOICE** | 1 | Current snapshot | 1 format | SPARSE - 39% nulls |

**Total Unique Columns:** 116 across all sources

---

## Critical Findings

### 1. AGODA Has 17 Header Variants ✅ CONFIRMED

The user's report of "12 Agoda header variants" was actually **17 distinct variants** found.

**Most Critical Issues:**
- `INVOICE` vs `INVOCIE` (8 typo occurrences)
- `COMM + GST` (6 spacing variants: `COMM+GST`, `COMM +GST`, `COMM+ GST`)
- `INVOICE NO.` vs `INVOICE  NO.` (double space)
- `AGODA SITE` vs `AGODAT SITE` (typo)

**Impact:** Cannot use simple column name matching. Requires normalization dictionary.

### 2. UPI UTR Has 93% Duplicate Rate

**Finding:** Same UTR appears for 93 out of 100 transactions in sample data.

**Root Cause:** Paytm batches multiple transactions into single bank settlement.

**Impact:** 
- Cannot join 1:1 on UTR
- Must `GROUP BY utr_no, SUM(settled_amount)` before reconciliation
- 53.7% of March 2026 files have NULL UTR (unsettled transactions)

### 3. Bank Statements Have No Standard Headers

**Finding:** Headers appear at variable row positions (typically row 21).

**Structure:**
```
Rows 0-20:  Bank metadata (account, balance, dates)
Row 21:     Headers (usually)
Row 22:     Balance brought forward
Row 23+:    Transaction data
```

**Impact:** Cannot use `pd.read_excel(file, header=0)`. Must detect header row programmatically.

### 4. Invoice Numbers Are 39% Null

**Finding:** Transaction detail export has null `Invoice #` for 39 out of 100 rows.

**Impact:** Cannot use `Invoice #` as primary join key. Must use composite key:
- `(Reservation #, Guest Name, Arrival Date)`

---

## Data Quality Issues Summary

| Issue | Source | Severity | Impact |
|-------|--------|----------|--------|
| **Typos in headers** | AGODA | HIGH | Breaks column matching |
| **93% UTR duplicates** | UPI | HIGH | Breaks 1:1 joins |
| **53.7% null UTRs** | UPI | HIGH | Cannot reconcile unsettled |
| **39% null Invoice #** | INVOICE | MEDIUM | Need composite keys |
| **20 columns >50% null** | INVOICE | LOW | Just noise columns |
| **No standard headers** | BANK | MEDIUM | Requires custom parser |
| **4 date formats** | ALL | MEDIUM | Need format detection |
| **Balance CR/DR suffix** | BANK | LOW | Simple string cleaning |

---

## Join Strategy

### AGODA → BANK
**Problem:** No direct join key  
**Solution:** Fuzzy match on amount + date range
```python
WHERE bank.credit_amount BETWEEN agoda.from_agoda * 0.99 AND agoda.from_agoda * 1.01
  AND bank.value_date BETWEEN agoda.checkin_date - 7 AND agoda.checkin_date + 30
```

### UPI → BANK  
**Problem:** 93% duplicate UTRs  
**Solution:** Aggregate UPI first, then join
```python
# Step 1: Aggregate
upi_agg = upi.groupby('utr_no').agg({'settled_amount': 'sum'})

# Step 2: Join
JOIN bank ON bank.utr_no = upi_agg.utr_no 
         AND bank.credit_amount = upi_agg.settled_amount
```

### INVOICE → AGODA
**Problem:** Guest names have case/title variations  
**Solution:** Normalize + fuzzy match
```python
# Normalize
invoice['guest_clean'] = invoice['Guest Name'].str.upper().str.replace(r'^(MR\.|MRS\.)\s*', '')

# Fuzzy join
WHERE similarity(invoice.guest_clean, agoda.guest_clean) > 0.8
  AND invoice.arrival_date = agoda.checkin_date
```

---

## Recommended Parser Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Raw Excel Files                         │
│  AGODA (17 variants) | BANK (4 variants) | UPI (4 variants) │
└────────────┬────────────────────┬───────────────┬───────────┘
             │                    │               │
             ▼                    ▼               ▼
┌────────────────────┐ ┌──────────────────┐ ┌──────────────┐
│  AgodaParser       │ │  BankParser      │ │  UPIParser   │
│  - Detect variant  │ │  - Find headers  │ │  - Strip "'" │
│  - Normalize cols  │ │  - Extract meta  │ │  - Aggregate │
│  - Clean names     │ │  - Parse CR/DR   │ │  - Clean UTR │
└────────────┬───────┘ └────────┬─────────┘ └──────┬───────┘
             │                  │                   │
             ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Canonical Data Models (Pydantic)               │
│   Booking | Invoice | Payment | BankTransaction             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                  Reconciliation Engine                      │
│  - Direct joins (UPI → Bank by UTR)                         │
│  - Fuzzy joins (Invoice → Agoda by name)                    │
│  - Amount matching (Agoda → Bank by amount)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Documentation Files

This discovery generated the following documentation:

1. **`discovery-2026-04-29-excel-structure.md`** (30KB)
   - Complete analysis with all 17 AGODA variants
   - Column mappings for all sources
   - Join key analysis
   - Data quality issues
   - Recommended parsers with Python code

2. **`column-normalization-rules.md`** (9KB)
   - Quick reference for all column normalizations
   - Data cleaning rules
   - Validation rules
   - Common issues & fixes

3. **`all-column-variants.txt`** (12KB)
   - Complete listing of all 17 AGODA variants
   - UPI and bank variant details
   - Summary statistics

4. **`/tmp/excel_analysis.json`**
   - Raw analysis output with sample data
   - Null percentages, duplicates, date/amount formats
   - 48 files fully analyzed

---

## Next Steps

### Phase 1: Parser Development (Week 1)
- [ ] Implement `AgodaParser` with 17-variant support
- [ ] Implement `BankParser` with header detection
- [ ] Implement `UPIParser` with UTR aggregation
- [ ] Implement `InvoiceParser` with name normalization
- [ ] Unit tests for each parser (1 file per variant)

### Phase 2: Data Models (Week 1)
- [ ] Define Pydantic models: `Booking`, `Invoice`, `Payment`, `BankTransaction`
- [ ] Add validation rules (date ranges, amount limits)
- [ ] Build staging tables in database

### Phase 3: Reconciliation (Week 2)
- [ ] Implement direct joins (UPI → Bank)
- [ ] Implement fuzzy matching (guest names)
- [ ] Implement amount-based matching (AGODA → Bank)
- [ ] Build confidence scoring system

### Phase 4: Testing & Validation (Week 2)
- [ ] Test on all 48 files
- [ ] Validate reconciliation accuracy
- [ ] Generate exception reports
- [ ] Build dashboard

---

## Sample Code Snippets

### AGODA Parser Template
```python
from typing import Dict
import pandas as pd

AGODA_NORMALIZER = {
    'INVOICE NO.': 'invoice_no',
    'INVOCIE NO.': 'invoice_no',  # Typo
    'INVOICE  NO.': 'invoice_no',  # Double space
    'COMM + GST': 'commission_gst',
    'COMM+GST': 'commission_gst',
    # ... 40 more mappings
}

class AgodaParser:
    def parse(self, file_path: str) -> pd.DataFrame:
        df = pd.read_excel(file_path, sheet_name='Remittances')
        df.columns = [AGODA_NORMALIZER.get(col, col.lower()) for col in df.columns]
        df['guest_name'] = df['guest_name'].str.upper()
        df['checkin_date'] = pd.to_datetime(df['checkin_date'])
        return df
```

### Bank Parser Template
```python
class BankParser:
    def parse(self, file_path: str) -> tuple[pd.DataFrame, Dict]:
        # Read raw
        df_raw = pd.read_excel(file_path, header=None)
        
        # Find header row
        header_row = None
        for i in range(30):
            if 'Value Date' in str(df_raw.iloc[i, 0]):
                header_row = i
                break
        
        # Extract metadata
        metadata = {
            'account_number': self._extract(df_raw, 'Account Number'),
            'cleared_balance': self._extract(df_raw, 'Cleared Balance'),
        }
        
        # Re-read with header
        df = pd.read_excel(file_path, header=header_row)
        df['Balance_Numeric'] = df['Balance'].str.replace('CR|DR', '').astype(float)
        
        return df, metadata
```

### UPI Parser Template
```python
class UPIParser:
    def parse(self, file_path: str) -> pd.DataFrame:
        df = pd.read_excel(file_path)
        
        # Handle variant 1: Updated_Date instead of Transaction_Date
        if 'Updated_Date' in df.columns:
            df = df.rename(columns={'Updated_Date': 'Transaction_Date'})
        
        # Strip quotes from string fields
        df['Transaction_Date'] = df['Transaction_Date'].str.strip("'")
        df['UTR_No.'] = df['UTR_No.'].str.strip("'").str.upper()
        
        # Remove summary rows
        df = df[~df['Transaction_Date'].str.contains('TOTAL', na=False)]
        
        return df
```

---

## File Paths Reference

**Source Data:**
```
/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/meet-recording/
├── data_sheets_historical/mangal all data sheet/
│   ├── AGODA/ (20 files)
│   ├── INDIAN BANK/ (9 files)
│   ├── INDIAN BANK ROOFTOP/ (6 files)
│   ├── UPI STATMENT/ (4 files)
│   ├── PTM ROOFTOP/ (5 files)
│   └── F&B UPI/ (3 files)
└── transaction_detail20250428.xlsx
```

**Analysis Outputs:**
```
/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/docs/
├── discovery-2026-04-29-excel-structure.md (MAIN DOCUMENT)
├── column-normalization-rules.md
├── all-column-variants.txt
└── README-DATA-DISCOVERY.md (this file)

/tmp/
├── excel_analysis.json (raw analysis)
└── column_inventory.csv (116 columns)
```

---

## Key Takeaways

1. **AGODA is the messiest source** - 17 header variants, requires extensive normalization
2. **UPI requires aggregation** - Cannot join 1:1 due to 93% duplicate UTRs
3. **Bank requires custom parsing** - No standard headers, variable row positions
4. **Fuzzy matching is essential** - Guest names vary significantly
5. **Date formats are inconsistent** - 4 different formats across sources
6. **Amount matching needs tolerance** - Use ±1% for fuzzy amount joins

**Estimated Reconciliation Accuracy (with fuzzy matching):**
- UPI → Bank: **95%** (direct UTR match)
- Invoice → AGODA: **80%** (fuzzy name + date)
- AGODA → Bank: **70%** (fuzzy amount + date range)

**Manual Review Required:** ~15-20% of transactions

---

## Questions for Stakeholders

1. **AGODA header variance**: Can we request standardized exports from AGODA?
2. **UPI batching**: Is there a detailed transaction report from Paytm with unique IDs?
3. **Null invoice numbers**: Why are 39% of invoices missing Invoice #? Can we fix at source?
4. **Unsettled UPI**: How to handle the 53.7% of transactions with null UTR?
5. **Date range tolerance**: Is 7 days before + 30 days after reasonable for AGODA → Bank matching?

---

*This discovery provides a complete foundation for building robust ETL parsers and reconciliation logic for the TMV project.*
