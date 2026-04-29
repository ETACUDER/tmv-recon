# TMV Reconciliation System - Requirements Document

**Date:** 2026-04-29  
**Phase:** Discovery Phase 1 Complete  
**Sources:** 4 parallel agent analyses (meeting transcripts, Tally vouchers, Excel files, transaction report)

---

## Executive Summary

Reverse-engineered Urvashi's manual Tally posting workflow from 60 actual vouchers, meeting transcripts, and 48 Excel files. System must replicate current patterns exactly to match ground truth (95%+ target).

**Key Findings:**
- 5 voucher types used (Sales 37%, Journal 37%, Purchase 18%, Receipt 5%, Credit Note 3%)
- Single ledger strategy: all OTAs → `Sundry Debtors`, all payments → `CARD / UPI / PAYTM / G PAY`
- Commission & GST currently NOT posted (P&L gap, input credit lost)
- 17 Excel header variants in Agoda files alone
- 60.4% of invoices lack payment settlement tracking
- Join strategy: UTR exact match > amount+date fuzzy > manual review queue

---

## 1. Voucher Types & Posting Patterns

### 1.1 Sales Voucher (37% of volume)

**Purpose:** Customer invoices for room bookings

**XML Tag:** `LEDGERENTRIES.LIST` (NOT `ALLLEDGERENTRIES.LIST`)

**Ledger Pattern:**
```
Dr  Sundry Debtors                     {{gross_amount}}
    Cr  SALE ACCOMODATION GST @ 5%     {{net_amount}}
    Cr  CGST                           {{cgst}}
    Cr  SGST                           {{sgst}}
```

**Sign Convention:**
```xml
<LEDGERENTRIES.LIST>
  <LEDGERNAME>Sundry Debtors</LEDGERNAME>
  <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
  <AMOUNT>{{gross_amount}}</AMOUNT>  <!-- positive = Dr -->
</LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST>
  <LEDGERNAME>SALE ACCOMODATION GST @ 5%</LEDGERNAME>
  <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
  <AMOUNT>-{{net_amount}}</AMOUNT>  <!-- negative = Cr -->
</LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST>
  <LEDGERNAME>CGST</LEDGERNAME>
  <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
  <AMOUNT>-{{cgst}}</AMOUNT>
</LEDGERENTRIES.LIST>
<LEDGERENTRIES.LIST>
  <LEDGERNAME>SGST</LEDGERNAME>
  <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
  <AMOUNT>-{{sgst}}</AMOUNT>
</LEDGERENTRIES.LIST>
```

**Narration Template:**
```
INVOICE NO:-{{invoice_no}} {{GUEST_NAME_UPPERCASE}}
```

**Example:**
```
INVOICE NO:-25-26/6453 MRS. MADHUR PIPARSANIA
```

**Voucher Number Format:** `25-26/####` (fiscal year 2025-26)

**PARTYLEDGERNAME:** `Sundry Debtors`

**GST Rates:**
- Accommodation: 5% (CGST 2.5% + SGST 2.5%)
- Rental income: 18% (CGST 9% + SGST 9%)

**GST Validation:** `net + cgst + sgst = gross` (within ₹1 tolerance)

---

### 1.2 Journal Voucher (37% of volume)

**Purpose:** Payment settlements, salary disbursements, TDS entries, commission postings, adjustments

**XML Tag:** `ALLLEDGERENTRIES.LIST`

**Ledger Pattern (Payment Settlement):**
```
Dr  CARD / UPI / PAYTM / G PAY         {{settled_amount}}
    Cr  Sundry Debtors                 {{settled_amount}}
```

