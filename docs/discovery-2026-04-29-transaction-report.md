# Transaction/Folio Report Discovery
**Date:** 2026-04-29  
**Objective:** Hunt for EZee PMS transaction report bridging booking → invoice → payment

---

## Search Strategy

### 1. File Name Search Patterns
Searched entire `/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/` for:
- `*transaction*`
- `*folio*`
- `*ezee*`
- `*pms*`
- All `.xlsx`, `.xls`, `.csv` files

### 2. Directories Scanned
- `meet-recording/` (raw meeting files)
- `data/invoices/raw/`
- `data/booking/processed/`
- `data/payments/processed/`
- `data/recon/canonical/`

---

## Candidate Found: CONFIRMED

### File Location
```
/Volumes/CRESCENT/dev/project-sonnet/tmv-recon/meet-recording/transaction_detail20250428.xlsx
```

**This IS the EZee Absolute PMS transaction/folio report.**

---

## File Structure

### Metadata
- **Total Rows:** 1,399 transactions
- **Total Columns:** 55
- **File Size:** Contains both header transactions and line-item details
- **Date Range Covered:**
  - Reservation Date: 2024-12-17 → 2025-04-27
  - Invoice Date: 2025-04-01 → 2025-04-28 
  - Transaction Date: 2025-04-01 → 2025-04-28

### All 55 Columns
```
Transaction Type, Reservation #, Group Code, Reservation Date, Folio #, 
Invoice #, Invoice date, Arrival, Dept., Room Type, Rate Type, Room #, 
Owner Name, Is Paymaster, Pax, Guest Name, VIP Status, Nationality, 
Market Code, Travel Agent, Travel Agent Voucher #, Business Source, 
Company Name, Sales Person Name, Reservation Type, Booking Status, 
Bill To Name, RegNo., Transaction, Transaction Date, Charge, 
Extra Charge Type, HSN/SAC, Settlement/Particular, Reference #, User Name, 
Comment, Qty, Actual Rate(Configured Rate), Slab Information, Net Amount, 
Discount Name, Discount %, Discount Amount, Taxable Amount, Tax Name, 
Tax %, Tax Amount, Tax Name.1, Tax %.1, Tax Amount.1, 
Adjustment(Room Charge/Extra Charges), Gross Amount, Settlement Amount, 
Folio Status
```

### Key Columns for Bridging

#### Booking Domain
- `Reservation #` - Links to booking/reservation system
- `Group Code` - For group bookings
- `Business Source` - OTA/channel (AGODA, BOOKING.com, Rovers Network, DIRECT, Goibibo-MMT)
- `Travel Agent Voucher #` - OTA booking reference

#### Invoice Domain  
- `Invoice #` - Format: `2025/2026/96`, `25-26/35`, etc.
- `Folio #` - Folio reference number
- `Invoice date` - Invoice generation date

#### Payment Domain
- `Settlement/Particular` - Payment mode (UPI, Cash, Credit Card, Debit Card, Agoda, Goibibo, Round Off, Bank Transfer)
- `Settlement Amount` - Amount settled via this mode
- `Gross Amount` - Total invoice amount

---

## Sample Data (First 5 Rows)

```
Reservation # | Folio # | Invoice #    | Business Source          | Guest Name           | Gross Amount | Settlement/Particular | Settlement Amount
6669          | 4844    | NaN          | BOOKING.com              | indrajeet tiwari     | 0.0          | NaN                  | NaN
6739          | 43      | NaN          | Rovers Network Pvt. Ltd. | Mr.Nikhil Jat        | 0.0          | NaN                  | NaN
6757          | 66      | NaN          | Rovers Network Pvt. Ltd. | Mr.ROSHAN KUMAR      | 0.0          | NaN                  | NaN
6803-1        | 122     | 2025/2026/96 | NaN                      | Mr.UGAM SINGH        | 0.0          | NaN                  | NaN
6910-2        | 268     | NaN          | NaN                      | Mr.Shahrukh Cooper   | 0.0          | NaN                  | NaN
```

---

## Data Completeness Assessment

### Invoice Coverage
- **Total rows:** 1,399
- **Rows with Invoice #:** 1,201 (85.8%)
- **Rows without Invoice #:** 198 (14.2%)
- **Invoices in canonical:** 304 (already extracted from this file)

### Payment Settlement Tracking
- **Rows with settlement data:** 530 (37.9%)
- **Rows WITHOUT settlement data:** 869 (62.1%)
- **Settlement data coverage:** Only 39.6% of invoices have payment mode recorded

### Settlement Mode Breakdown
```
UPI              188 (35.5%)
Agoda            174 (32.8%)
Cash              66 (12.5%)
Credit Card       64 (12.1%)
Debit Card        18 (3.4%)
Goibibo           14 (2.6%)
Round Off          5 (0.9%)
Bank Transfer      1 (0.2%)
```

