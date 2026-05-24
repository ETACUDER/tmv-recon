# tmv-recon

**Monthly EZee → Tally voucher pipeline** for **The Mangal View Residency**.

EZee Transaction Detail Report (.xlsx) → canonical CSVs → verbose Tally
Sales + Journal vouchers (UTF-16 LE+BOM XML, matches native Tally export
schema) → manual import into Tally.

**Status:** Live for FY 2026 monthly runs. Most recent: **April 2026**
(1,083 vouchers — 506 Sales + 577 Journal, ₹23.4L, Sundry Debtors closes
to ₹0 per invoice).

**Live wizard:** <https://accounts.themangalview.com>
(Azure App Service, single login).

**Single source of truth for flow + logic:** [`docs/monthly-voucher-flow.md`](docs/monthly-voucher-flow.md).

## Wizard UI (recommended for monthly runs)

```bash
.venv/bin/python web_ui/app.py --port 5005
# open http://127.0.0.1:5005/
```

Flask 5-step wizard:
1. Upload raw EZee xlsx → pick month → opens a versioned **run folder**
2. Aggregate → canonical invoice CSV + by-source breakdown
3. Generate **Sales XML** → bill-allocation breakdown + download
4. Extract payments → canonical payment CSV + by-mode breakdown
5. Generate **Journal XML** → payment-ledger breakdown + close-out check
   + auto-generates **`combined.xml`** (single import, vouchers ordered per-invoice)

All artifacts (raw.xlsx, invoice.csv, payment.csv, sales.xml.gz,
journal.xml.gz, combined.xml.gz, bundle.zip, run.json) are saved to
`data/recon/runs/<YYYY-MM>/runs/<timestamp>/`. Every run preserved
indefinitely. Browse via **`/history`**, see the flow via **`/flow`**.

Optional single-user login: set env vars `TMV_USER`, `TMV_PASS`,
`TMV_SECRET_KEY` before starting.

## CLI alternative

```bash
.venv/bin/python -m pip install -e .

# 1. Aggregate raw EZee → canonical invoice CSV
.venv/bin/python scripts/aggregate_invoices_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month YYYY-MM \
  --out data/recon/canonical/invoice_<mon><yr>.csv

# 2. Extract payment lines → canonical payment CSV
.venv/bin/python scripts/extract_payments_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month YYYY-MM \
  --out data/recon/canonical/payment_<mon><yr>.csv

# 3. Render Sales XML
.venv/bin/python scripts/generate_sales_vouchers_verbose.py \
  --input  data/recon/canonical/invoice_<mon><yr>.csv \
  --output data/recon/output/sales_vouchers_<mon><yr>_verbose.xml \
  --alter-id-base 70000

# 4. Render Journal XML
.venv/bin/python scripts/generate_journal_vouchers_verbose.py \
  --input    data/recon/canonical/payment_<mon><yr>.csv \
  --invoices data/recon/canonical/invoice_<mon><yr>.csv \
  --output   data/recon/output/journal_vouchers_<mon><yr>_verbose.xml \
  --alter-id-base 80000

# 5. (Recommended) Render a single Combined XML — vouchers ordered per-invoice
#    so Tally imports the bill-opener before any settler in one operation.
.venv/bin/python scripts/generate_combined_vouchers_verbose.py \
  --invoices data/recon/canonical/invoice_<mon><yr>.csv \
  --payments data/recon/canonical/payment_<mon><yr>.csv \
  --output   data/recon/output/combined_<mon><yr>_verbose.xml \
  --sales-alter-id-base 70000 \
  --journal-alter-id-base 80000
```

Import **`combined.xml`** in one shot, or import Sales then Journal separately.
Pick a different `--alter-id-base` per month so VCHKEYs stay distinct across imports.

## Layout

```
src/tmv_recon/vouchers/      ← business logic (single source of truth)
├── config.py                  company, GSTIN, GUID seed, tolerances
├── ledgers.py                 all Tally ledger names + mappings
├── ezee_columns.py            EZee column-name constants
├── flags.py                   voucher/ledger flag sets + empty container lists
├── primitives.py              XML rendering (no business logic)
├── sales.py                   render_sales_voucher(row, alter_id)
└── journal.py                 render_journal_voucher(row, alter_id, ...)

scripts/                       thin CLI wrappers (~50-100 lines each)
├── aggregate_invoices_monthly.py
├── extract_payments_monthly.py
├── generate_sales_vouchers_verbose.py
└── generate_journal_vouchers_verbose.py

web_ui/                        Flask wizard
docs/monthly-voucher-flow.md   end-to-end flow + accounting logic
data/recon/canonical/          per-month canonical CSVs (input to emitters)
data/recon/output/             generated XMLs (input to Tally)
data/recon/newTally/           reference: Master.xml + Transactions.xml from Tally
```

## Key concepts

- **Total Payable** = `Gross − Discount − Adjustment`. Sundry Debtors is
  debited at Total Payable; ROUND OFF Dr balances the voucher when EZee
  applied a small adjustment.
- **Advance Receipt Adjustment:** per invoice, whichever event (Sales or
  Journal payment) is *earliest* opens the bill with **`New Ref`**; all
  later events settle with **`Agst Ref`**. Computed from a pre-pass in
  the aggregator (`bill_opens_with` column).
- **Journal date:** comes from each payment row's `Transaction Date`
  (not the Invoice date) — captures pre-arrival OTA advances correctly.
- **Bill allocation on Journal Dr side:** OTAs (AGODA SDR / BOOKING.COM
  SDR / GOIBIBO / MAKE MY TRIP) + `CARD / UPI / PAYTM / G PAY` get
  `New Ref`. `SANDEEP SHARMA IMP A/C.` (Cash) skips bill alloc — its
  master has bill-wise off.

Full details in [`docs/monthly-voucher-flow.md`](docs/monthly-voucher-flow.md).

## Setup

Requires Python 3.14+ and a venv at `.venv`. See `pyproject.toml` /
`requirements.txt` for the minimal dep list (`pandas`, `openpyxl`,
`flask` for the wizard).

## Historical phases (archived)

Phase 1/2 (April 2026, 3-stage matcher + ground-truth validator) lives
in `src/tmv_recon/{etl,parsers,integration,llm}/` and tests. Not used by
the monthly pipeline; revive by running:
```bash
.venv/bin/python -m pytest tests/test_validator.py tests/test_ground_truth.py
```
Discovery docs at `docs/discovery-2026-04-29-*.md`.
