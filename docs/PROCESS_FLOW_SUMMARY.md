# TMV Recon - Complete Process Flow
**End-to-End Data Flow: Raw Inputs → Tally Vouchers**

---

## COMPLETE DATA FLOW

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAW INPUTS (Multiple Sources)                   │
└─────────────────────────────────────────────────────────────────────────┘

📄 1. EZee Transaction Detail (Hotel PMS)
   ├─ Source: Hotel management system
   ├─ Format: Excel (.xlsx)
   ├─ Frequency: Monthly export
   ├─ Contains: Invoice #, Guest, Room, Net, CGST, SGST, Gross, Settlement
   └─ Coverage: 579 invoices/month (100% hotel bookings)

📄 2. OTA Booking Reports (Agoda/Booking.com/GoMMT)
   ├─ Source: OTA partner portals
   ├─ Format: Excel (.xlsx)
   ├─ Frequency: Per settlement batch
   ├─ Contains: Booking ID, Guest, Check-in, Commission, Net settled
   └─ Coverage: 378 bookings/month (~65% of total)
   └─ Purpose: Match bookings → invoices, verify OTA commissions

📄 3. UPI Payment Reports (Paytm Gateway)
   ├─ Source: Paytm Business Dashboard
   ├─ Format: Excel (.xlsx) - 123 columns
   ├─ Frequency: Monthly
   ├─ Contains: UTR, Amount, Commission, GST, Settled amount, Settlement date
   └─ Coverage: 28 aggregated payments/month
   └─ Purpose: Link payments → bank, verify gateway fees

📄 4. Bank Statements (Indian Bank)
   ├─ Source: Bank statement download
   ├─ Format: Excel (.xls)
   ├─ Frequency: Monthly
   ├─ Contains: Date, Description (with UTR), Credit, Debit, Balance
   └─ Coverage: 277 transactions/month
   └─ Purpose: Final reconciliation, verify cash received

                          ⬇️ EXTRACTION & MATCHING

┌─────────────────────────────────────────────────────────────────────────┐
│                    CANONICAL DATA (Standardized)                         │
└─────────────────────────────────────────────────────────────────────────┘

📊 bookings.csv (3,476 records FY25-26)
   ├─ From: Agoda/Booking.com/GoMMT Excel files
   ├─ Key: booking_id, invoice_no (when available)
   └─ Match rate: 347/378 have invoice_no (91.8% for Oct)

📊 invoice.csv (579 records for Oct 2025)
   ├─ From: EZee Transaction Detail
   ├─ Key: invoice_no (normalized: 25-26/123 → 2025/2026/123)
   ├─ Aggregated: Sum of line items per invoice
   └─ Validation: Net + CGST + SGST = Gross (100% pass)

📊 upi_payments.csv (28 aggregated for Oct 2025)
   ├─ From: Paytm Excel (123-col format)
   ├─ Key: utr (UTR number)
   ├─ Aggregated: Group by UTR (93% duplicate rate before aggregation)
   └─ Purpose: Link to bank statements

📊 bank.csv (277 transactions for Oct 2025)
   ├─ From: Indian Bank statements
   ├─ Key: utr_extracted (from description)
   └─ Coverage: 792 UTRs extracted across all months

                          ⬇️ MATCHING LOGIC

┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA MATCHING                                    │
└─────────────────────────────────────────────────────────────────────────┘

🔗 Stage 1: BOOKING → INVOICE (91.8% matched)
   Method: Exact match on invoice_no
   ├─ bookings.invoice_no == invoice.invoice_no
   ├─ Matched: 347/378 bookings
   └─ Unmatched: Fuzzy match on guest name + amount + date (not implemented)

