# Discovery: Urvashi's Manual Tally Posting Workflow
**Analysis Date:** 2026-04-29  
**Meeting:** 141551856 (2026-04-28, Urvashi Jani × Nishant S)  
**Company:** Mangal View Residency (Tally Prime Gold, FY 2025–26)

---

## Workflow Steps

### Sales Entry (EZ Sheet → Tally)
1. Download raw transaction list from EZ PMS: `transaction_detail*.xlsx`
2. Manually highlight required columns: Invoice #, Invoice Date, Guest Name
3. Open Tally: Gateway → Vouchers → F8 Sales
4. For each invoice row, create Sales voucher:
   - Voucher No: convert `2025/2026/126` → `25-26/126`
   - Date: from Invoice Date column
   - Party: `Sundry Debtors` (lumped ledger, no per-customer split)
   - Particulars:
     - `SALE ACCOMODATION GST @ 5%` (net amount)
     - `CGST` (2.5%)
     - `SGST` (2.5%)
   - Narration: `INVOICE NO -<voucher#> <GUEST NAME>` (uppercased)
5. Save voucher. Repeat for each invoice. Time-consuming.

### Payment Entry (Card/UPI Statement → Tally)
1. Download aggregator statement (PTM/Pine Labs): monthly XLSX
2. Cleanup: remove unnecessary columns, keep Transaction_Amount, Commission, GST, Settled_Amt, UTR_No, Settled_Date, Payment_Mode
3. Manually match gross Transaction_Amount to invoice numbers (no automation)
4. For each matched payment, create Journal voucher (not Receipt):
   - Voucher No: re-use invoice number (`25-26/5924`)
   - Date: from Settled_Date
   - Dr `CARD / UPI / PAYTM / G PAY` (gross amount)
   - Cr `Sundry Debtors` (gross amount)
   - New Ref: invoice number (critical for bill-wise clearing)
   - Narration: `BEING PAID THROUGH <MODE> AGAINST INVOICE NO:<vno> <GUEST>`
5. Commission & GST are NOT posted to Tally (gap in current workflow)
6. Unmatched payments sit "On Account" — manual backlog reconciliation

### OTA Processing (Agoda, GoMT)
1. Download monthly raw export from OTA portal
2. Create processed Excel sheet per OTA:
   - Add computed columns: commission, GST breakdown
   - Manually annotate complex cases (e.g., rate changes)
   - Tag credit notes with notation like `(1554*2)` for validation
3. Enter sales into Tally (same Sales voucher process as EZ)
4. Reconcile OTA settlements against bank statements manually
5. Payment entry follows same Journal voucher pattern

---

## Business Rules

### OTA → Tally Ledger Mapping
- **All OTAs** post to single `Sundry Debtors` ledger (no per-OTA split currently)
- **Card/UPI payments** (all modes) post to single `CARD / UPI / PAYTM / G PAY` ledger
- **Three operating units** share one Tally company:
  1. Hotel Front Office (rooms)
  2. TMV Rooftop ≡ JKP (rooftop bar/restaurant)
  3. F&B Service (in-hotel restaurant)

### GST Handling
- **Intra-state:** CGST 2.5% + SGST 2.5% (5% total)
- **Rate:** accommodation 5% observed (screenshots show only 5%; 12% above ₹7500/night not seen yet)
- **Commission GST:** NOT posted to Tally → **input credit lost**

### Commission Pattern
- Deducted at source by aggregators (PTM, Pine Labs, OTAs)
- Gross amount posted to Tally
- Commission + Commission_GST currently NOT recorded as expense
- Net (`Settled_Amt`) hits bank, but Tally shows gross → creates bank recon gap

---

## Edge Cases

### Rate Change Credit Notes
**Context:** Booking made at old rate (e.g., Aug 2025), but check-in after rate change (Sept 2025)  
**Current manual flow:**
1. Original invoice issued at old rate
2. When guest checks in, system catches rate mismatch
3. Urvashi issues credit note for old invoice
4. New invoice cut at new rate
5. Excel notation: `Iwana Bhansali (1554*2)` where `(rate*nights)` validates calculation
6. **Pain:** multi-row Booking IDs (e.g., `5802 5803`) indicate this scenario — easy to miss

**Tally handling:** unclear if credit notes posted as Credit Note voucher type or sales reversal (needs verification)

### On-Account Postings
- Payments without matched invoices sit marked "On Account" in Pending Bills report
- Accumulates over time → reconciliation backlog
- Causes: timing gaps (invoice date ≠ payment date), missing invoice data, typos in manual entry

