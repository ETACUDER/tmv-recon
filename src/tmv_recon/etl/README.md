# tmv-recon ETL

Hotel reconciliation pipeline for **The Mangal View Residency** (FY 25–26).
Source-agnostic ETL into canonical fact tables, then matcher across
booking ↔ invoice ↔ payment.

## Status

| Stage | Status |
|---|---|
| File bucketing | ✅ done — 105 files classified, LIC noise quarantined |
| Schema discovery | ✅ done — see `_discovery_{booking,invoices,payments}.md` |
| Canonical models | ✅ done (`models.py` + extractors emit CSV in `data/recon/canonical/`) |
| Extractors | ✅ done — booking, invoice, payment, bank |
| Matcher | ✅ v1 done — UTR/amount-date/guest fuzzy strategies |
| Reports | ✅ summary at `data/recon/reports/summary.txt` |

## Current pipeline output

| Canonical file | Rows |
|---|---|
| `invoice.csv` | 304 invoices (300 reconcile Net+CGST+SGST=Gross) |
| `booking.csv` | 3,476 Agoda rows across 20 batches (2,808 invoice-linked, 715 with rate×nights, 119 credit-notes) |
| `payment.csv` | 316 PTM transactions (Dec 25 – Feb 26) |
| `bank.csv` | 1,363 Indian Bank statement lines (Jan 25 – Mar 26) |

| Match | Result |
|---|---|
| PTM ↔ Bank (Paytm settlement → bank credit) | **66 payout batches matched, 146 of 316 PTM txns covered** (46%) |
| PTM ↔ Invoice | 0/316 — no temporal overlap (see below) |
| Booking ↔ Invoice (Agoda invoice_no exact) | 40/3476 — same temporal mismatch |

## ⚠️ Critical data gap

**The EZ invoice export covers only 1–28 April 2025.** Payments cover Dec 2025 – Feb 2026. There is **zero overlap** between the two periods, so PTM↔invoice matching can't currently produce results regardless of how good the matcher is.

To get real recon numbers we need either:
- A fresh EZ `transaction_detail*.xlsx` covering Dec 2025–Feb 2026 (and/or full FY 25–26), or
- PTM/bank statements covering April 2025 to match the existing EZ export.

Once a same-period EZ export lands in `data/invoices/raw/`, re-running `python -m tmv_recon.etl.extract.invoice && python -m tmv_recon.etl.recon` will populate match rates.

## ⚠️ Findings the user should weigh in on

1. **GST rate mismatch.** EZ data shows accommodation GST = **12% (CGST 6 + SGST 6)** on every invoice; the Tally ledger label seen on screen is `SALE ACCOMODATION GST @ 5%`. Either the label is misleading or there's a hidden 5% bucket elsewhere. *Decision needed: which is canonical for the recon?*
2. **PrmPayRcpt PDFs are NOT TMV.** All 12 are LIC of India renewal premium receipts from the Banswara branch (per discovery). Moved to `data/_quarantine/`. The hypothesised "PDF carries invoice → bridges EZ to PTM" doesn't apply. *Need actual TMV PMS payment receipts (or an EZ payment-allocation export) to build that bridge.*
3. **`tallyData/` is not a real Tally export.** All 30 files are byte-identical (or cosmetic-diff) dupes of `payments/processed/` and `booking/processed/`. **No journal vouchers, no Dr/Cr lines, no Sundry Debtors postings.** To validate matching against Tally we still need a real Tally Day Book / Vouchers XML export.

## Buckets on disk

```
data/
├── booking/
│   ├── raw/         (0)        — no untouched OTA dump in scope
│   └── processed/   (21)       — Agoda, with rate-change credit notes & header typos
├── invoices/
│   ├── raw/         (1)        — transaction_detail*.xlsx (EZ, 1399×55)
│   └── processed/   (0)
├── payments/
│   ├── raw/         (6)        — PTM 123-col Paytm dumps (FRONT OFFICE Dec/Jan/Feb)
│   └── processed/   (35)       — PTM/UPI slim copies + Indian Bank statements
├── tally/raw/       (30)       — dupes only; not a real Tally export (see above)
├── recon/
│   ├── canonical/              — output: parquet/csv per fact table
│   ├── matches/                — output: matched + unmatched lists
│   ├── reports/                — output: human-readable reconciliation reports
│   └── _manifest.csv           — file→bucket mapping
└── _quarantine/    (12 LIC PDFs)
```

## Three reconciliation streams