🔗 Stage 2: INVOICE → PAYMENT (100% available in invoice data)
   Method: Settlement data embedded in invoice
   ├─ invoice.settlement_amount → Journal voucher amount
   ├─ invoice.settlement_modes → Payment ledger mapping
   │   ├─ "UPI" → "CARD / UPI / PAYTM / G PAY"
   │   ├─ "Cash" → "Cash"
   │   ├─ "Agoda" → "Sundry Debtors" (settled later by OTA)
   │   └─ "Credit Card" → "CARD / UPI / PAYTM / G PAY"
   └─ Coverage: 392/579 invoices have settlement (67.7%)

🔗 Stage 3: UPI → BANK (Optional - for bank reconciliation)
   Method: Match on UTR number
   ├─ upi_payments.utr == bank.utr_extracted
   ├─ Matched: 66 UPI → Bank matches
   └─ Purpose: Verify Paytm settlements hit bank account

                          ⬇️ VOUCHER GENERATION

┌─────────────────────────────────────────────────────────────────────────┐
│                       TALLY VOUCHERS                                     │
└─────────────────────────────────────────────────────────────────────────┘

📝 SALES VOUCHER (Revenue Recognition)
   Source: invoice.csv
   Trigger: Invoice generated in EZee
   Frequency: 579 vouchers/month (Oct 2025)

   Example:
   ┌──────────────────────────────────────────────────────────┐
   │ Type: Sales                Date: 02/10/2025              │
   │ No: 2025/2026/2870         Party: Sundry Debtors        │
   │ Narration: INVOICE NO:-2025/2026/2870, Mr.Chandra...    │
   │                                                          │
   │ Input Column → Tally Ledger:                            │
   │   invoice.gross_amount (₹4,733) → Dr Sundry Debtors    │
   │   invoice.net_amount (₹4,533) → Cr Sale Accom 12%      │
   │   invoice.cgst (₹100) → Cr CGST                         │
   │   invoice.sgst (₹100) → Cr SGST                         │
   └──────────────────────────────────────────────────────────┘

📝 JOURNAL VOUCHER (Payment Settlement)
   Source: invoice.settlement_amount + invoice.settlement_modes
   Trigger: Payment received (recorded in EZee)
   Frequency: 392 vouchers/month (Oct 2025)

   Example:
   ┌──────────────────────────────────────────────────────────┐
   │ Type: Journal              Date: 02/10/2025              │
   │ No: J/2025/2870                                          │
   │ Narration: BEING PAID THROUGH UPI AGAINST INVOICE...    │
   │                                                          │
   │ Input Column → Tally Ledger:                            │
   │   invoice.settlement_amount (₹4,733) → Dr UPI/Card     │
   │   invoice.settlement_amount (₹4,733) → Cr Sundry Debtors│
   │                                                          │
   │ Settlement Mode Mapping:                                 │
   │   invoice.settlement_modes = "UPI"                       │
   │   → Maps to "CARD / UPI / PAYTM / G PAY" ledger         │
   └──────────────────────────────────────────────────────────┘

                          ⬇️ VALIDATION

┌─────────────────────────────────────────────────────────────────────────┐
│                      QUALITY CHECKS                                      │
└─────────────────────────────────────────────────────────────────────────┘

✅ Automated Validations:
   1. GST Formula: Net + CGST + SGST = Gross (100% pass for Oct)
   2. Voucher Balance: Dr total = Cr total (100% balanced)
   3. Invoice Format: Normalized to 2025/2026/XXXX format
   4. Duplicate Check: No duplicate invoice numbers
   5. Date Range: All within fiscal year FY25-26

⚠️ Manual Checks Required:
   1. Guest name spelling (from EZee data)
   2. Multi-payment splits (e.g., "Agoda,UPI" → need manual split if amounts known)
   3. Missing settlements (185/579 invoices unpaid → no journal voucher)
   4. OTA commission entries (not auto-generated)

                          ⬇️ OUTPUT

┌─────────────────────────────────────────────────────────────────────────┐
│                         FINAL OUTPUT                                     │
└─────────────────────────────────────────────────────────────────────────┘

