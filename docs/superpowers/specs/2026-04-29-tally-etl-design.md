# Tally ETL Reconciliation System - Design Spec

**Date:** 2026-04-29  
**Project:** tmv-recon  
**Scope:** The Mangal View Residency hotel reconciliation automation  
**Goal:** Automate Urvashi's manual process - raw Excel → matched vouchers → Tally-importable XML

---

## Overview

Replace manual data entry with automated ETL that replicates current Tally posting workflow. Takes monthly/ad-hoc Excel exports (bookings, invoices, payments) → matches across streams → generates Tally XML vouchers matching existing structure.

**Two-phase approach:**
1. **Discovery Phase (one-time):** Reverse-engineer current manual process from evidence
2. **Production Phase (recurring):** Automated ETL matching discovered patterns

---

## Architecture

### Phase 1: Discovery (One-Time, ~2-4 hours)

**Purpose:** Analyze evidence to understand Urvashi's current Tally posting workflow.

**Method:** Spawn 4 parallel agents to extract requirements from:

1. **Meeting transcripts** (`meet-recording/141551856/`)
   - Extract workflow steps
   - Business rules (which OTA → which ledger)
   - Commission/GST handling
   - Edge cases (rate changes, credit notes, on-account)

2. **Tally Day Book vouchers** (`data/tally/raw_xml/daybook_FY25-26.xml`, 60 vouchers)
   - Voucher type breakdown (Sales: 22, Journal: 22, Purchase: 11, Receipt: 3, Credit Note: 2)
   - Ledger name catalog with parent groups
   - Narration format patterns ("RENT/MARCH26", "INVOICE NO -...")
   - Amount sign conventions (ISDEEMEDPOSITIVE mapping)
   - GST split patterns (CGST + SGST rates)

3. **Raw Excel files** (`data/{booking,invoices,payments}/raw/`)
   - Column mappings per source (Agoda 12 header variants, PTM 123 columns, EZ folios)
   - Join key candidates (invoice_no, UTR, amount+date, guest_name)
   - Missing data patterns
   - Date format variations

4. **Transaction report** (hunt across all Excel files)
   - Locate EZee transaction/folio report
   - Bridge data: invoice# + booking channel + payment details
   - Column structure

**Output:** Single **Requirements Document** synthesizing all findings:
- Discovered voucher types and ledger mappings
- Narration templates with placeholders
- Join key strategy (exact match priority, fuzzy fallback)
- Data quality issues and handling rules
- Edge case patterns (credit notes, rate changes, partial payments)

**Location:** `docs/discovery-2026-04-29-requirements.md`

---

### Phase 2: Production ETL (Recurring)

**Trigger:** Monthly dumps or ad-hoc Excel files dropped into `data/{booking,invoices,payments}/raw/`

#### **1. Extract Layer**

**Input:** Raw Excel/CSV files  
**Process:**
- Auto-detect source type (Agoda vs GoMT, EZee invoice vs transaction report, PTM vs Bank)
- Parse using discovered column mappings from Requirements Doc
- Handle header variants (normalize "Guest Name" / "GuestName" / "GUEST_NAME")
- Normalize dates (multiple formats → YYYY-MM-DD)
- Normalize amounts (remove commas, handle negatives)
- Clean guest names (title case, trim whitespace)

**Output:** Canonical models (`etl/models.py` dataclasses)
- `data/recon/canonical/bookings.csv` → `Booking` records
- `data/recon/canonical/invoices.csv` → `Invoice` records  
- `data/recon/canonical/payments.csv` → `Payment` records

**Existing code:** `src/tmv_recon/etl/extract/{booking,invoice,payment}.py` (enhance with discovered patterns)

---

#### **2. Transform Layer (Matcher)**

**Input:** Canonical CSV files  
**Process:** Match records across streams using discovered join key strategy

**Stage 1 - Exact Matches:**
- invoice_no exact match (booking ↔ invoice)
- UTR exact match (payment ↔ bank, payment ↔ booking settlement)
- Confidence: 1.0

**Stage 2 - Fuzzy Matches:**
- Amount + date window (±3 days)
- Guest name similarity (Levenshtein > 0.8)
- Confidence: 0.6 - 0.9 (scored)

