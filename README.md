# tmv-recon

**Monthly EZee → Tally voucher pipelines** for **two entities** under one wizard:

| Entity | GST | Source | Output |
|---|---|---|---|
| 🏨 **The Mangal View Residency** (hotel) | Regular | EZee *Transaction Detail Report* (.xlsx) | Sales + Journal (CGST/SGST, bill-wise) |
| 🍽️ **TMV Rooftop Restaurant** | Composition | EZee *Sales Detail* + *Settlement Detail* (.html); bank optional | Sales + Journal (+ Receipt/Payment) |

Both emit verbose UTF-16 LE+BOM XML matching the native Tally export schema
for manual import. **Live wizard:** <https://accounts.themangalview.com> —
landing page picks the entity; **⚙ Ledger mappings** page edits how each
channel/mode posts to a Tally ledger.

**Status:** Live (Azure App Service, single login). Hotel latest clean run
April 2026 (1,083 vouchers). Rooftop live for March 2026.

**Flow + logic detail:** [`docs/monthly-voucher-flow.md`](docs/monthly-voucher-flow.md).

## Hotel — the pipeline in one paragraph
EZee report → canonical `invoice.csv` + `payment.csv` → **Sales** (Dr Sundry
Debtors New Ref / Cr GST-rated Sales + CGST/SGST) and **Journal** (settle the
bill via Agst Ref) → `combined.xml`. A **close-out check** confirms Sundry
Debtors nets to ₹0 before import. Two safety layers: (1) settlement **modes
with no ledger** are flagged in the result and mappable from the wizard
(self-service, no code change); (2) invoices with a **reversal/refund** are
quarantined for **manual review** with a plain-English treatment (see
`src/tmv_recon/vouchers/review.py`) instead of fudging a balancing entry.

## Rooftop — the pipeline in one paragraph
EZee **Settlement Detail** gives the per-order payment **channel** (Cash / UPI /
Credit Card / Debit Card / Dineout / Zomato / Swiggy); joined to **Sales Detail**
by receipt #. Per order: **Sales** (Dr `SUNDRY DEBTORS RESTAURENT` New Ref / Cr
`SALES UNDER COMPOSITION SCHEME`) + **Journal** (Dr channel ledger / Cr the
restaurant debtor). Channel → ledger map lives in `restaurant/pipeline.py`
(`CHANNEL_LEDGER`, override-able from `/config`). The **bank statement is
optional** — with it, Receipts (credits) + Payments (debits) are added; without
it, only Sales + Journal. Composition dealer: no output GST, no bill-wise.

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

## Ledger mappings (`/config`)

How each payment channel/mode posts to a Tally ledger, viewable + editable
in the browser at **`/config`**:
- **Rooftop** channel → ledger (Dineout → `BUNDAL TECHNOLOGIES`, Swiggy →
  `SWIGGY SCR`, UPI/Card → `CARD / UPI / PAYTM / G PAY [F&B]`, Cash →
  `SANDEEP SHARMA IMP A/C.`, Zomato → `ZOMATO`). Validated against the
  restaurant Tally master (`data/recon/rooftop/ledgers.json`) — a red dot
  means the ledger isn't in the master.
- **Hotel** mode → ledger (Agoda/Booking/Goibibo/UPI/Cash… + any the
  accountant adds).

Built-in defaults live in code (`restaurant/pipeline.py CHANNEL_LEDGER`,
`vouchers/ledgers.py PAYMENT_LEDGER_BY_MODE`); edits are saved as **overrides**
(`recon/rooftop_channel_ledgers.json`, `recon/hotel_payment_ledgers.json`) and
merged at run time. `GET/POST /api/config/mapping(s)`.

## Deploy & persistence

Production is **Azure App Service `tmv-accounts`** (rg `tmv-accounts`) mapped to
`accounts.themangalview.com`. Deploy is a **manual zip** (no CI): bundle
`web_ui/ src/ scripts/` + `requirements.txt startup.txt .deployment` +
`data/recon/rooftop/ledgers.json`, then

```bash
az webapp deploy -g tmv-accounts -n tmv-accounts --src-path app.zip --type zip
```

Oryx builds from `requirements.txt` (`SCM_DO_BUILD_DURING_DEPLOYMENT=true`);
startup runs `gunicorn --chdir web_ui app:app`. **Runtime data (runs, uploads,
saved mappings) lives under `TMV_DATA_DIR`** — set to `/home/data` on Azure (the
persistent share) so redeploys don't wipe run history or mappings. Locally it
defaults to `./data`. Login via env `TMV_USER` / `TMV_PASS` / `TMV_SECRET_KEY`.

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
