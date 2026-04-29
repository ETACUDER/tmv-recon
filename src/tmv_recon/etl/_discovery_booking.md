# Booking bucket — discovery (Agoda OTA exports)

20 xlsx files in `data/booking/processed/`. All link to `meet-recording/data_sheets_historical/mangal all data sheet/AGODA/`. Each file = one Agoda settlement batch; settlement amount encoded in filename (e.g. `AMT 759282.14`). Tally postings: Sales vouchers + occasional Credit Notes.

## 1. Files inspected

| File | Sheet | rows × cols |
|---|---|---|
| AGODA AUGUST 2025 -AMT 44912.xlsx | Remittances | 31×11 (raw) |
| AGODA 16540.78 AMT [8.10.25].xlsx | Remittances | 5×10 (annot+CN) |
| AGODA SEP 2025 AMT 80280.25 RS.xlsx | Remittances | 12×9 (annot) |
| AGODA AUGUST 2025.xlsx | Remittances | 581×11 (raw) |
| AGODA MARCH 2026, AMT 759282.14.xlsx | "AGODA MARCH 2026..." | 174×12 (annot+RefNo+SITE) |
| AGODA SEPT 2025-AMT 1876144.81.xlsx | Remittances | 371×9 (annot) |
| AGODA NOV 2025 - 2140075.38 AMT.xlsx | Remittances | 375×11 (annot+amend) |
| AGODA DEC 2025- 2030043.35 AMT.xlsx | Remittances | 430×12 (annot+amend, Unnamed cols) |
| AGODA 14 APRIL 2026 AMT- 734555.64 RS.xlsx | PastPayouts_20260406-96148_2026 | 139×11 (annot+RefNo) |
| AGODA FEB 2026 AMT- 630617.67 RS.xlsx | "AGODA FEB 2026..." | 142×11 |
| AGODA SEPT 2025- AMT- 80280.25 ISSUED.xlsx | Remittances | 13×9 (HEADER ROW SHIFTED — title row in row 0) |
| (others similar) | | |

All single-sheet workbooks. No hidden sheets, no merged cells. Some files have live formulas (MARCH 759282 = 338, SEPT 1876144 = 373); raw-export files have zero formulas.

## 2. Canonical column union (occurrence count over 20 files)

**Required (≥17 files)**: `Guest name` (19), `Booking paid by` (19, always 'Agoda'), `From Agoda` (19, net to property), `Check-in date` (19), `Check-out date` (19).

**Booking ID variants (12)**: `Booking ID` (12) — also encoded as `Reference number` (7) in newer files. Together cover 19/20.

**Invoice number variants (17)**: `INVOICE NO.` (9), `INVOCIE NO.` (6, typo), `INVOICE NO` (1), `INVOCIE NO` (1), `INVOICE  NO.` (1).

**Invoice amount variants (16)**: `INVOICE AMT.` (7), `INVOCIE AMT.` (4), `INVOCIE AMT` (3), `INVOICE AMT` (2), `invoice amt.` (1).

**Commission variants (16)**: `COMM + GST` (9), `COMM+GST` (5), `COMM +GST` (1), `COMM+ GST` (1), `comm + gst` (1).

**Credit-note variants (9)**: `CREDIT NOTE` (8), `credit note` (1).

**Amendment variants (3)**: `ament amt absoulte` (1, typo), `amend amt` (1), `AMEND` (1, string flag).

**Site amount (7)**: `AGODA SITE` (6), `site amt` (1), `AGODAT SITE` (1, typo) — the gross room-night amount Agoda displays on its site (incl. their commission); generally ≥ INVOICE AMT.

**Reconciliation (3)**: `e-f =g` (1, leftover formula label).

**Raw export only (2 files: AUG 2025, AUG 2025-44912)**: `Transaction type` (always 'Reservation'), `Property ID` (always 37040529), `Currency` (INR), `To property` (=From Agoda), `Payout method` ('Telex Transfer').

**Quirky one-off**: `AGODA SEPT 2025- AMT- 80280.25 ISSUED.xlsx` has the actual headers in row 0 with column labels `Unnamed: 0..8` + a banner cell `ISSUED SHEET` — needs `header=1` or skip 1 row.

## 3. Sample rows (verbatim, names lightly anonymized)

Annotated style — `AGODA SEPT 2025-AMT 1876144.81`:
```
INVOCIE NO. | Booking ID  | Guest name      | Booking paid by | INVOCIE AMT. | From Agoda | COMM + GST | Check-in date         | Check-out date
2436        | 1929760xxx  | Abh___          | Agoda           | 4704.00      | 3372.60    | 1331.40    | 9/7/2025 12:00:00 AM  | 9/9/2025
2504, 2505  | 1928029xxx  | Abh___ [7056*2] | Agoda           | 14112.00     | 10193.40   | 3918.60    | 9/9/2025              | 9/12/2025
(TOTAL row)                                                  | 1185743.44   | 845285.74  | 340457.70  |                       |
```