**Stage 3 - Manual Review Queue:**
- Low confidence (< 0.6)
- Conflicts (1 payment → multiple invoices, amount mismatch)
- Missing join keys

**Output:**
- `data/recon/matches/booking_invoice.csv` → `Match` records
- `data/recon/matches/payment_invoice.csv` → `Match` records
- `data/recon/unmatched/{bookings,invoices,payments}.csv` (with reason codes)

**Existing code:** `src/tmv_recon/etl/recon.py` (enhance with discovered join strategy)

---

#### **3. Load Layer (Voucher Generator)**

**Input:** Match records + canonical data  
**Process:** Generate Tally vouchers using discovered templates from Requirements Doc

**Voucher Types (examples, actual types discovered in Phase 1):**

**Sales Voucher** (per matched invoice):
```xml
<VOUCHER VCHTYPE="Sales" ACTION="Create">
  <DATE>20260331</DATE>
  <VOUCHERNUMBER>INV-25-26/0304</VOUCHERNUMBER>
  <NARRATION>INVOICE NO - 25-26/0304, Guest: {{guest_name}}</NARRATION>
  <PARTYLEDGERNAME>{{ota_ledger}}</PARTYLEDGERNAME>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>{{ota_ledger}}</LEDGERNAME>  <!-- e.g., "AGODA COMPANY PTE LTD" -->
    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
    <AMOUNT>{{gross_amount}}</AMOUNT>  <!-- positive = credit -->
  </ALLLEDGERENTRIES.LIST>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>Sales - Room Rent</LEDGERNAME>
    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
    <AMOUNT>-{{net_amount}}</AMOUNT>  <!-- negative = debit -->
  </ALLLEDGERENTRIES.LIST>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>CGST</LEDGERNAME>
    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
    <AMOUNT>-{{cgst}}</AMOUNT>
  </ALLLEDGERENTRIES.LIST>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>SGST</LEDGERNAME>
    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
    <AMOUNT>-{{sgst}}</AMOUNT>
  </ALLLEDGERENTRIES.LIST>
</VOUCHER>
```

**Journal Voucher** (per matched payment):
```xml
<VOUCHER VCHTYPE="Journal" ACTION="Create">
  <DATE>{{settlement_date}}</DATE>
  <VOUCHERNUMBER>JNL-{{date}}-{{seq}}</VOUCHERNUMBER>
  <NARRATION>{{payment_mode}} settlement, UTR: {{utr}}, Ref: {{invoice_no}}</NARRATION>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>CARD / UPI / PAYTM / G PAY</LEDGERNAME>
    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
    <AMOUNT>-{{settled_amount}}</AMOUNT>
  </ALLLEDGERENTRIES.LIST>
  <ALLLEDGERENTRIES.LIST>
    <LEDGERNAME>{{ota_ledger}}</LEDGERNAME>
    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
    <AMOUNT>{{settled_amount}}</AMOUNT>
  </ALLLEDGERENTRIES.LIST>
</VOUCHER>
```

**Templates filled from Requirements Doc patterns.**

**Output:**
- `data/recon/output/sales_vouchers_YYYY-MM-DD.xml`
- `data/recon/output/journal_vouchers_YYYY-MM-DD.xml`
- `data/recon/output/credit_note_vouchers_YYYY-MM-DD.xml` (if rate changes discovered)
- `data/recon/output/recon_report_YYYY-MM-DD.csv` (all matches + confidence scores)

**Existing code:** 
- `src/tmv_recon/tally/xml.py` (voucher XML generation)
- `src/tmv_recon/tally/models.py` (Voucher, LedgerEntry dataclasses)
- New: voucher template engine applying discovered patterns

---

#### **4. Validation Layer**

**Checks:**
- Voucher amounts balance to zero (sum of all AMOUNT fields)
- All ledger names exist in Tally's 440-ledger catalog (`data/tally/raw_xml/ledgers.xml`)
- Narration format matches discovered patterns (regex validation)
- Date sanity: booking_date ≤ arrival_date ≤ departure_date
- Amount sanity: net + CGST + SGST = gross (within ₹1 tolerance)
- Outlier detection: amount > 3σ, flag for review