### Delayed Settlement Timing
**GoMT case:** guest checks in (e.g., Aug), but OTA settlement hits bank next month (Sept)
- Urvashi posts based on bank settlement date to align with actual cash flow
- Creates month-end cutoff issues — invoices in Aug books, cash in Sept books
- "A little bit of problem" — manual accrual adjustment needed

### Multi-Invoice Settlements
- Single OTA settlement file can contain multiple invoices across date ranges
- Requires manual grouping and matching against EZ sheet invoices
- Agoda files: ~20 files for Aug 2025 – Apr 2026, multiple per month due to split settlements

---

## Pain Points

### 1. Manual Data Entry Volume
**Quote (00:04:54):** "So this time is very consuming."  
- Each invoice = 5+ field copies from Excel → Tally
- No batch import used
- Repetitive across 3 operating units

### 2. Multi-Source Reconciliation
- EZ sheet (sales)
- PTM card statement (Hotel, Rooftop, F&B — 3 separate files)
- Bank statements (Hotel main bank, Rooftop bank)
- OTA portals (Agoda, GoMT)
- **All different formats** — manual alignment needed

### 3. Invoice Matching Guesswork
- No UTR or transaction ID in EZ sheet invoices
- Match by amount + approximate date + guest name fuzzy match
- Error-prone: amount collisions (multiple guests same total)

### 4. Lost Financial Data
- Commission expense not recorded → P&L understates costs
- Commission GST not claimed → overpaying GST liability
- Payment mode, UTR, issuing bank lost → audit trail gaps

### 5. On-Account Cleanup
**Quote (context.md line 63):** "shows the gap — payments sitting 'On Account' because they were not properly tied"  
- Manual periodic cleanup needed
- Grows each month if not addressed

### 6. Rate-Change Credit Note Complexity
**Quote (00:21:00):** booking in Aug, guest arrives Sept after rate change → "So when the bill came out, made it... He made it... made it." (transcription garbled, but clear this is painful manual rework)

---

## Key Quotes

**Workflow time burden (00:04:54):**  
> "So this time is very consuming."

**Manual breakdown for validation (00:21:00):**  
> "I have a lot of things that I have. I put it manually. I have to on the of and I use this title to its title for the title."  
> *(Context: manually annotating Agoda sheet with rate calculations to validate totals)*

**Delayed settlement pain (00:23:00):**  
> "it's possible to the payment in the next month. So that's a little bit of problem, because I don't to month here. Because the payment of my bank, give according to the So that's the I have do"  
> *(Translation: settlement timing mismatch forces month-end adjustments)*

**Manual invoice addition to UPI statement (context.md line 88):**  
> "Manually add the corresponding invoice number to each transaction."

**Multi-source data package (00:38:25):**  
> "I will a Tally, which is the Mangalview, and I will you a zip file to the data export."

---

## Narration/Voucher Conventions

### Sales Voucher
- **Voucher No format:** `25-26/####` (fiscal year prefix)
- **Narration template:** `INVOICE NO -<voucher#> <GUEST NAME>`
- **Guest name:** always uppercased in observed entries
- **Particulars labels:** 
  - `SALE ACCOMODATION GST @ 5%` (typo "ACCOMODATION" appears consistent — may be Tally ledger name)
  - `CGST`, `SGST` (standard Tally GST ledgers)

### Journal Voucher (Payments)
- **Voucher No:** re-uses invoice number (same namespace)
- **Narration template:** `BEING PAID THROUGH <MODE> AGAINST INVOICE NO:<vno> <GUEST>`
- **Modes observed:** UPI, TPP, TIDY_CARD, CREDIT_CARD
- **Reference linkage:** New Ref = invoice no (enables Tally bill-wise clearing)

### File Naming (Excel)
- Card statements: `PTM - <MONTH YEAR> (UNIT)`  
  Example: `PTM - MARCH 2026 (FRONT OFFICE)`
- Bank statements: `<BANK> - <MONTH YEAR>`
- OTA processed: `<OTA> <MONTH YEAR> (UNIT if applicable)`  
  Example: `AGODA MARCH 2026 (NMT TRESHA)`

---

## Automation Opportunities

1. **EZ sheet parser** → Tally XML import (avoid manual voucher entry)
2. **UTR-based matching** → auto-link payments to invoices where amount + date window match
3. **Commission ledger creation** → post `Transaction_Amt - Settled_Amt` as expense, Commission_GST as input credit
4. **OTA settlement parser** → standardize Agoda/GoMT formats into canonical pipeline
5. **On-Account resolver** → ML fuzzy matcher for backlog cleanup
6. **Rate-change detector** → flag multi-invoice booking IDs, auto-generate credit note voucher pairs

---

**Total word count:** 982
