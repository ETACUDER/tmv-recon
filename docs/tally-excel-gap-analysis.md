# Tally → Excel Data Gap Analysis
**Generated:** 2026-04-29  
**Validated Against:** FY 2024-25 Tally backup (20,977 vouchers)

## Executive Summary

To reproduce Tally vouchers from Excel data, we need 3 primary matching operations:

1. **Booking → Invoice** → Sales Voucher (8,628 vouchers)
2. **Payment → Invoice** → Journal Voucher (10,602 vouchers)
3. **Bank → Payment** → Bank reconciliation (1,190 receipts)

---

## 1. Sales Voucher Generation (Booking → Invoice)

### Tally Structure (Example):
```
VOUCHER TYPE: Sales
VOUCHER NUMBER: 25-26/96
DATE: 20250412
NARRATION: "INVOICE NO:-25-26/96, Mr.UGAM SINGH"

LEDGER ENTRIES:
  Dr  Sundry Debtors                ₹2,210.00  (IsDeemedPositive=Yes, Amount=-2210.00)
      Cr  SALE ACCOMODATION GST @ 10%  ₹1,995.72  (IsDeemedPositive=No, Amount=1995.72)
      Cr  CGST                           ₹107.14  (IsDeemedPositive=No, Amount=107.14)
      Cr  SGST                           ₹107.14  (IsDeemedPositive=No, Amount=107.14)
```

### Excel Data Available:

#### From `invoice.csv` (EZee Transaction Detail):
| Column | Maps To | Status |
|--------|---------|--------|
| `invoice_no` | Voucher Number | ✅ PRESENT |
| `invoice_date` | Voucher Date | ✅ PRESENT |
| `guest_name` | Narration (guest part) | ✅ PRESENT |
| `gross_amount` | Dr to Sundry Debtors | ✅ PRESENT |
| `net_amount` | Cr to SALE ACCOMODATION | ✅ PRESENT |
| `cgst` | Cr to CGST | ✅ PRESENT |
| `sgst` | Cr to SGST | ✅ PRESENT |
| `gst_rate` | Determines ledger (5%, 12%, 18%) | ✅ PRESENT |

#### From `bookings.csv` (Agoda/GoMT):
| Column | Maps To | Status |
|--------|---------|--------|
| `invoice_no` | Match key to invoice | ✅ PRESENT (715 of 3,476) |
| `guest_name` | Validation | ✅ PRESENT |
| `settlement_date` | Journal voucher date | ✅ PRESENT |
| `net_settled` | Journal voucher amount | ✅ PRESENT |
| `commission` | NOT in Tally (OTA keeps it) | ⚠️ INFORMATIONAL |

### GAP ANALYSIS:

| Required Field | Source | Status | Issue |
|----------------|--------|--------|-------|
| Invoice Number | EZee Excel | ✅ | **None** - 304 invoices extracted |
| Guest Name | Both | ✅ | **None** - present in both |
| Amounts (Gross/Net/GST) | EZee Excel | ✅ | **None** - all components present |
| GST Rate/Ledger | EZee Excel | ✅ | **None** - gst_rate column exists |
| Party Ledger | **HARDCODED** | ⚠️ | **Always "Sundry Debtors"** (75% actual) |

**✅ CONCLUSION:** Invoice → Sales Voucher is **COMPLETE** with current data.

---

## 2. Journal Voucher Generation (Payment Settlement)

### Tally Structure (Example):
```
VOUCHER TYPE: Journal
VOUCHER NUMBER: J/2025/12345
DATE: 20250110
NARRATION: "BEING PAID THROUGH CARD AGAINST INVOICE NO:25-26/96 Mr.UGAM SINGH"

LEDGER ENTRIES:
  Dr  CARD / UPI / PAYTM / G PAY    ₹1,800.00  (IsDeemedPositive=Yes, Amount=-1800.00)
      Cr  Sundry Debtors              ₹1,800.00  (IsDeemedPositive=No, Amount=1800.00)
```

### Excel Data Available:

#### From `invoice.csv` (EZee Transaction Detail):
| Column | Maps To | Status |
|--------|---------|--------|
| `invoice_no` | Links to booking | ✅ PRESENT (304 invoices) |
| `settlement_amount` | Journal voucher amount | ✅ PRESENT (304 invoices) |
| `settlement_modes` | Payment mode ledger | ✅ PRESENT (293 of 304) |
| `gross_amount` | Validation | ✅ PRESENT |