### Business Source Breakdown
```
AGODA                       610 (43.6%)
Rovers Network Pvt. Ltd.    308 (22.0%)
BOOKING.com                 242 (17.3%)
DIRECT                      103 (7.4%)
Goibibo-MMT                  53 (3.8%)
```

### Why "Partial Data"?

1. **Time Period Limited:** Only April 2025 invoices (2025-04-01 to 2025-04-28)
   - Missing historical months
   - Missing May 2025 onwards (future from file date)

2. **Payment Settlement Gaps:**
   - 60.4% of invoices lack payment mode details
   - Settlement/Particular field is sparse
   - No payment transaction IDs to link to Paytm bank statements

3. **No Direct Payment Transaction Link:**
   - Contains settlement modes (UPI, Credit Card) but NO transaction IDs
   - Cannot directly join to `canonical/payment.csv` which has `txn_id`, `order_id`
   - Payment reconciliation requires fuzzy matching on:
     - Guest name (available in both)
     - Amount (gross amount vs payment amount)
     - Date range (invoice date vs transaction date)

4. **OTA Settlements Not Detailed:**
   - When Settlement/Particular = "Agoda", no breakdown of actual payment mode
   - OTA settlements are black boxes - no visibility into how OTA collected from guest

---

## Join Key Analysis

### Transaction Detail → Canonical Booking
**Primary Keys:**
- `Reservation #` → `agoda_booking_id` (for AGODA)
- `Travel Agent Voucher #` → Can contain booking reference

**Secondary Keys:**
- `Guest Name` → `guest_name` (fuzzy match required)
- `Arrival` → `checkin` date
- `Invoice #` → `invoice_no`

**Coverage:**
- Booking canonical has mostly AGODA/Goibibo data (settlement batches)
- Transaction detail has ALL channels including BOOKING.com, Direct

### Transaction Detail → Canonical Invoice
**Primary Keys:**
- `Invoice #` → `invoice_no` (EXACT match)
- `Folio #` → `folio_nos`
- `Reservation #` → `reservation_no`

**Status:** Already extracted! 304 invoices in canonical came from this file.

**What's New in Transaction Detail:**
- Line-item level details (charges, taxes, discounts)
- Settlement mode per transaction row
- Multiple payment modes per invoice (split payments)

### Transaction Detail → Canonical Payment
**No Direct Join Keys Available**

**Fuzzy Matching Required:**
- `Guest Name` → `pos_guest_name` (only 107/316 payments have guest name)
- `Settlement Amount` → `settled_amount` (amount match within tolerance)
- `Invoice date` → `txn_dt` (date proximity)
- `Settlement/Particular` → `payment_mode` (mode type match)

**Major Gap:**
- Transaction detail has payment MODE (UPI, Cash, Credit Card)
- Payment canonical has transaction ID, bank details, UTR
- No common identifier to join them definitively

**Example Mismatch:**
- Invoice shows "UPI - 7500.0" settlement
- Payment canonical shows "txn_id 20251201010840000202321030660583916, UPI 7500.0"
- Same amount, same mode, but which invoice? Requires date+guest+amount triangulation

---

## Bridging Strategy

### What This File DOES Bridge