**Sign Convention:**
```xml
<ALLLEDGERENTRIES.LIST>
  <LEDGERNAME>CARD / UPI / PAYTM / G PAY</LEDGERNAME>
  <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
  <AMOUNT>-{{settled_amount}}</AMOUNT>  <!-- negative = Cr -->
</ALLLEDGERENTRIES.LIST>
<ALLLEDGERENTRIES.LIST>
  <LEDGERNAME>Sundry Debtors</LEDGERNAME>
  <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
  <ISPARTYLEDGER>Yes</ISPARTYLEDGER>
  <AMOUNT>{{settled_amount}}</AMOUNT>  <!-- positive = Dr -->
</ALLLEDGERENTRIES.LIST>
```

**Narration Template (Payment):**
```
BEING PAID THROUGH {{PAYMENT_MODE_UPPERCASE}} AGAINST INVOICE NO:{{invoice_no}} {{GUEST_NAME}}
```

**Example:**
```
BEING PAID THROUGH UPI AGAINST INVOICE NO:25-26/5924 JOHN DOE
```

**Voucher Number:** Re-uses invoice number for linkage

**Bill-Wise Reference:** Add `<BILLALLOCATIONS.LIST>` with `<NAME>{{invoice_no}}</NAME>` to link settlement to invoice

**Payment Modes Observed:**
- UPI
- TPP (Third Party Payment)
- TIDY_CARD
- CREDIT_CARD
- DEBIT_CARD
- CASH

**Other Journal Patterns:**
- **TDS Commission:** `PAN NO:-{{pan}}, COMMISSION AMT. - {{amt}}/- @{{rate}}% , TDS- {{tds}}/-`
- **Salary:** `BEING PAID SALARY FOR THE MONTH OF {{MONTH}} {{YEAR}}`
- **Period entries:** `FOR {{DD-MM-YY}} TO {{DD-MM-YY}}`
- **Adjustments:** `CREDIT NOTE-{{N}} ADJUSTMENT`

---

### 1.3 Purchase Voucher (18% of volume)

**Purpose:** Vendor invoices (OTA commissions, security services, stationery)

**XML Tag:** `LEDGERENTRIES.LIST`

**Ledger Pattern:**
```
Dr  {{EXPENSE_LEDGER}}                 {{amount}}
    Cr  {{VENDOR_LEDGER}}              {{amount}}
```

**Observed Expense Ledgers:**
- `COMMISSION PAID`
- `SECURITY SERVICES RCM`
- `PRINTING & STATIONERY EXP`
- `Accounting Charges`

**Observed Vendor Ledgers:**
- `ROVERS NETWORK PVT LTD`
- `MAKE MY TRIP INDIA PVT LTD`
- `SMART EYE SECURITY SERVICE`
- `MADHULATA TELI`

**Narration Pattern:**
```
INVOCIE NO:-{{vendor_invoice_no}} FOR THE MONTH OF {{MONTH}} {{YY}}
INVOICE NO:-{{no}}, [{{DESCRIPTION}}], BASIC AMT -{{amt}}/- TDS @{{rate}}%={{tds}}/- PAN NO-{{pan}}
```

---

### 1.4 Receipt Voucher (5% of volume)

**Purpose:** Bank receipts from payment gateways (Paytm, MakeMyTrip)

**XML Tag:** `ALLLEDGERENTRIES.LIST`

**Ledger Pattern:**
```
Dr  CARD / UPI / PAYTM / G PAY         {{gross}}
    Cr  INDIAN BANK A/C.7223534417     {{net}}
    Cr  ONE 97 COMMUNICATIONS LTD UP   {{fee}}
```

**Narration:** UTR/transaction reference number

---

### 1.5 Credit Note Voucher (3% of volume)

**Purpose:** GST rate adjustment reversals (12% → 5% corrections), rate-change refunds

**XML Tag:** `LEDGERENTRIES.LIST`

**Ledger Pattern:** Reverse of Sales voucher

**Narration:** `GST RATE CHANGE ADJUSTMENT 12% TO 5%`

**Edge Case Trigger:**
- Booking made at old rate, guest arrives after rate change
- Excel notation: `Guest Name (rate*nights)` indicates credit note scenario
- Multi-row Booking IDs (e.g., `5802 5803`) flag this condition

