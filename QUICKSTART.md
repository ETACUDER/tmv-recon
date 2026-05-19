# Quick start — monthly run

5-minute recipe to take a fresh EZee Transaction Detail Report and
produce Tally-importable XML for one month.

## 0. One-time setup

```bash
.venv/bin/python -m pip install -e .
```

Requires Python 3.14+. Deps: `pandas`, `openpyxl`, `flask` (for wizard).

## 1. Drop the raw EZee report

Place the freshest `Transaction Detail Report_*.xlsx` from EZee in:

```
data/recon/2026/
```

Filename doesn't matter — the scripts accept a glob.

## 2. Run the pipeline (4 commands)

Pick `MON=apr2026` style; use the corresponding `YYYY-MM` for filters.
Pick a unique `--alter-id-base` per month (Oct=60000, Apr=70000, May=90000…).

```bash
MONTH=2026-04
MON=apr2026
BASE=70000

# Aggregate raw → canonical invoice CSV
.venv/bin/python scripts/aggregate_invoices_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month "$MONTH" \
  --out  "data/recon/canonical/invoice_${MON}.csv"

# Extract payments → canonical payment CSV
.venv/bin/python scripts/extract_payments_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month "$MONTH" \
  --out  "data/recon/canonical/payment_${MON}.csv"

# Sales XML
.venv/bin/python scripts/generate_sales_vouchers_verbose.py \
  --input  "data/recon/canonical/invoice_${MON}.csv" \
  --output "data/recon/output/sales_vouchers_${MON}_verbose.xml" \
  --alter-id-base "$BASE"

# Journal XML
.venv/bin/python scripts/generate_journal_vouchers_verbose.py \
  --input    "data/recon/canonical/payment_${MON}.csv" \
  --invoices "data/recon/canonical/invoice_${MON}.csv" \
  --output   "data/recon/output/journal_vouchers_${MON}_verbose.xml" \
  --alter-id-base $((BASE + 10000))
```

## 3. Import into Tally

**Order matters:** Sales XML first, then Journal XML.

Gateway → Import → Vouchers → select XML.

Expected outcome (April 2026 reference): Sundry Debtors closes to ₹0
per invoice; any rounding gain/loss lands in `ROUND OFF` ledger.

## Wizard UI (alternative)

```bash
.venv/bin/python web_ui/app.py --port 5005
# open http://127.0.0.1:5005/
```

Drag-drop the xlsx, pick month, download Sales XML. (Journal step pending.)

---

For the *why* of every step (bill-allocation chain, Total Payable, the
paise rounding, advance-receipt rule) see
[`docs/monthly-voucher-flow.md`](docs/monthly-voucher-flow.md).