✅ **Booking → Invoice** (via Reservation #, Travel Agent Voucher #, Invoice #)
- Can link OTA bookings to generated invoices
- Track which reservations got invoiced

✅ **Invoice → Payment Mode** (via Settlement/Particular)
- Know WHAT payment mode was used (UPI vs Cash vs Card)
- Track split payments (multiple settlement rows per invoice)

✅ **Invoice → OTA** (via Business Source)
- Filter invoices by channel
- Group settlements by OTA

### What This File DOES NOT Bridge

❌ **Invoice → Bank Statement** (no transaction IDs)
- Cannot link invoice settlement to specific Paytm/bank transaction
- No UTR, order_id, txn_id references

❌ **Payment Mode → Payment Transaction** (no POS identifiers)
- "UPI 1500" in transaction detail ≠ specific UPI txn in payment canonical
- Multiple UPI payments on same day create ambiguity

❌ **OTA Settlement → Commission Breakdown** (aggregated data)
- "Agoda settlement" is a lump sum
- No visibility into Agoda's commission, guest payment method, etc.

---

## Alternative Bridging Strategies

Since this file is partial and lacks payment transaction IDs, use these approaches:

### Strategy 1: Amount + Date + Guest Triangulation
```python
# Pseudo-logic
for invoice in transaction_detail:
    if invoice.settlement_mode in ['UPI', 'Credit Card', 'Debit Card']:
        candidates = payment_canonical.filter(
            payment_mode == invoice.settlement_mode,
            abs(settled_amount - invoice.settlement_amount) < 5,  # tolerance
            txn_dt.date == invoice.invoice_date,
            guest_name_similarity(pos_guest_name, invoice.guest_name) > 0.8
        )
        # Pick best match
```

**Challenges:**
- Multiple payments same day, same amount (common for fixed room rates)
- Guest name mismatches (POS uses card name, invoice uses booking name)
- Settlement date ≠ transaction date (delays)

### Strategy 2: Aggregate Cross-Validation
```python
# Instead of line-by-line matching, validate totals
daily_invoice_totals = transaction_detail.group_by(invoice_date, settlement_mode).sum()
daily_payment_totals = payment_canonical.group_by(txn_date, payment_mode).sum()

# Flag discrepancies
discrepancies = daily_invoice_totals - daily_payment_totals
# Investigate unmatched amounts
```

**Use Case:**
- Detect missing payments (invoiced but not received)
- Detect extra payments (received but not invoiced)
- Monthly reconciliation reports

### Strategy 3: Two-Hop Join via Canonical Invoice
```
Transaction Detail → Canonical Invoice → Manual Annotation File → Payment
```

If a manual annotation file exists (or can be created) mapping:
- `invoice_no` → `txn_id` or `order_id`

Then:
1. Transaction detail → canonical invoice (via invoice_no)
2. Canonical invoice → annotation (manual mapping)
3. Annotation → payment canonical (via txn_id)

**Requires:** Manual data entry or OCR of receipts linking invoices to payment IDs.

### Strategy 4: Use This File for Invoice-Level Tracking Only
Accept the limitation and use transaction detail for:
- Invoice generation audit (which reservations got invoiced?)
- OTA channel analysis (revenue by Business Source)
- Payment mode trends (UPI vs Cash adoption over time)
- Settlement status tracking (Close vs Active vs Void folios)

Then use payment canonical separately for:
- Bank reconciliation (UTR matching to bank statements)
- Commission analysis (payment processor fees)
- Settlement timeline (payout delays)

Treat them as parallel views, not joined datasets.

---

## Recommended Next Steps

1. **Extract Extended Invoice Details**
   - Add line-item charges (Transaction, Charge columns)
   - Add tax breakdown (Tax Name, Tax %, Tax Amount)
   - Add discount tracking (Discount Name, Discount %)
   - Create `invoice_line_items.csv` canonical

2. **Build Payment Mode Mapping Table**
   - Extract all settlement records from transaction detail
   - Create `invoice_settlements.csv`:
     - invoice_no, settlement_mode, settlement_amount, settlement_date
   - Use for split payment analysis

3. **Request Complete Transaction History**
   - Get transaction detail exports for ALL months (not just April 2025)
   - Ensure date range covers same period as booking/payment data

4. **Investigate PMS Settlement Workflow**
   - Why is Settlement/Particular missing for 62% of rows?
   - Are these unpaid invoices? Or payment mode not recorded?
   - Check Folio Status = "Active" vs "Close" correlation

5. **Build Fuzzy Matching Pipeline**
   - Implement Strategy 1 (triangulation) for partial automation
   - Flag low-confidence matches for manual review
   - Create `payment_invoice_links.csv` with confidence scores

6. **Create Dashboard for Gaps**
   - Invoices with settlement mode but no matching payment transaction
   - Payments with no linked invoice
   - Daily totals variance (invoice settlements vs payment totals)

---

## Summary

**FOUND:** EZee Absolute PMS transaction/folio report at `meet-recording/transaction_detail20250428.xlsx`

**BRIDGES:**
- Booking → Invoice ✅ (via Reservation #, Invoice #, OTA voucher)
- Invoice → Payment Mode ✅ (via Settlement/Particular field)
- Invoice → Payment Transaction ❌ (no txn_id, requires fuzzy match)

**PARTIAL BECAUSE:**
- Time period: Only April 2025 (28 days)
- Settlement tracking: Only 39.6% of invoices have payment mode
- No transaction IDs: Cannot directly link to bank/Paytm statements

**USE FOR:**
- Invoice generation audit
- OTA channel revenue analysis  
- Payment mode trend tracking
- Split payment identification

**CANNOT USE FOR:**
- Definitive bank reconciliation (use payment canonical instead)
- Commission calculation (use booking canonical OTA settlements)
- Real-time payment status (data is snapshot from 2025-04-28)

**BRIDGE STRATEGY:**
- Use as invoice master + payment mode indicator
- Join to canonical invoice for extended details
- Fuzzy match to payment canonical via amount+date+guest
- Aggregate validation rather than line-by-line matching