---

## 2. Ledger Catalog (70 Unique Ledgers)

### Primary Ledgers (High Volume)

| Ledger Name | Parent Group | Purpose | Frequency |
|-------------|--------------|---------|-----------|
| **Sundry Debtors** | Current Assets | All customer receivables | 55/60 vouchers |
| **CARD / UPI / PAYTM / G PAY** | Current Assets | All payment modes lumped | 22/60 vouchers |
| **SALE ACCOMODATION GST @ 5%** | Indirect Incomes | Room rental income | 21/60 vouchers |
| **CGST** | Duties & Taxes | GST output tax | 22/60 vouchers |
| **SGST** | Duties & Taxes | GST output tax | 22/60 vouchers |

### Bank Ledgers

- `INDIAN BANK A/C.7223534417` (Hotel main account)
- `Indian Bank MSME LOan Account 787522521`
- `Indian Bank MSME Loan Account 787521107`

### OTA/Vendor Ledgers

- `AGODA SDR` (Sundry Debtor - Agoda)
- `BOOKING.COM SCR` (Sundry Creditor - Booking.com)
- `GOIBIBO / MAKE MY TRIP`
- `MAKE MY TRIP INDIA PVT LTD`
- `ROVERS NETWORK PVT LTD`
- `ONE 97 COMMUNICATIONS LTD UP` (Paytm)
- `PAYTM PAYMENTS SERVICES LTD`

### Expense Ledgers

- `COMMISSION PAID`
- `SALARY TO STAFF`
- `Interest Paid To Indian Bank MSME Loan`
- `Accounting Charges`
- `PRINTING & STATIONERY EXP`
- `SECURITY SERVICES RCM`

### Tax Ledgers

- `TDS PAYABLE`
- `ABC` (tax-related)

### Individual Salary Ledgers (35 employees)

Example: `ANIRUDHA PANDA SSALARY A/C`, `Dinesh Rebari Salary A/c.`

**Note:** Naming inconsistent (all-caps vs sentence case, "SALARY" vs "Salary A/c.")

### Special Ledgers

- `ROUND OFF` (rounding adjustments)

---

## 3. Join Key Strategy

### Stage 1: Exact Match (Confidence 1.0)

| Source A | Source B | Join Key | Success Rate |
|----------|----------|----------|--------------|
| Invoice | Booking | `invoice_no` exact | 85.8% (1201/1399 invoices have invoice_no) |
| Payment | Bank | `utr` exact | 95% (after aggregation) |
| Payment | Invoice | `txn_id` → lookup table | Requires manual mapping (not directly available) |

**Implementation:**
```python
# Invoice ↔ Booking
matches = pd.merge(invoices, bookings, on='invoice_no', how='inner')

# Payment ↔ Bank (aggregate Paytm batches first)
payment_agg = payments.groupby('utr').agg({'settled_amount': 'sum'})
matches = pd.merge(payment_agg, bank, on='utr', how='inner')
```

### Stage 2: Fuzzy Match (Confidence 0.6-0.9)

| Source A | Source B | Join Keys | Tolerance | Success Rate |
|----------|----------|-----------|-----------|--------------|
| Invoice | Booking | guest_name + arrival_date + amount | name: Levenshtein>0.7, date: ±3 days, amt: ±1% | 80% |
| Payment | Invoice | guest_name + txn_date + amount | name: Levenshtein>0.7, date: ±7 days, amt: exact | 70% |
| Booking | Bank | amount + settlement_date | date: ±5 days, amt: ±1% | 70% |

**Name Normalization:**
```python
def normalize_name(name):
    # Remove titles
    name = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.)\s*', '', name, flags=re.I)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    # Title case
    return name.title()
```