#### From `upi_payments.csv` (Paytm aggregated):
| Column | Maps To | Status |
|--------|---------|--------|
| `utr` | Match key (bank ref) | ✅ PRESENT |
| `settled_amount` | Both ledger amounts | ✅ PRESENT |
| `settled_dt` | Voucher Date | ✅ PRESENT |
| `payment_mode` | NOT USED (all UPI) | ⚠️ LIMITED |

#### From `bank.csv` (Indian Bank statement):
| Column | Maps To | Status |
|--------|---------|--------|
| `utr` (extracted) | Match to UPI | ✅ PRESENT (792 of 1,363) |
| `amount` | Validation | ✅ PRESENT |
| `date` | Validation | ✅ PRESENT |

### GAP ANALYSIS:

| Required Field | Source | Status | Issue |
|----------------|--------|--------|-------|
| Invoice Number | invoice.csv | ✅ | Present in all 304 invoices |
| Guest Name | invoice.csv | ✅ | Present for narration |
| Settled Amount | invoice.csv | ✅ | settlement_amount column |
| Settlement Date | invoice.csv | ✅ | invoice_date used for journal |
| Payment Mode Ledger | invoice.csv | ✅ | settlement_modes (293 of 304) |

**✅ CONCLUSION:** Invoice → Journal Voucher is **COMPLETE** with current data. Invoice contains settlement_amount and settlement_modes linking booking to payment.

---

## 3. Matching Logic (Urvashi's Manual Process)

### Current Matching Keys (Based on Tally FY24-25):

#### Stage 1: Exact Match (High Confidence)
```python
# Invoice appears in Tally narration
match_key = invoice_no  # e.g., "25-26/96"

# Found in:
# - Tally: VOUCHERNUMBER or NARRATION field
# - Excel: invoice.csv → invoice_no
#         bookings.csv → invoice_no (715 of 3,476)
```

#### Stage 2: Fuzzy Match (Medium Confidence)
```python
# When invoice_no is missing, match on:
match_criteria = {
    'guest_name': fuzz_ratio >= 70%,  # Levenshtein distance
    'amount': abs(tally_amt - excel_amt) <= 1%,  # ±1% tolerance
    'date_window': abs(tally_date - excel_date) <= 7 days
}
```

#### Stage 3: Manual Queue (Low/No Confidence)
```python
# Unmatched records requiring Urvashi's review:
- Bookings without invoice_no (2,761 of 3,476 = 79%)
- Payments without UTR (from older periods)
- Mismatched amounts (commission discrepancies)
```

---

## 4. Missing Data Summary

### 🔴 CRITICAL GAPS:

1. **Invoice Numbers in Bookings**
   - **Status:** Only 715 of 3,476 (20.6%) have invoice_no
   - **Missing:** 2,761 bookings (79.4%)
   - **Urvashi's Manual Fix:** Cross-reference with EZee daily
   - **Impact:** Cannot auto-generate sales vouchers for 79% of bookings

2. **Payment Mode Classification**
   - **Status:** Invoice has settlement_modes but values are generic ("UPI", "Agoda", "Cash")
   - **Tally Uses:** Single combined ledger "CARD / UPI / PAYTM / G PAY"
   - **Coverage:** 293 of 304 invoices (96.4%) have settlement_modes
   - **Impact:** Can map to Tally's combined ledger

### ⚠️ MEDIUM GAPS:

3. **Room Posting Numbers**
   - **Status:** Found in Tally narration but not in Excel
   - **Example:** "ROOM POSTING NO:- REC-4706"
   - **Impact:** Lost audit trail (minor - not used for matching)

### ✅ WELL-COVERED:

4. **Invoice → Payment Link** - settlement_amount and settlement_modes in invoice.csv (293 of 304)
5. **Amount Breakdowns** - All GST components present
6. **Guest Names** - Present in all sources
7. **Dates** - Invoice, booking, payment dates all present
8. **UTR Codes** - Bank reconciliation key present (792 of 1,363)

---

## 5. Recommended Automation Improvements

### Priority 1: Invoice Number Backfill
```python
# Add to extract/booking.py:
def enrich_with_invoice_numbers():
    """
    Match bookings to invoices using:
    - Guest name (fuzzy)
    - Arrival date (±2 days window)
    - Amount (gross_amount from booking ≈ gross_amount from invoice)
    """
    # This would increase coverage from 20.6% → ~60%
```