**Output:**
- `data/recon/reports/validation_errors_YYYY-MM-DD.csv` (severity: ERROR, WARNING, INFO)
- Block XML generation if ERROR-level issues exist
- Proceed with WARNINGs but flag in report

---

## Error Handling & Edge Cases

### Duplicate Detection
- Query Tally Day Book via HTTP for vouchers in date range
- Check local SQLite ledger: `data/recon/imported_vouchers.db` (date, reference, amount)
- Skip vouchers already imported
- If re-running same month, only process new records

### Missing Data Handling
| Missing Field | Strategy |
|---|---|
| invoice_no | Fall back to fuzzy match (amount + date + guest), confidence < 0.7 |
| GST split | Calculate from gross using discovered rate (12% or 5% from Requirements) |
| ledger name | Map to "Suspense A/c", add to manual review queue |
| payment settlement_date | Use txn_date as fallback |
| guest_name | Use "Guest - {{invoice_no}}" as placeholder |

### Unmatched Records
- Output separate CSV per stream: `data/recon/unmatched/{bookings,invoices,payments}.csv`
- Include reason code:
  - `NO_JOIN_KEY` - missing invoice_no/UTR
  - `AMOUNT_MISMATCH` - amounts don't align within tolerance
  - `DATE_OUT_RANGE` - booking/payment date > 90 days apart
  - `DUPLICATE` - already imported
- Urvashi reviews, fixes source data, re-runs

### Conflict Resolution
| Conflict | Strategy |
|---|---|
| 1 payment → multiple invoices | Split payment proportionally, create separate Journal vouchers |
| 1 invoice → multiple payments | One Sales voucher, multiple Journal vouchers for each payment |
| Rate change credit notes | Generate Credit Note voucher (pattern discovered from Agoda credit_note_for field) |
| Partial payment | Create voucher for settled amount, flag remainder as pending in report |

### Data Quality Checks (Pre-Validation)
- Amount validation: `booking.net_settled + commission + commission_gst + tcs - tds = gross_amount`
- Date validation: `booking_date ≤ arrival_date ≤ departure_date ≤ settlement_date`
- Name consistency: `fuzzy_match(booking.guest_name, invoice.guest_name) > 0.7`
- All issues logged with severity

---

## Testing Strategy

### Ground Truth Comparison
- **Baseline:** 60 existing Tally vouchers (March 2026, Day Book)
- **Test:** Re-run ETL on same date range using source Excel files
- **Compare:**
  - Voucher type (Sales vs Journal vs Credit Note)
  - Ledger names (exact match)
  - Amounts (within ₹1 tolerance for rounding)
  - Narration pattern (regex match, not exact string)
- **Report:** `data/recon/reports/ground_truth_diff_YYYY-MM-DD.csv`
- **Target:** 95%+ structural match

### Unit Tests
| Component | Test |
|---|---|
| Parsers | Each Excel format → canonical model with known input/output |
| Matchers | Known booking + invoice → expected Match with correct confidence |
| Voucher generator | Match → XML with correct sign conventions (ISDEEMEDPOSITIVE) |
| Ledger validator | All generated ledger names exist in Tally's 440-ledger catalog |
| Amount balancer | Voucher entries sum to zero |

**Location:** `tests/test_etl_production.py` (new)

### Integration Test
- **End-to-end:** Drop sample Excel files → run full pipeline → validate XML output
- **XML validation:** Parse with `xml.etree.ElementTree`, check envelope structure
- **Tally dry-run:** POST to test company on Azure VM, parse IMPORTRESULT response
- **Expected:** `<CREATED>N</CREATED>`, `<ERRORS>0</ERRORS>`

### Acceptance Criteria
- [ ] 95%+ of generated vouchers match ground truth structure
- [ ] All XMLs pass Tally import without errors (IMPORTRESULT.ERRORS = 0)
- [ ] Unmatched rate < 5% (flagged for manual review)
- [ ] Processing time < 5 minutes for monthly batch (~300 records)
- [ ] Validation errors logged with actionable reason codes

### Manual Review Phase (First 2 Months)
- Urvashi reviews `recon_report_YYYY-MM-DD.csv` before importing XML
- Feedback loop: Track her corrections in `data/recon/feedback/urvashi_edits.csv`
- Adjust matchers/templates based on correction patterns
- Track accuracy improvement: `match_rate_week_N.csv`