**Fuzzy Matching:**
```python
from fuzzywuzzy import fuzz

def fuzzy_match(row_a, row_b):
    name_score = fuzz.ratio(normalize_name(row_a.guest_name), 
                            normalize_name(row_b.guest_name))
    date_match = abs((row_a.date - row_b.date).days) <= 3
    amount_match = abs(row_a.amount - row_b.amount) / row_a.amount < 0.01
    
    if name_score > 80 and date_match and amount_match:
        return 0.9
    elif name_score > 70 and (date_match or amount_match):
        return 0.7
    else:
        return 0.0
```

### Stage 3: Manual Review Queue (Confidence < 0.6)

**Triggers:**
- Missing join keys (`invoice_no` null, `utr` null)
- Amount mismatch > 1%
- Date out of range (> 90 days apart)
- Multiple match candidates (1 payment → 3 invoices with similar amounts)
- Conflict: gross amount in invoice ≠ settled amount in payment

**Output:** `data/recon/unmatched/*.csv` with reason codes

---

## 4. Data Quality Issues & Handling Rules

### 4.1 Excel Header Variants

**AGODA: 17 variants discovered**

**Critical Typos:**
- `INVOICE NO.` vs `INVOCIE NO.` vs `INVOICE  NO.` (4 variants)
- `INVOICE AMT` vs `INVOCIE AMT` vs `invoice amt.` (6 variants)
- `COMM + GST` (6 spacing/case variants)
- `AGODA SITE` vs `AGODAT SITE`

**Normalization Strategy:**
- Build fuzzy column matcher (Levenshtein distance < 2)
- Map all variants to canonical names via lookup table
- Log unrecognized columns as warnings

**Implementation:**
```python
AGODA_NORMALIZER = {
    'INVOICE NO.': 'invoice_no',
    'INVOICE  NO.': 'invoice_no',
    'INVOCIE NO.': 'invoice_no',
    'INVOCIE NO': 'invoice_no',
    # ... (50+ mappings, see excel-structure.md)
}

def normalize_columns(df, source_type):
    df.columns = [AGODA_NORMALIZER.get(c, c.lower().replace(' ', '_')) 
                  for c in df.columns]
    return df
```

### 4.2 Bank Statement Parsing

**Issue:** Headers at row 21 (not row 0), balance suffixes ("CR"/"DR")

**Parser Strategy:**
```python
def parse_bank_statement(filepath):
    # Search for "Value Date" in first 30 rows
    df = pd.read_excel(filepath, header=None)
    header_row = df[df[0] == 'Value Date'].index[0]
    
    # Read again with correct header
    df = pd.read_excel(filepath, header=header_row, skiprows=range(header_row))
    
    # Skip "Balance brought forward" row
    df = df[df['Description'] != 'Balance brought forward']
    
    # Clean balance suffix
    df['Balance'] = df['Balance'].str.replace(' CR', '').str.replace(' DR', '')
    df['Balance'] = pd.to_numeric(df['Balance'])
    
    # Fill blank amounts with 0
    df['Debit Amount'] = pd.to_numeric(df['Debit Amount'], errors='coerce').fillna(0)
    df['Credit Amount'] = pd.to_numeric(df['Credit Amount'], errors='coerce').fillna(0)
    
    return df
```

### 4.3 UPI Duplicate UTRs

**Issue:** 93% duplicate UTR rate (Paytm batches settlements)

**Strategy:** Aggregate by UTR before join
```python
upi_agg = upi_payments.groupby('utr').agg({
    'transaction_amount': 'sum',
    'commission': 'sum',
    'gst': 'sum',
    'settled_amount': 'sum',
    'settled_date': 'first'  # Take earliest date
})
```

### 4.4 Missing Invoice Numbers

**Issue:** 39% of transaction_detail rows lack invoice_no

**Strategy:**
- Fall back to fuzzy match (guest_name + gross_amount + invoice_date)
- Flag as low confidence (< 0.7)
- Output to manual review queue

### 4.5 Date Format Variations