📄 sales_vouchers_oct2025.xml
   ├─ Format: Tally XML import format
   ├─ Count: 579 vouchers
   ├─ Total Revenue: ₹45,42,340
   └─ Import: Gateway → Import Data → Vouchers

📄 journal_vouchers_oct2025.xml
   ├─ Format: Tally XML import format
   ├─ Count: 392 vouchers
   ├─ Total Settled: ₹27,16,567
   └─ Import: Gateway → Import Data → Vouchers

📊 validation_report_oct2025.csv
   ├─ Contains: Match status, amount validation, errors
   ├─ Unmatched: 185 unsettled invoices flagged
   └─ Review: Before importing to Tally
```

---

## COMPLETE COLUMN MAPPING

### EZee Transaction Detail → Tally Sales Voucher

| EZee Column | Type | Sample | → | Tally Field | Purpose |
|-------------|------|--------|---|-------------|---------|
| Invoice # | Text | 25-26/2870 | → | VOUCHERNUMBER | Unique ID (normalized) |
| Invoice date | Date | 02/10/2025 | → | DATE | Posting date |
| Guest Name | Text | Mr. Chandra | → | NARRATION | Reference |
| Net Amount | Decimal | 4533.00 | → | Sale Accom 12% | Revenue (Cr) |
| Tax Amount | Decimal | 100.00 | → | CGST | State tax (Cr) |
| Tax Amount.1 | Decimal | 100.00 | → | SGST | State tax (Cr) |
| Gross Amount | Decimal | 4733.00 | → | Sundry Debtors | Receivable (Dr) |
| Tax % | Decimal | 12.0 | → | Ledger selection | Determines 5%/12%/18% |

### Invoice Settlement → Tally Journal Voucher

| Invoice Column | Type | Sample | → | Tally Field | Purpose |
|----------------|------|--------|---|-------------|---------|
| Invoice # | Text | 2025/2026/2870 | → | NARRATION | Reference |
| Settlement Amount | Decimal | 4733.00 | → | AMOUNT | Payment (Dr/Cr) |
| Settlement/Particular | Text | UPI | → | LEDGERNAME | Payment mode |
| Invoice date | Date | 02/10/2025 | → | DATE | Settlement date |

### UPI Payments → Bank Reconciliation (Optional)

| UPI Column | Type | Sample | → | Bank Column | Match Purpose |
|------------|------|--------|---|-------------|---------------|
| UTR | Text | AXN1234567 | → | utr_extracted | Verify settlement |
| Settled Amount | Decimal | 4733.00 | → | credit | Amount match |
| Settled Date | Date | 05/10/2025 | → | value_date | Date validation |

### OTA Bookings → Invoice Matching

| Booking Column | Type | Sample | → | Invoice Column | Match Purpose |
|----------------|------|--------|---|----------------|---------------|
| invoice_no | Text | 25-26/2870 | → | Invoice # | Primary key |
| guest_name | Text | Chandra | → | Guest Name | Validation |
| gross_amount | Decimal | 4733.00 | → | Gross Amount | Amount check |
| settlement_date | Date | 05/10/2025 | → | - | OTA settlement tracking |

---

## DATA COVERAGE (October 2025)

```
START: 378 OTA Bookings
  ├─ 347 have invoice_no (91.8%) ──┐
  └─ 31 missing invoice_no (8.2%)   │
                                     ▼
                          579 EZee Invoices (MASTER)
                            ├─ 577 hotel bookings ✅
                            ├─ 2 in Excel not in Tally
                            │
                            ├─ 392 have settlement (67.7%) ──┐
                            └─ 187 no settlement (32.3%)     │
                                                              ▼
                                                   28 UPI Aggregated Payments
                                                      ├─ Match by UTR ──┐
                                                      └─ 281 unique UTRs│
                                                                         ▼
                                                              277 Bank Transactions
                                                                ├─ 792 UTRs extracted
                                                                └─ 66 matched to UPI