Annotated+CN — `AGODA MARCH 2026 AMT 759282.14`:
```
INVOICE NO.   | Reference number | Guest name        | AGODA SITE | INVOICE AMT. | e-f =g | From Agoda | COMM + GST | CREDIT NOTE | Check-in   | Check-out
6106 , 6122   | 1971317xxx       | Aak___ (1554*2)   | 3108       | 3108.00      | 0.0    | 2184.48    | 923.52     | 0.0         | 2026-03-12 | 2026-03-13
5941 , 5942   | 1970964xxx       | Aar___ (3885*2)   | 7770       | 7770.00      | 0.0    | 5431.60    | 2338.40    | 0.0         | 2026-03-02 | 2026-03-04
5915          | 1956716xxx       | Abh___ Mishra     | 5250       | 5250.00      | 0.0    | 2345.00    | 2905.00    | 0.0         | 2026-02-28 | 2026-03-02
```

Raw export — `AGODA AUGUST 2025`:
```
Transaction type | Booking ID | Property ID | Guest name | Booking paid by | Currency | From Agoda | To property | Check-in              | Check-out             | Payout method
Reservation      | 1906206xxx | 37040529    | Nid___     | Agoda           | INR      | 11687.12   | 11687.12    | 7/3/2025 12:00:00 AM  | 7/7/2025 12:00:00 AM  | Telex Transfer
Reservation      | 1913622xxx | 37040529    | Dev___     | Agoda           | INR      | -417.40    | -417.40     | 7/6/2025              | 7/8/2025              | Telex Transfer  (negative = refund/cancel)
```

ISSUED variant — `AGODA SEPT 2025- AMT- 80280.25 ISSUED`:
```
INVOICE NO. | Booking ID | Guest name      | INVOICE AMT. | From Agoda | COMM. + GST
CANCEL      | 575899xxx  | AVI___ FROFETA  | 0            | 8431.50    | -8431.50
2370        | 1637618xxx | ALA___          | 11760        | 12045      | -285
```

## 4. Candidate canonical schema for `booking` records

| Field | Dtype | Source / derivation |
|---|---|---|
| `settlement_batch_id` | str | from filename (month + amount) |
| `settlement_amount` | decimal | parsed from filename `AMT ####.##` |
| `transaction_type` | enum {reservation, cancel, amend, credit_note} | derived: `Transaction type` if present; else heuristics — `INVOICE NO.='CANCEL'` → cancel; `CREDIT NOTE != 0` or string `AMEND` → amend; multi-id `5802 5803` → credit_note+new_invoice pair |
| `agoda_booking_id` | int64 (str safer; can be 9- or 10-digit) | coalesce(`Booking ID`, `Reference number`) |
| `property_id` | int64 | `Property ID` (always 37040529 — TMV) |
| `invoice_no` | str (e.g. `25-26/2436`, can be list `'2504, 2505'`) | normalize all `INVO[I]CE NO[.]` variants; split on comma to get list of internal Tally invoice nos |
| `guest_name` | str | `Guest name`; trim trailing `(rate*nights)` annotation |
| `rate_x_nights_annotation` | str / nullable struct {rate, nights} | regex `\(([\d.]+)\s*\*\s*(\d+)\)` or `\[…\*\d\]` from `Guest name` — implies the booking was rebilled at this rate per night for these nights; total = rate × nights |
| `booking_paid_by` | enum | `Booking paid by` (always 'Agoda') |
| `currency` | str | `Currency` if present, else 'INR' |
| `agoda_site_amount` | decimal | `AGODA SITE` / `site amt` — gross retail price displayed on Agoda; ≥ invoice_amount |
| `invoice_amount` | decimal | normalize `INVO[I]CE AMT[.]` — equals `from_agoda + comm_gst` exactly (verified) |
| `from_agoda` | decimal | `From Agoda` — net amount remitted by Agoda for this booking |
| `to_property` | decimal | `To property` (raw export only) — equals `from_agoda` |
| `commission_plus_gst` | decimal | `COMM[ ]?\+[ ]?GST` variants |
| `credit_note_amount` | decimal | `CREDIT NOTE` / `credit note` (default 0) |
| `amend_amount` | decimal | `amend amt` / `ament amt absoulte` (different files use opposite signs — needs reconciliation) |
| `check_in_date` | date | `Check-in date` (string `M/D/YYYY 12:00:00 AM` in old files; real datetime in MARCH/FEB files) |
| `check_out_date` | date | `Check-out date` |
| `payout_method` | str | `Payout method` (raw only; always 'Telex Transfer') |
| `reconciliation_diff` | decimal | `e-f =g` column — likely (invoice_amt − from_agoda) − comm_gst residual |

## 5. Join keys (priority)

1. **`agoda_booking_id`** — most stable; 10-digit numeric (some 9-digit, some short-format `575899211`). Present in raw export AND in annotated files (as `Booking ID` or `Reference number`). Best key for cross-file dedupe & for matching against Agoda payment statements.
2. **`invoice_no`** — internal Tally invoice number (`25-26/####` style; bare digits in sheet). Critical for join against Tally Sales Vouchers. Note multi-id rows (`'5802, 5803'`) require list-explode before joining; an invoice number can also be `CANCEL` or `0` (sentinel).
3. **`(guest_name, check_in_date)`** — fallback fuzzy key when invoice/booking_id missing or for Agoda-pay-statement matches that lack invoice numbers.
4. **`check_in_date` / `check_out_date`** — secondary disambiguation.
5. **`settlement_batch_id` × `from_agoda`** — for tying records back to bank credit on settlement date.