---

## Implementation Notes

### Reuse Existing Code
- `src/tmv_recon/etl/models.py` - Booking, Invoice, Payment, Match dataclasses ✓
- `src/tmv_recon/etl/extract/` - parser framework ✓
- `src/tmv_recon/tally/xml.py` - XML generation ✓
- `src/tmv_recon/tally/models.py` - Voucher, LedgerEntry ✓
- `src/tmv_recon/parsers/{excel,pdf}.py` - file readers ✓

### New Components Needed
- `src/tmv_recon/etl/discovery/` - parallel agent orchestrator
- `src/tmv_recon/etl/templates.py` - voucher template engine (applies discovered patterns)
- `src/tmv_recon/etl/validator.py` - pre-flight checks
- `src/tmv_recon/etl/dedup.py` - SQLite ledger for imported vouchers
- `tests/test_etl_production.py` - full integration test

### CLI Commands
```bash
# Discovery phase (one-time)
tmv-recon-discover --output docs/discovery-2026-04-29-requirements.md

# Production ETL (recurring)
tmv-recon-etl \
  --bookings data/booking/raw/*.xlsx \
  --invoices data/invoices/raw/*.xlsx \
  --payments data/payments/raw/*.xlsx \
  --output-dir data/recon/output/ \
  --validate

# Ground truth comparison
tmv-recon-test --date-range 2026-03-01:2026-03-31
```

### Dependencies
- Existing: `pandas`, `openpyxl`, `pdfplumber`, `anthropic`, `google-generativeai`
- New: `sqlite3` (stdlib), `fuzzywuzzy` (string matching), `pytest` (tests)

---

## Out of Scope (Future Enhancements)

- Auto-push to Tally via HTTP (manual import for now)
- Two-way sync (Tally → verification report against Excel)
- Multi-company support (TMV only initially)
- Real-time processing (batch only)
- Web UI for match review (CSV review initially)
- Historical data migration (FY25-26 forward only)

---

## Success Metrics

**Week 1:** Discovery complete, Requirements Doc validated by Urvashi  
**Week 2:** ETL pipeline functional, passes ground truth comparison (95%+ match)  
**Week 3:** First production run, Urvashi reviews output, provides feedback  
**Week 4:** Refinements based on feedback, accuracy > 97%  
**Month 2:** Urvashi imports XML directly without manual edits

**Long-term:** 
- Urvashi's manual entry time: 4 hours/month → 30 minutes/month (review only)
- Error rate: < 1% (unmatched or incorrect vouchers)
- Processing time: < 5 minutes per monthly batch

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Discovery finds inconsistent manual process | Document variations, choose most common pattern, flag exceptions |
| Excel formats change mid-project | Build flexible parser with column fuzzy matching |
| Tally vouchers don't match any discoverable pattern | Fallback: Interview Urvashi directly for clarification |
| Matching rules too strict (high unmatched rate) | Tune confidence thresholds, add fuzzy fallback stages |
| Matching rules too loose (false positives) | Ground truth comparison catches this, tighten rules |
| Data quality worse than expected | Extensive validation layer, clear error reports |

---

## Appendix: Key Files Reference

**Evidence for Discovery:**
- `meet-recording/141551856/141551856_transcript.md` - meeting transcript
- `meet-recording/141551856/tally-recon-todo.md` - action items
- `data/tally/raw_xml/daybook_FY25-26.xml` - 60 actual vouchers
- `data/tally/raw_xml/ledgers.xml` - 440 ledger catalog
- `data/booking/raw/`, `data/invoices/raw/`, `data/payments/raw/` - source files

**Documentation:**
- `docs/tally-integration.md` - XML schema, sign conventions
- `docs/handover-2026-04-29.md` - Tally VM setup, data pull process
- `README.md` - current ETL pipeline overview

**Existing ETL Code:**
- `src/tmv_recon/etl/README.md` - ETL spec
- `src/tmv_recon/etl/_flow.md` - recon flow diagram
- `src/tmv_recon/etl/models.py` - canonical dataclasses