```
┌── Sales (invoice) ────────────────────────┐
│   EZ sheet (invoices/raw/)                │
│         ↓ ETL → canonical_invoice          │
│   Tally Sales voucher (Sundry Debtors)    │
└───────────────────────────────────────────┘
              ⇅  invoice_no
┌── OTA (Agoda — booking/processed/) ───────┐
│   Per-batch settlement Excels             │
│         ↓ ETL → canonical_booking          │
│   Tally Sales + occasional Credit Note    │
└───────────────────────────────────────────┘
              ⇅  UTR / amount-date / VPA
┌── Receipts (payment) ─────────────────────┐
│   PTM raw 123-col (Paytm aggregator)      │
│   Indian Bank statements (main + rooftop) │
│         ↓ ETL → canonical_payment          │
│   Tally Journal voucher                   │
└───────────────────────────────────────────┘
```

## Key formulas (verified)

**Agoda (booking)** — `INVOICE AMT = From Agoda + COMM+GST` exactly (max diff 2.3e-13 across 370 rows). No TCS/TDS columns in this dataset (likely netted upstream or only in GoMT — which we don't have).

**PTM (payment)** — `Settled_Amount = Amount − Commission − GST` exact. `GST = 18% × Commission` (pure 18%). Commission rate per mode/scheme:

| Mode | Scheme | Rate (mean) |
|---|---|---|
| CREDIT_CARD | AMEX | 3.99% |
| CREDIT_CARD | DINERS | 2.99% |
| CREDIT_CARD | MASTER | 2.93% |
| CREDIT_CARD | RUPAY | 1.99% |
| CREDIT_CARD | VISA | 2.93% |
| DEBIT_CARD | MASTER | 3.50% |
| DEBIT_CARD | VISA | 2.90% |
| UPI_CREDIT_CARD | – | 2.50% (flat) |
| UPI | – | 0.00% (zero MDR) |

**EZ invoice** — `Net + CGST + SGST = Gross` for every invoice (304/304 reconciled).

## Match logic (planned)

Priority for the matcher (`recon.py`):

1. **UTR exact** (PTM `UTR_No.` ↔ bank `Description` regex `NEFT/<bank>/(<utr>)/…` ↔ bank `Chq No/REF No/UTR No`). One-to-many: a single UTR settles multiple PTM rows; the bank credit equals `sum(Settled_Amount where UTR=X)`.
2. **RRN/ARN** (PTM `RRN` ↔ rooftop UPI narration `BY UPI CREDIT UPI/<rrn>/…`).
3. **Amount + date window** (gross PTM `Amount` ≈ EZ invoice `Gross_Amount`, settled within +0/+7 days of invoice date).
4. **`UDF2` / `Customer_VPA` → guest fuzzy** vs EZ `Bill To Name` / `Guest Name` (rapidfuzz ≥ 85).
5. **Agoda booking_id → invoice** via EZ `Travel Agent Voucher #` (when present).

`booking_id`-based EZ↔Agoda match is the ground truth for OTA-channel invoices; missing values fall to amount+date+guest.

## Header normalization required

Agoda files have **12 column-name variants** (typos: `INVOCIE`, `INVOICE  NO.`, `COMM + GST`, `COMM+ GST`, `AGODAT SITE`, `ament amt absoulte`, etc.). Extractor must canonicalize via fuzzy header matching before further processing.

EZ has 3 `Tax Name` spellings (`CGST`, `CGST 6%`, `CGST @ 9%`) — same canonicalization concern.

PTM raw has consistent column names but values for ID-like cols are stored Excel-quoted (leading `'`) — strip on read.

## Running

```bash
# 1. (Re-)bucket files
.venv/bin/python -m tmv_recon.etl.bucket

# 2. Extract → canonical (one-shot per source)
.venv/bin/python -m tmv_recon.etl.extract.booking
.venv/bin/python -m tmv_recon.etl.extract.invoice
.venv/bin/python -m tmv_recon.etl.extract.payment

# 3. Run matcher
.venv/bin/python -m tmv_recon.etl.recon

# 4. Outputs land in data/recon/{canonical,matches,reports}/
```

## Open questions (to resolve incrementally)

- [ ] **GST 12% vs 5%** in Tally label — which is canonical?
- [ ] **TCS/TDS** location — Agoda data has no TCS/TDS column. Where do these get applied? (GoMT-only? Year-end JV?)
- [ ] **Where is the actual Tally export** (Day Book XML or vouchers dump)?
- [ ] **Where do PMS receipt PDFs live** (the real ones — the bridge from invoice → payment)?
- [ ] **Sign convention** for `amend amt` / `credit note` columns differs between NOV and DEC Agoda files — clarify.
- [ ] **`HSN/SAC=RP`** rows in EZ — what's the business meaning? (207 rows have non-zero Net but no tax.)
- [ ] **Void-after-issue invoices** (13 rows in EZ with Folio Status=Void, Invoice # populated, all zero) — handle as no-op or as credit-note?