```

**Coverage Summary:**
- Bookings → Invoices: 91.8% (347/378 with invoice#)
- Invoices → Settlements: 67.7% (392/579 settled)
- UPI → Bank: 23.5% (66/281 matched)

---

## DATASETS NOT USED (But Available)

### ❌ booking.csv - Limited Use
**Why:** Only 91.8% have invoice numbers
**Current:** Used for validation only
**Future:** Implement fuzzy matching (guest name + amount + date)

### ⚠️ upi_payments.csv - Partial Use
**Why:** Not all invoices paid via UPI
**Current:** Used for bank reconciliation only
**Future:** Link UPI → specific invoices (not just bank matching)

### ⚠️ bank.csv - Validation Only
**Why:** Can't directly match bank transactions to invoices
**Current:** Used to verify UPI settlements hit bank
**Future:** Full bank reconciliation module

---

## MONTHLY WORKFLOW WITH ALL INPUTS

**Week 1 (Export Data):**
```bash
Day 1: Export EZee Transaction Detail → invoice.csv ✅ REQUIRED
Day 1: Export Paytm Settlement Report → upi_payments.csv (optional)
Day 2: Download Bank Statements → bank.csv (optional)
Day 2: Export OTA Bookings → bookings.csv (for validation)
```

**Week 1 (Generate Vouchers):**
```bash
Day 3: Run extraction scripts
  $ python -m tmv_recon.etl.extract.invoice    # REQUIRED
  $ python -m tmv_recon.etl.extract.payment    # Optional
  $ python -m tmv_recon.etl.extract.booking    # Optional
  $ python -m tmv_recon.etl.extract.bank       # Optional

Day 3: Generate vouchers
  $ python -m tmv_recon.etl.voucher_generator  # REQUIRED
```

**Week 2 (Import & Validate):**
```bash
Day 4: Import to Tally (3 mins)
Day 4: Validate in Tally (10 mins)
Day 5: Reconciliation reports (if needed)
```

---

## ACCURACY VALIDATION

### October 2025 Results:

| Dataset | Source | Records | Coverage | Used For |
|---------|--------|---------|----------|----------|
| **Invoices** | EZee | 579 | 100% ✅ | Sales vouchers |
| **Settlements** | EZee | 392 | 67.7% ⚠️ | Journal vouchers |
| **Bookings** | OTA | 378 | 91.8% ⚠️ | Validation only |
| **UPI Payments** | Paytm | 28 | - | Bank recon only |
| **Bank Txns** | Bank | 277 | - | Final verification |

**Voucher Generation:**
- Sales: 579/579 = 100% ✅
- Journal: 392/579 = 67.7% (unsettled invoices normal)
- Matched to Tally: 577/577 = 100% ✅

---

## WHAT'S INCLUDED / EXCLUDED

### ✅ AUTOMATED (Zero Manual Entry):
- Hotel room sales (579/month from EZee)
- Guest payments recorded in EZee (392/month)
- GST calculations (100% automated)
- Invoice-to-payment linking (via settlement_modes)

### ⚠️ PARTIALLY AUTOMATED:
- OTA booking matching (91.8% with invoice#)
- Bank reconciliation (66 UPI matches)
- Multi-payment splits (uses first mode only)

### ❌ MANUAL ENTRY REQUIRED:
- F&B restaurant sales (108/month - separate system)
- No-show penalties (4/month)
- Advance payments (not in invoice export)
- Refunds (manual Tally entry)
- Purchase/Expense vouchers (out of scope)

---

## CONTACT & SUPPORT

**Detailed Documentation:** `/docs/ACCOUNTANT_GUIDE.md`  
**Quick Reference:** `/docs/ONE_PAGER.md`  
**Sample Files:** `/data/tally/generated/`  
**Error Logs:** `/tmp/errors.log`

**For Questions:** Contact system administrator

---

**Version:** 1.1 | **Date:** 29-Apr-2026 | **Status:** Complete Data Flow Documented