**4 formats observed:**
- `DD/MM/YYYY` (bank statements)
- `YYYY-MM-DD` (transaction detail)
- `DD-MMM-YY` (Agoda)
- Excel serial dates (numeric)

**Normalization:**
```python
def parse_date(date_val):
    if pd.isna(date_val):
        return None
    if isinstance(date_val, (int, float)):  # Excel serial
        return pd.to_datetime('1899-12-30') + pd.Timedelta(days=date_val)
    return pd.to_datetime(date_val, infer_datetime_format=True, errors='coerce')
```

### 4.6 Guest Name Inconsistencies

**Issues:**
- Title variations: `Mr.` vs `MR.` vs `Mr` vs missing
- Case: `JOHN DOE` vs `John Doe` vs `john doe`
- Extra whitespace: `John  Doe` (double space)

**Normalization:** See Stage 2 fuzzy matching above

---

## 5. Edge Cases & Special Handling

### 5.1 Rate Change Credit Notes

**Detection Pattern:**
- Excel notation: `Guest Name (rate*nights)` in processed sheets
- Multi-row Booking IDs: `5802 5803` (same guest, two vouchers)
- `credit_note_for` field populated in Booking model

**Voucher Generation:**
1. Generate Credit Note voucher for original invoice (reverse ledger entries)
2. Generate new Sales voucher at new rate
3. Link via narration: `CREDIT NOTE FOR INVOICE {{original_invoice_no}}, RATE CHANGE`

### 5.2 Partial Payments

**Scenario:** Invoice gross ₹10,000, payment settlement ₹8,000 (commission deducted)

**Current Manual Process:** Post gross amount (₹10,000) in both vouchers, ignore commission

**Automation Strategy:**
- Journal voucher for settled amount (₹8,000)
- Separate Journal voucher for commission expense (₹2,000):
  ```
  Dr  COMMISSION PAID                  ₹2,000
      Cr  CARD / UPI / PAYTM / G PAY   ₹2,000
  ```
- **Flag for Phase 2:** Commission posting currently NOT done manually (gap in workflow)

### 5.3 On-Account Backlog

**Issue:** Payments without matched invoices sit "On Account" in Pending Bills

**Detection:** Query Tally Pending Bills report via HTTP

**Resolution:**
- Re-run fuzzy matcher with relaxed thresholds (name: >0.6, date: ±14 days)
- Output `data/recon/on_account_resolutions.csv` for manual review
- Urvashi confirms, then generate Journal vouchers with bill-wise allocations

### 5.4 Delayed OTA Settlements

**Scenario:** Guest check-in Aug, OTA settlement hits bank Sept

**Current Manual Process:** Post based on bank settlement date (Sept)

**Automation:** Use `settlement_date` from bank statement as voucher date, not `invoice_date`

### 5.5 Multi-Invoice OTA Settlements

**Scenario:** Single Agoda settlement file contains 20 invoices across Aug-Sept

**Strategy:**
- Parse settlement file into individual booking rows
- Match each booking to invoice via `booking_id` or fuzzy
- Generate one Journal voucher per invoice (NOT one lump voucher)

### 5.6 GST Rate Ambiguity

**Meeting Context:** "12% above ₹7500/night, but we only see 5% in data"

**Resolution:** Use GST rate from income ledger name:
- `SALE ACCOMODATION GST @ 5%` → 5%
- `RENTAL INCOME GST @ 18%` → 18%

If ledger name doesn't specify, calculate from invoice data:
```python
gst_rate = ((cgst + sgst) / net_amount) * 100
```

### 5.7 Three Operating Units (Hotel, Rooftop, F&B)

**Current State:** All post to same Sundry Debtors ledger (no split)

**Phase 1 Strategy:** Match current behavior (single ledger)

**Phase 2 Consideration:** Add unit dimension to ledger names:
- `Sundry Debtors - Hotel`
- `Sundry Debtors - Rooftop`
- `Sundry Debtors - F&B`