## 6. Formulas / derivations (verified)

- **`invoice_amount = from_agoda + commission_plus_gst`** — verified exact (max diff 2.3e-13) on 370-row September file.
- **`commission_plus_gst ≈ 28-30 % of invoice_amount`** observed (e.g. 1331.40/4704 = 28.3%, 3110/10500 = 29.6%). Includes Agoda commission + 18% GST on commission. No separate TCS/TDS columns seen — those are presumably netted upstream by Agoda (or applied at Tally posting, not in these sheets).
- **`rate*nights` notation in Guest name** (e.g. `Aakash Mundra (1554*2)`, `[2887.5*2]`, `[7243.95*2]`): means the booking was re-invoiced at `rate × nights` after a rate-change credit-note. Multi-row Booking IDs (`6106, 6122`) pair the credit-note voucher with the new invoice; both share one `agoda_booking_id`. Total of the row = rate × nights.
- **`AGODA SITE − INVOICE AMT.` reconciliation** (MARCH 759282 file, footer): `g+h+i = 1150516.30`, `f = 1140935.18`, `diff = 9581.12` — labels suggest cumulative reconciliation of site amount vs invoice amount.
- **TOTAL footer row** present in most files (last row, `Guest name == 'TOTAL'`); column sums must equal filename `AMT`. Validates the `from_agoda` column against settlement.

## 7. Data-quality issues / quirks

- Column-header typos pervasive: `INVOCIE` (vs INVOICE), `ament amt absoulte`, `AGODAT SITE`, `COMM+ GST` vs `COMM + GST` vs `comm + gst`. Need case+space+spelling-tolerant header normalizer.
- Two distinct schemas: **raw Agoda dump** (`Transaction type, Property ID, Currency, To property, Payout method`) and **manually-annotated** (`INVOICE NO., COMM+GST, CREDIT NOTE`). Loader must branch.
- `AGODA SEPT 2025- AMT- 80280.25 ISSUED.xlsx` — banner row `ISSUED SHEET` consumed columns; real headers in row 1. Skip 1 row.
- Date columns: half files store dates as strings `'9/7/2025 12:00:00 AM'`, half as real datetimes. Coerce.
- `Booking ID` / `Reference number` rendered as float (`1.929760e+09`) — must read with `dtype={'Booking ID': 'Int64'}` or convert.
- `INVOICE NO.` mixes int, str (`'5802, 5803'`, `'CANCEL'`, `'cancel'`, `'0'`) — keep as str.
- TOTAL footer rows must be filtered (`Guest name == 'TOTAL'` or rows where Booking ID is NaN and From Agoda is non-null).
- Some files have label rows in body (`MARCH 759282`: `g+h+i`, `f`, `-` reconciliation labels at end) — drop rows where `Guest name` is null AND `Booking ID` is null.
- Negative `From Agoda` values = cancellation refunds / chargebacks against the property; raw export shows zero/negative pairs (booking + cancellation in same batch).
- One Aug-2025 file (44912) is a tiny raw-export subset overlapping with the larger 581-row Aug-2025 file — possible duplicate ingestion risk; dedupe on `agoda_booking_id × from_agoda × check_in_date`.
- DEC 2025- 2030043.35: `comm + gst` column has dtype `object` (mixed numeric+string) — likely stray text. Coerce.
- DEC 2025- 2030043.35: footer row `429` has `'diff' / 14063.85` — manual reconciliation note.
- `Property ID` always `37040529` — Mangal View Residency on Agoda. Useful as constant assertion.

## 8. Open questions

1. Are TCS / TDS captured in these sheets or only on the Agoda-side payment statement? None visible here.
2. What does `e-f =g` formally compute? Expected = `invoice_amt - from_agoda - comm_gst` (=0) or = `agoda_site - invoice_amt`? Almost always 0; leftover formula label.
3. Convention for sign of `amend amt` / `credit note` differs between NOV and DEC files — confirm with finance.
4. Multi-invoice rows (`'5802, 5803'` or `'5868, 5869, 5870'`): is each Tally invoice for one night, or is one a CN against the other plus a fresh invoice? `(rate*N)` annotation suggests the latter — N invoices, each = rate.
5. Is `INVOICE NO.` here the bare suffix of `25-26/####` Tally numbers or a separate sequence? Numeric ranges (2342–6455) span the FY which fits.
6. ISSUED variant — what does ISSUED mean vs the regular SEPT 80280 file (same amount)? Possibly one is the invoice-issued summary, other the actual remittance.
7. Should negative `From Agoda` rows in raw export be modeled as separate `cancel` records or netted against the original Reservation row sharing the same `agoda_booking_id`?
