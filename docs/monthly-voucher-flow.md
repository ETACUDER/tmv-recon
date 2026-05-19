# Monthly Sales + Journal Voucher Flow

End-to-end guide for converting an EZee Transaction Detail Report into
Tally-importable verbose XML for one month.

> If you're lost mid-month, re-read **§3 Bill-Allocation Chain** and
> **§4 The "Pending Balance in Paise" Mystery** first — those are where
> our settlement logic and rounding rules live.

---

## 1. Pipeline at a Glance

```
EZee Transaction Detail Report (.xlsx)
        │   raw line-items, 56 columns
        ▼
┌───────────────────────────────────────────┐
│ scripts/aggregate_invoices_monthly.py     │  one row per Invoice #
│   → data/recon/canonical/invoice_<m><y>.csv
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ scripts/generate_sales_vouchers_verbose.py│  one Sales voucher per invoice
│   → data/recon/output/sales_vouchers_…xml │  (UTF-16 LE+BOM, ~50 KB per vch)
└───────────────────────────────────────────┘

        EZee Transaction Detail Report (.xlsx)
                │
                ▼
┌───────────────────────────────────────────┐
│ scripts/extract_payments_monthly.py       │  one row per payment line
│   → data/recon/canonical/payment_<m><y>.csv
└───────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────┐
│ scripts/generate_journal_vouchers_verbose.py │ one Journal voucher per payment
│   → data/recon/output/journal_vouchers_…xml  │ split (UTF-16 LE+BOM)
└───────────────────────────────────────────┘

        ▼

┌───────────────────────────────────────────┐
│ TALLY IMPORT ORDER (mandatory):           │
│  1. Sales XML  → creates `New Ref` bills  │
│  2. Journal XML → `Agst Ref` settles them │
└───────────────────────────────────────────┘
```

Reusable wizard UI exposing this pipeline lives at `web_ui/app.py`
(currently single-month Sales side; Journal step to be added).

---

## 2. Canonical CSV Schemas

### `invoice_<mon><yr>.csv` — produced by `aggregate_invoices_monthly.py`

| Column | Source | Notes |
|---|---|---|
| `invoice_no_normalized` / `Invoice #` | EZee `Invoice #` | identical |
| `Invoice date` | EZee `Invoice date` | `YYYY-MM-DD` |
| `Guest Name`, `Room Type`, `Travel Agent`, `Business Source` | EZee | first non-null per invoice |
| `Net Amount` | sum of EZee `Net Amount` per invoice | taxable amount |
| `Tax Amount` | sum CGST per invoice | |
| `Tax Amount.1` | sum SGST per invoice | |
| `Gross Amount` | sum of EZee `Gross Amount` | = Net + CGST + SGST |
| `Discount Amount` | sum of EZee `Discount Amount` | typically 0 |
| `Adjustment` | sum of EZee `Adjustment(Room Charge/Extra Charges)` | small paise-level rounding |
| **`Total Payable`** | `Gross − Discount − Adjustment` | **what Sundry Debtors gets debited at** |
| `settlement_amount_abs` | abs of negative settlements | informational |
| `Settlement/Particular` | EZee | first mode |
| `calc_gross` | `Net + CGST + SGST` | sanity check |
| `diff` | `calc_gross − Gross` | should be 0 |

### `payment_<mon><yr>.csv` — produced by `extract_payments_monthly.py`

One row per `Settlement Amount != 0` line.

| Column | Source |
|---|---|
| `Invoice #` | EZee |
| `Invoice date` | EZee |
| `Guest Name` | EZee |
| `Settlement/Particular` | EZee — payment mode (Cash / UPI / Agoda / etc.) |
| `Settlement Amount` | abs value of EZee `Settlement Amount` (always positive in canonical) |
| `Reference #` | EZee (payment txn ref, if any) |
| `Transaction Date` | EZee |

---

## 3. Bill-Allocation Chain (the settlement engine)

Tally settles outstanding balances per-invoice via **bill references**.
A receivable is opened by `BILLTYPE=New Ref` and closed by `BILLTYPE=Agst Ref`.

### Sales voucher (per invoice)

```
Dr  Sundry Debtors          Total Payable    ← New Ref: invoice#
   Cr  SALE ACCOMODATION GST @ X%   Net
   Cr  CGST                          CGST
   Cr  SGST                          SGST
Dr  ROUND OFF              (Discount + Adjustment)   ← only if non-zero
```

The `Dr ROUND OFF` line is what balances the voucher when `Total Payable`
is less than `Gross` (see §4).

### Journal voucher (per payment line)

```
Dr  <payment ledger>        Settlement Amount   ← bill-ref rule below
   Cr  Sundry Debtors                Settlement Amount   ← Agst Ref: invoice#
```

| Payment mode (EZee) | Tally ledger | Dr bill-ref |
|---|---|---|
| Cash | `SANDEEP SHARMA IMP A/C.` | none (bill-wise off) |
| UPI / Credit Card / Debit Card | `CARD / UPI / PAYTM / G PAY` | none |
| Agoda | `AGODA SDR` | **New Ref** (OTA now owes us) |
| Booking.com | `BOOKING.COM SDR` | **New Ref** |
| Goibibo | `GOIBIBO / MAKE MY TRIP` | **New Ref** |

**Why Sundry Debtors uses `Agst Ref`:** the Sales voucher already created
that bill via `New Ref`. The Journal closes it.

**Why OTA platforms use `New Ref`:** the moment a guest pays via Agoda,
Agoda holds our money and a *new* receivable opens against the OTA. That
bill gets settled later when Agoda actually transfers cash — handled by a
separate OTA-settlement journal we don't generate here.