---

## 6. Validation Rules

### Pre-Voucher Generation

| Check | Rule | Action if Failed |
|-------|------|------------------|
| Amount balance | `sum(AMOUNT) = 0` for voucher | ERROR, block generation |
| GST calculation | `net + cgst + sgst = gross` (±₹1) | WARNING, flag for review |
| Ledger exists | All ledgers in 70-ledger catalog | ERROR, map to `Suspense A/c` |
| Date sanity | `booking_date ≤ arrival ≤ departure ≤ settlement` | WARNING, flag |
| Invoice# format | Matches `^\d{2}-\d{2}/\d{4,5}$` | ERROR, reject |
| Narration length | < 255 characters (Tally limit) | ERROR, truncate |

### Post-XML Generation

| Check | Rule | Action if Failed |
|-------|------|------------------|
| XML well-formed | Parse with `xml.etree.ElementTree` | ERROR, halt |
| Envelope structure | `<ENVELOPE><HEADER><BODY><DATA>` hierarchy | ERROR, halt |
| ISDEEMEDPOSITIVE | All entries have this field | ERROR, halt |
| Duplicate voucher | Check `imported_vouchers.db` by (date, ref, amount) | SKIP, log |

### Ground Truth Comparison

| Metric | Target | Measurement |
|--------|--------|-------------|
| Voucher type match | 95%+ | Generated type = actual type |
| Ledger name match | 100% | Exact string match |
| Amount match | 98%+ | Within ₹1 tolerance |
| Narration pattern | 95%+ | Regex match, not exact string |

---

## 7. Transaction Report Bridge (Partial Data)

### File: `transaction_detail20250428.xlsx`

**Coverage:**
- 1,399 rows, 55 columns
- Date range: April 2025 only (28 days)
- 85.8% have invoice_no
- 39.6% have settlement tracking

**What It Bridges:**
- ✅ Booking → Invoice (via `Reservation #`, `Travel Agent Voucher #`)
- ✅ Invoice → Payment Mode (via `Settlement/Particular`)
- ❌ Invoice → Payment Transaction ID (NO `txn_id`, `order_id`, `utr` fields)

**Join Strategy:**
```python
# Invoice exact match
invoices_enriched = pd.merge(
    invoices, 
    transaction_detail[['Invoice #', 'Business Source', 'Settlement/Particular']], 
    left_on='invoice_no', 
    right_on='Invoice #', 
    how='left'
)

# Booking fuzzy match
booking_matches = []
for _, inv in invoices_enriched.iterrows():
    if pd.isna(inv['Business Source']):
        # Fall back to fuzzy match on guest name + date
        candidates = transaction_detail[
            (transaction_detail['Guest Name'].apply(normalize_name) == normalize_name(inv.guest_name)) &
            (abs((transaction_detail['Invoice date'] - inv.invoice_date).dt.days) <= 3)
        ]
        if len(candidates) == 1:
            booking_matches.append((inv.invoice_no, candidates.iloc[0]['Reservation #']))
```

**Limitation:** Cannot directly link to `canonical/payment.csv` (no txn_id). Must use amount + date + guest fuzzy match.

---

## 8. CLI Implementation

### Discovery Command (One-Time, Completed)

```bash
tmv-recon-discover --output docs/discovery-2026-04-29-requirements.md
```
**Status:** ✅ COMPLETE (this document)

### Production ETL Commands