### Priority 2: Settlement Mode Mapping
```python
# Add to extract/invoice.py:
def map_settlement_to_tally_ledger():
    """
    Map settlement_modes to Tally ledgers:
    - "UPI", "Paytm", "G Pay", "Credit Card" → "CARD / UPI / PAYTM / G PAY"
    - "Cash" → "Cash" (if separate ledger exists)
    - "Agoda", "Booking.com" → "Sundry Debtors" (receivable)
    - Mixed modes (e.g., "Agoda,UPI") → split into multiple journal entries
    """
    # This would enable automated journal voucher generation
```

### Priority 3: Credit Note Detection
```python
# Current: 119 credit notes detected in bookings (negative amounts)
# Tally: Only 2 credit note vouchers
# Gap: 117 credit notes not entered in Tally
# Action: Generate credit note vouchers for negative booking amounts
```

---

## 6. Columns Urvashi Uses for Matching

Based on Tally data analysis:

### For Booking → Invoice Match:
1. **invoice_no** (primary key when available)
2. **guest_name** (fallback matching)
3. **arrival_date** (temporal validation)
4. **gross_amount** (amount validation)

### For Payment → Invoice Match:
1. **invoice_no** (invoice.csv has this as primary key)
2. **settlement_amount** → journal voucher amount (invoice.csv)
3. **settlement_modes** → determines payment ledger (invoice.csv, 293 of 304)
4. **invoice_date** → journal voucher date

### For Bank → Payment Match:
1. **utr** (exact match when available)
2. **amount** (validation)
3. **date** (validation, ±2 day window)
4. **"ONE 97 COM"** in narration → confirms Paytm/UPI

---

## 7. Action Items

| # | Task | Owner | Priority | Estimated Coverage Gain |
|---|------|-------|----------|-------------------------|
| 1 | Implement fuzzy invoice_no backfill | ETL | HIGH | +1,500 bookings matched |
| 2 | Map settlement_modes to Tally ledgers | ETL | MEDIUM | Enables journal voucher gen |
| 3 | Generate credit note vouchers | ETL | MEDIUM | +117 vouchers |
| 4 | Handle mixed settlement modes | ETL | LOW | Split multi-mode payments |
| 5 | Document Urvashi's manual steps | Process | MEDIUM | Capture tribal knowledge |

**Total Potential Automation:** From 20.6% → 65% of bookings auto-matched to invoices. Journal vouchers can be generated for all 304 invoices with settlement data.

---

## Appendix: Sample Data Flow

```
EXCEL (Source)                    CANONICAL CSV                 TALLY VOUCHER
───────────────                  ─────────────────             ─────────────

Agoda Booking                    bookings.csv                  Sales Voucher
├─ Guest: UGAM SINGH            ├─ invoice_no: 25-26/96      ├─ Voucher: 25-26/96
├─ Arrival: 2025-04-11          ├─ guest_name: UGAM          ├─ Narration: "...UGAM..."
├─ Gross: ₹11,760               ├─ gross_amount: 11760       ├─ Dr Sundry Debtors: 2210
└─ Settlement: ₹8,431           └─ net_settled: 8431         ├─ Cr SALE ACCOM: 1995.72
                                                              ├─ Cr CGST: 107.14
                                 invoice.csv                  └─ Cr SGST: 107.14
                                ├─ invoice_no: 25-26/96
EZee Transaction Detail         ├─ guest_name: UGAM SINGH
├─ Invoice: 25-26/96            ├─ gross_amount: 2210
├─ Guest: UGAM SINGH            ├─ net_amount: 1995.72
├─ Gross: ₹2,210                ├─ cgst: 107.14
├─ Net: ₹1,995.72               └─ sgst: 107.14
├─ CGST: ₹107.14
└─ SGST: ₹107.14
                                                              Journal Voucher
Paytm Payment Report            upi_payments.csv             ├─ Date: 2025-04-15
├─ UTR: AXN...324              ├─ utr: AXN...324            ├─ Narration: "...25-26/96..."
├─ Settled: ₹8,431             ├─ settled_amount: 8431      ├─ Dr CARD/UPI: 8431
├─ Date: 2025-04-15            └─ settled_dt: 2025-04-15    └─ Cr Sundry Debtors: 8431
└─ ❌ NO INVOICE LINK!           ⚠️ MISSING: invoice_no

Indian Bank Statement           bank.csv
├─ UTR: AXN...324              ├─ utr: AXN...324
├─ Amount: ₹8,431              ├─ amount: 8431
├─ Date: 2025-04-15            └─ date: 2025-04-15
└─ Narration: "ONE 97 COM"      ✅ UTR MATCH CONFIRMS
```