**Import order is mandatory:** Sales first → Journal second. Otherwise
`Agst Ref` finds no bill and Tally posts "On Account".

---

## 4. The "Pending Balance in Paise" Mystery

### Why ₹0.01–₹0.04 sometimes hangs around per invoice

EZee's room charge math rounds at each line. Across a multi-night stay
the per-line rounding adds up to a few paise that don't sum back to the
displayed Gross. EZee compensates with the `Adjustment(Room Charge/Extra
Charges)` column — typically `+0.01` to `+0.04` per affected invoice.

For April 2026: **78 of 506 invoices** carry such adjustments, totalling
₹0.22 across the month.

### How we handle it

We treat `Adjustment` as a **reduction in what the guest actually owes**
(they pay the rounded-down number EZee printed on the invoice). So:

- `Total Payable = Gross − Discount − Adjustment`
- Sundry Debtors is debited at `Total Payable` (not Gross).
- A balancing `Dr ROUND OFF` entry absorbs the `Discount + Adjustment`
  amount so the voucher still totals to zero.

This is exactly the pattern Tally itself uses (the reference Sales
vouchers in your export include `ROUND OFF` lines at paise values).

### Sign convention for ROUND OFF

- `Adjustment > 0` (guest pays less than computed Gross) → **Dr ROUND OFF** with `IDP=Yes, AMOUNT = −(adjustment)`. This is a loss to us.
- `Adjustment < 0` (rare — guest pays more) → **Cr ROUND OFF** with `IDP=No, AMOUNT = +abs(adjustment)`. This is a gain.

`abs(round_off) < ₹0.005` ⇒ skipped (no ROUND OFF entry needed).

### Result after both imports

| Side | Total (₹) |
|---|---:|
| Sales: Dr Sundry Debtors (sum of Total Payable) | 23,38,992.39 |
| Journal: Cr Sundry Debtors (sum of Settlement Amount) | 23,38,992.83 |
| **Net Sundry Debtors balance after month** | **−₹0.44** |

The remaining ₹0.44 is the gap between what we collected (Settlement)
and what we billed-net-of-adjustment (Total Payable). That's typically a
mix of mode-specific micro-rounding (e.g. UPI gateways rounding to
whole-rupee amounts on a few transactions). **We do not auto-clear this**
— it's small enough to clear with a single manual journal at month-end
if desired.

---

## 5. Voucher-Number Conventions

| | Voucher Number | Reference |
|---|---|---|
| Sales | `<Invoice #>` (e.g. `2025/2026/1`) | `<Invoice #>` |
| Journal | `<Invoice #>` (same number as the invoice it settles) | `<Invoice #>` |

Multiple Journal vouchers can share the same number when an invoice was
paid in multiple splits (UPI ₹500 + UPI ₹500 + UPI ₹5,300 etc.) — Tally
accepts this with Manual numbering. Each split has a distinct GUID so
re-imports are idempotent.

April 2026 audit: **64 of 506 invoices** have 2–4 payment splits.

---

## 6. Idempotency

Both emitters seed `<GUID>` with `uuid5(invoice_no [+ mode + amount + row_id])`.
Re-importing the same XML overwrites the existing voucher in Tally rather
than creating duplicates. Safe to re-run the pipeline whenever the source
data is updated.

---

## 7. Re-running for a New Month

```bash
.venv/bin/python scripts/aggregate_invoices_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month YYYY-MM \
  --out data/recon/canonical/invoice_<mon><yr>.csv

.venv/bin/python scripts/extract_payments_monthly.py \
  --raw "data/recon/2026/Transaction Detail Report_*.xlsx" \
  --month YYYY-MM \
  --out data/recon/canonical/payment_<mon><yr>.csv

.venv/bin/python scripts/generate_sales_vouchers_verbose.py \
  --input  data/recon/canonical/invoice_<mon><yr>.csv \
  --output data/recon/output/sales_vouchers_<mon><yr>_verbose.xml \
  --alter-id-base 70000

.venv/bin/python scripts/generate_journal_vouchers_verbose.py \
  --input  data/recon/canonical/payment_<mon><yr>.csv \
  --output data/recon/output/journal_vouchers_<mon><yr>_verbose.xml \
  --alter-id-base 80000
```

Pick a different `--alter-id-base` per month so generated VCHKEYs don't
collide across months (e.g. Oct=60000, Apr=70000, May=90000, …).

---

## 8. Known Quirks & Gotchas

- **`SALE ACCOMODATION GST @ 5 %`** has spaces both sides of `%` — the
  12% and 18% variants do **not**. Mis-emit and Tally rejects the row.
- **`SANDEEP SHARMA IMP A/C.`** has a trailing period — required.
- **`Sundry Debtors`** is bill-wise on (verified in Master). `CARD / UPI / PAYTM / G PAY` is also bill-wise on but we skip bill allocation on it; this currently shows as "On Account" entries on that ledger — acceptable since it nets out daily.
- Tally's import error log strips whitespace when displaying ledger
  names, so error `"Ledger 'SALE ACCOMODATION GST @5%' does not exist!"`
  was the renderer collapsing `@ 5 %` → `@5%`. The XML byte content was
  always correct; if the import succeeds you know the names match.
- Tally's import is idempotent on `<GUID>`. Manual edits in Tally are
  overwritten if you re-import. Deleted-and-reimported vouchers come
  back identical.

---

_Last updated: 2026-05-19 — covers April 2026 month run._