```bash
# Extract canonical data
tmv-recon-extract \
  --agoda "data/booking/raw/AGODA*.xlsx" \
  --invoices "meet-recording/transaction_detail20250428.xlsx" \
  --upi "data/payments/raw/PTM*.xlsx" \
  --bank "data/payments/raw/INDIAN_BANK*.xlsx" \
  --output-dir "data/recon/canonical/"

# Match across streams
tmv-recon-match \
  --canonical-dir "data/recon/canonical/" \
  --output-dir "data/recon/matches/" \
  --confidence-threshold 0.6

# Generate Tally vouchers
tmv-recon-generate \
  --matches-dir "data/recon/matches/" \
  --output-dir "data/recon/output/" \
  --tally-company "THE MANGAL VIEW RESIDENCY Final" \
  --validate

# Ground truth test
tmv-recon-test \
  --baseline "data/tally/raw_xml/daybook_FY25-26.xml" \
  --generated "data/recon/output/" \
  --report "data/recon/reports/ground_truth_diff.csv"
```

---

## 9. Implementation Priorities

### Phase 1A: Core Extractors (Week 1)
1. Agoda parser with 17-variant normalization
2. Bank statement parser with row-21 header detection
3. UPI parser with UTR aggregation
4. Transaction detail parser (already exists, enhance)

### Phase 1B: Matchers (Week 1-2)
1. Exact match on invoice_no, utr
2. Fuzzy match on guest_name + amount + date
3. Manual review queue generation

### Phase 1C: Voucher Generators (Week 2)
1. Sales voucher (LEDGERENTRIES.LIST, GST splits)
2. Journal voucher (ALLLEDGERENTRIES.LIST, bill-wise ref)
3. Template engine with discovered narration patterns

### Phase 1D: Validation & Testing (Week 2-3)
1. Pre-flight validation (amount balance, ledger exists)
2. XML well-formedness checks
3. Ground truth comparison (60 vouchers)
4. Integration test (POST to Tally VM)

### Phase 2: Enhancement (Month 2)
1. Commission expense posting (currently gap)
2. On-account backlog resolver
3. Rate-change credit note detector
4. Multi-unit ledger split

---

## 10. Success Metrics

**Acceptance Criteria:**
- [ ] Parse all 48 Excel files without errors
- [ ] Match rate > 95% (invoice ↔ booking, payment ↔ bank)
- [ ] Generate 60 vouchers matching ground truth structure (95%+ similarity)
- [ ] All XMLs import to Tally without errors (`IMPORTRESULT.ERRORS = 0`)
- [ ] Processing time < 5 minutes for monthly batch (~300 records)
- [ ] Unmatched rate < 5% (flagged for manual review)

**Business Impact:**
- Urvashi's manual entry time: 4 hours/month → 30 minutes/month (87.5% reduction)
- Error rate: < 1% (incorrect vouchers)
- Commission data captured (currently lost)
- Audit trail complete (UTR, payment mode, bank details preserved)

---

## Appendix: Quick Reference

### Voucher Type Decision Tree

```
IF record_type == 'invoice':
    → Sales Voucher (LEDGERENTRIES.LIST)
    
IF record_type == 'payment':
    → Journal Voucher (ALLLEDGERENTRIES.LIST) with bill-wise ref
    
IF record_type == 'rate_change_refund':
    → Credit Note Voucher (LEDGERENTRIES.LIST)
    
IF record_type == 'vendor_invoice':
    → Purchase Voucher (LEDGERENTRIES.LIST)
    
IF record_type == 'bank_receipt':
    → Receipt Voucher (ALLLEDGERENTRIES.LIST)
```

### Sign Convention Lookup

| ISDEEMEDPOSITIVE | Amount Sign | Accounting Side |
|------------------|-------------|-----------------|
| Yes | Negative | Credit |
| Yes | Positive | Debit |
| No | Positive | Debit |
| No | Negative | Credit |

### Join Key Priority

1. `invoice_no` (exact) - 85.8% coverage
2. `utr` (exact) - 95% coverage (after aggregation)
3. `guest_name + amount + date` (fuzzy, Levenshtein > 0.7) - 70-80% coverage
4. Manual review queue - remainder

---

**Document Status:** ✅ DISCOVERY COMPLETE  
**Next Step:** Proceed to Phase 2 (Production ETL implementation)
