# Payments + Tally bucket discovery

Inspected 2025-12 / 2026-01 / 2026-02 PTM raw, 5 processed PTM/PTM-ROOFTOP/F&B,
3 Indian Bank statements, 12 PrmPayRcpt PDFs, all 30 tally/raw files.

## PTM raw schema (`data/payments/raw/PTM*.xlsx`)

123 columns, 1 sheet per file (sheet name = month label, e.g. `'DECEMBER 2025'`).
~75-110 rows/month. Values are stored Excel-quoted (leading `'`) for ID-like cols.

The wide schema is Paytm's full transaction dump. Of 123 cols, only ~30 ever
hold a non-null. Real signal lives in:

| Col idx | Name | Dtype | Sample |
|---|---|---|---|
| 0 | `Transaction_ID` | str | `'20251201010800000202192837815411546'` |
| 1 | `Order_ID` | str | `'2025120110045900407211054677'` |
| 4 | `Transaction_Date` | str | `'2025-12-01 10:05:08'` |
| 5 | `Updated_Date` | str | `'2025-12-01 10:05:12'` |
| 7 | `Status` | str | `SUCCESS` / `FAILED` |
| 14 | `Amount` | float | gross e.g. `34267.20` |
| 15 | `Commission` | float | `1367.26` (NaN on FAIL or unsettled) |
| 16 | `GST` | float | `246.11` |
| 18 | `Payout_ID` | str | `AWSPG2025...` (one per UTR batch) |
| 20 | `UTR_No.` | str | `'YESAP53365113871'` (yes-bank UTR) |
| 21 | `Payout_Date` | str | `'2025-12-01 00:01:00'` |
| 22 | `Settled_Date` | str | `'2025-12-02 10:42:21'` |
| 23 | `Payment_Mode` | str | `CREDIT_CARD`/`DEBIT_CARD`/`UPI`/`UPI_CREDIT_CARD` |
| 24 | `Issuing_Bank` | str | `AMEX`/`HDFC`/`ICICI`/... |
| 44 | `Credit/Debit_Card_Last_4_Digits` | str | `'5009'` |
| 45 | `Bank_Transaction_ID` | str | mirrors RRN |
| 48 | `Settled_Amount` | float | net (Amount - Comm - GST) |
| 54 | `Customer_VPA` | str | `praveen.lic@okicici` (UPI only, ~25-40% of rows) |
| 67 | `RRN` | str | 12-digit ARN/RRN, == Bank_Transaction_ID |
| 73 | `Card_Scheme` | str | `VISA`/`MASTER`/`AMEX`/`RUPAY`/`DINERS` |
| 105 | `ARN` | str | 23-char (subset, ~17/107) |
| 110 | `UDF2` | str | guest name from POS terminal e.g. `'GREWAL/HARINDER'` |

The other ~93 cols are 100% null in the months sampled. Failed txns (`Status='FAILED'`) carry no Commission/GST/UTR/Settled rows.

## PTM processed schema (and diff vs raw)

Slim 8-col extract (sometimes 9 if `Issuing_Bank` kept). Same schema across
`UPI STATMENT__*`, `PTM ROOFTOP__*`, `F&B UPI__*`:

```
Transaction_Date | Amount | Commission | GST | Settled_Amount | UTR_No. | Settled_Date | Payment_Mode [| Issuing_Bank]
```

Examples:
- `UPI STATMENT__PTM - JULY 2025 (1).xlsx` shape (558, 8) — header `Updated_Date` instead of `Transaction_Date` (one inconsistency).
- `PTM ROOFTOP__TMV ROOFTOP - DECEMBER 2025.xlsx` shape (795, 9) — adds `Issuing_Bank`.
- F&B file `F&B UPI__PTM - JULY 2025 (F&B) (1).xlsx` has a merged title row `UPI STATEMENT F&B JULY 2025` so headers actually live on row 2; reader needs `header=1`.

**Diff vs raw**: only those 8-9 columns survive. **Nothing manually added** — no Invoice_No, no Customer_Name, no Folio. Sheet names are random UUID-fragments (`'65c13b64-a75d-4bc7-9bb9-6c42290'`) for some, plain month label for others.

Implication: processed files are pure column-subsets of raw — they LOSE the `Customer_VPA`, `RRN`, `UDF2 (guest name)`, `Card_Scheme`, `Issuing_Bank` (mostly), `Order_ID` that we need for joining. **Recommend ETL parses RAW directly** and ignores Urvashi's slim processed copies.

## Bank statement schema (Indian Bank — both 7223534417 main and 8150353104 rooftop)

Indian Bank web export (Excel). Header lives at row 21-22 (rooftop has 8 cols, main has 6). 18-21 lines of metadata above.

Metadata block (rows 1-20):
```
INDIAN BANK / UDAIPUR GOVERDHAN / IFSC CODE :IDIB000U506
Account Number : 7223534417  (main)  |  8150353104  (rooftop)
Product type :  CA-GEN-PUB-METRO/URBAN-I  |  CA-IND ASPIRE SILVER- IN
Customer: THE MANGAL VIEW RESIDENCY  |  TMV Rooftop Restaurant
Statement Date : Wed Oct 01 09:...
Cleared Balance : <opening>
Statement of Account from <DD/MM/YYYY> to <DD/MM/YYYY>
```

Transaction header:
- Main: `Value Date | Description | Chq No/REF No/UTR No | Debit Amount | Credit Amount | Balance` (DEC file drops the UTR col → 5 cols).
- Rooftop: `Value Date | Post Date | Remitter Branch | Description | Chq No/REF No/UTR No | Debit Amount | Credit Amount | Balance` (8 cols).

`Description` is the gold field — narration carries:
- aggregator name: `ONE 97 COM` (Paytm), `MAKEMYTRIP`, `ETERNAL LI` (Zomato), `BOOKING.CO`, etc.
- embedded UTR after `NEFT/<bank>/<utr>/...`, e.g. `NEFT/YESB/YESBN12025090102239225/ONE 97 COM/`
- For UPI direct credit: `BY UPI CREDIT UPI/<rrn>/UPI Payment XXXXX<masked>/<payer-vpa> <ifsc>/<payer-name>`.

`Balance` is string `'609894.61CR'` (CR/DR suffix) — needs stripping. `Debit Amount`/`Credit Amount` come as float OR space-padded string `' '` for empty.

UTR in `Chq No/REF No/UTR No` column = the same UTR as in description, when present (main account always; rooftop usually empty for this col since it's UPI-heavy and only carries Description).

## PDF receipt schema (CRITICAL — these are NOT TMV)

**ALL 12 `PrmPayRcpt-*.pdf` are LIC of India Renewal Premium Receipts**, not hotel PMS receipts. First-line of every PDF:
```
Collecting Center : A001 Branch Code : 102
LIC of India, Banswara Branch
RENEWAL PREMIUM RECEIPT
Received with thanks Rs. 2,727.00 from policyholder Shri/Smt.Lilaram Trivedi
```

Fields present (LIC, not useful for TMV):
- `Transaction No.` (LIC's own, e.g. `37040072`)
- `Date ( Time )` `21/07/2025 ( 13:42:34 )`
- Policyholder name, Policy No, Plan, Inst. Prem, Total Premium, CGST, SGST, Total Amt, Next Due, Branch | Agency Code
- `Paid by Cash/Card/QR/SR : 2,727.00`
- LIC GSTIN `08AAACL0582H2ZL`

**No invoice number, no guest name, no booking ID, no UTR, nothing TMV-related.** They were collected at LIC Banswara Branch, not by TMV.

→ The hypothesised "PrmPayRcpt is bridge between EZ invoice and PTM payment" is **WRONG for this dataset**. These files appear to have been mistakenly bundled (probably someone's personal LIC receipts). They should be moved out of `data/payments/raw/` or quarantined.

The actual EZ↔PTM invoice bridge will need to come from another source (EZ PMS export's payment-receipt section, or POS slip PDFs we haven't received).

## Tally-bucket inspection

`data/tally/raw/` contains 30 files. By MD5 against the underlying real files (followed symlinks):
- 19 byte-identical to a file in `data/payments/processed/`
- 9 byte-identical to a file in `data/booking/processed/`
- 2 cosmetic-DIFF (same content, different `.xls` save metadata): `INDIAN BANK ROOFTOP__...NOV 2025.xls`, `AGODA__AGODA OCT -802760.07 AMT.xlsx`
- 2 orphans (filename not present in payments/booking with that exact name):
  - `AGODA__AGODA SEPT 2025- AMT- 80280.25.xlsx` (a near-twin of `AGODA__AGODA  SEP 2025 AMT 80280.25 RS.xlsx` in booking/processed)
  - `INDIAN BANK__STATEMENT OF ASCCOUNT NOV 2025.xls` (note `ASCCOUNT` typo — peer in payments/processed is named `Statement Of Account - NOVEMBER 2025-imp.xls`)

**Verdict: there is NO actual Tally export here.** No journal vouchers, no Dr/Cr lines, no Sundry-Debtors postings, no bill-wise New Refs. The "tally bucket" is just a redundant collection of the same agent statements + bank statements, dumped from `meet-recording/tallyData/`. The Tally posting that the todo describes (Dr CARD/UPI/PAYTM/G PAY, Cr Sundry Debtors) is NOT in any of these files — we have not received Tally's day-book / journal export. Treat tally/raw/ as a duplicate; either delete or keep it only as a manifest of "what Urvashi handed to the accountant".

## Formulas (verified across DEC25 + JAN26 + FEB26 raw, 214 settled rows)

- `Settled_Amount == Amount - Commission - GST` exact (max abs diff 7.3e-12, 0 rows >0.01). **Identity holds**.
- `GST/Commission` cluster tightly at **18%** (median 0.18000, mean of nonzero 0.180; the 0.153 mean above is dragged by zero-comm rows).
- Commission rate per `Payment_Mode` × `Card_Scheme`:

| Mode | Scheme | n | rate (mean) |
|---|---|---|---|
| CREDIT_CARD | AMEX | 4 | 3.99% |
| CREDIT_CARD | DINERS | 1 | 2.99% |
| CREDIT_CARD | MASTER | 30 | 2.93% (mostly 2.99%, some 1.80% RuPay-equiv, 3.50% premium) |
| CREDIT_CARD | RUPAY | 4 | 1.99% |
| CREDIT_CARD | VISA | 18 | 2.93% |
| DEBIT_CARD | MASTER | 31 | 3.50% |
| DEBIT_CARD | VISA | 27 | 2.90% (one 0.40% outlier — small txn) |
| UPI_CREDIT_CARD | (n/a) | 7 | **2.50% flat** |
| UPI | — | 91 | **0.00%** (zero-MDR) |

- Effective fee % `(Comm+GST)/Amount`: CREDIT_CARD ~3.34%, DEBIT_CARD ~3.70%, UPI 0%, UPI_CC 2.95%.

→ Rule for ETL: when reconciling a PTM row to a bank credit, expect bank `Credit Amount == Settled_Amount` (already net). When reconciling to invoice gross, use `Amount`. Commission/GST is the ledger-gap that needs a separate Tally posting.

## Candidate join keys (priority order)

1. **`UTR_No.`** (PTM) ↔ regex from bank `Description` `NEFT/<bank>/(<utr>)/...` ↔ bank `Chq No/REF No/UTR No`. **One-to-many**: one UTR settles multiple PTM rows in one Payout_ID; the bank credit on that UTR equals `sum(Settled_Amount where UTR_No.=X)`. Ex: `YESAP53365113871` settles 3 DEC-1 txns on PTM, lands as one credit `7830.08` on bank 02/12.
2. **`Payout_ID`** ↔ logical batch-key (parents many PTM rows under one UTR). Useful intra-PTM grouping.
3. **`RRN` / `Bank_Transaction_ID`** ↔ for UPI direct (non-PTM) credits, the rooftop bank narration `BY UPI CREDIT UPI/<rrn>/...` exposes the RRN. Match on the 12-digit token.
4. **`Settled_Date` (date-only) ± 1 day** ↔ bank `Value Date`. Use as fallback / sanity, not primary.
5. **`Amount` (gross)** ↔ EZ invoice `total_amount`. Many-to-many for collisions; combine with date window.
6. **`Customer_VPA`** ↔ guest UPI handle (only useful for repeat guests; not in EZ).
7. **`UDF2`** ↔ guest name fuzzy match to EZ booking. Format `LASTNAME/FIRSTNAME` (POS-terminal style). Sparse (~40/107 rows for DEC).
8. **PDF invoice_no ↔ EZ invoice_no** — **NOT AVAILABLE** because PDFs are LIC noise. This bridge is unbuilt.

## Canonical payment schema (proposed)

| Field | Type | Source | Notes |
|---|---|---|---|
| `txn_id` | str (PK) | PTM `Transaction_ID` | unique per row |
| `order_id` | str | PTM `Order_ID` | aggregator order ref |
| `txn_dt` | datetime (Asia/Kolkata) | PTM `Transaction_Date` | naive in source |
| `status` | enum | PTM `Status` | SUCCESS / FAILED |
| `amount_gross` | Decimal(12,2) | PTM `Amount` | invoice-side |
| `commission` | Decimal(12,2) | PTM `Commission` | NaN on FAILED |
| `gst` | Decimal(12,2) | PTM `GST` | always 18% of commission |
| `settled_amount` | Decimal(12,2) | PTM `Settled_Amount` | bank-side |
| `payout_id` | str | PTM `Payout_ID` | batch parent |
| `utr` | str | PTM `UTR_No.` | join to bank |
| `payout_dt` | datetime | PTM `Payout_Date` | |
| `settled_dt` | datetime | PTM `Settled_Date` | |
| `payment_mode` | enum | PTM `Payment_Mode` | CREDIT_CARD / DEBIT_CARD / UPI / UPI_CREDIT_CARD |
| `card_scheme` | str (nullable) | PTM `Card_Scheme` | VISA/MASTER/AMEX/RUPAY/DINERS |
| `card_last4` | str (nullable) | PTM `Credit/Debit_Card_Last_4_Digits` | |
| `issuing_bank` | str (nullable) | PTM `Issuing_Bank` | |
| `customer_vpa` | str (nullable) | PTM `Customer_VPA` | UPI only |
| `rrn` | str (nullable) | PTM `RRN` (== `Bank_Transaction_ID`) | |
| `arn` | str (nullable) | PTM `ARN` | |
| `pos_guest_name` | str (nullable) | PTM `UDF2` | LASTNAME/FIRSTNAME |
| `merchant_id` | str | PTM `MID` | constant per outlet |
| `outlet` | enum | filename | FRONT_OFFICE / ROOFTOP / FB |
| `source_file` | str | filename | provenance |
| `_invoice_no` | str (nullable) | **JOIN-DERIVED** | from EZ amount+date+name match (no direct key in current data) |

Bank statement lines parse into a parallel `bank_txn` schema:

| Field | Type | Notes |
|---|---|---|
| `account_no` | str | `7223534417` main / `8150353104` rooftop (from metadata block) |
| `value_dt` | date | parsed `Value Date` (DD/MM/YYYY) |
| `post_dt` | date (nullable) | rooftop only |
| `description` | str | full narration |
| `utr` | str (nullable) | from `Chq No/REF No/UTR No` OR regex from description |
| `debit` | Decimal(12,2) (nullable) | strip blanks |
| `credit` | Decimal(12,2) (nullable) | strip blanks |
| `balance` | Decimal(12,2) | strip CR/DR suffix |
| `aggregator` | str (derived) | regex over description: ONE 97 COM/MAKEMYTRIP/ETERNAL/etc |
| `payer_vpa` | str (nullable) | from UPI narration |
| `payer_name` | str (nullable) | from UPI narration |

## Quirks / data quality

- All ID-like cells in raw PTM exports are stored with leading apostrophe (`'<id>'`). pandas reads them with quotes literally — strip in ETL.
- `Settled_Amount` and friends are NaN for `Status='FAILED'` (~20-25% of rows). Drop or flag.
- F&B file `F&B UPI__PTM - JULY 2025 (F&B) (1).xlsx` has a 1-row title above the header — needs `header=1`.
- Sheet name varies: month label OR random GUID-fragment. Always read sheet 0.
- `Updated_Date` vs `Transaction_Date`: processed files alternately use either as the only timestamp column (e.g. JULY uses Updated_Date, SEPTEMBER uses Transaction_Date). Pick `Transaction_Date` from raw to be canonical.
- Bank `Balance` column is string `'609894.61CR'` not numeric.
- Bank Description has trailing/leading whitespace and embedded `\n` in long narrations.
- Files show up duplicated as `... (FRONT OFFICE).xlsx` and `... (FRONT OFFICE1).xlsx` — same month, two pulls. Need dedup on `Transaction_ID` after concat.
- Two distinct bank accounts (front-office 7223534417, rooftop 8150353104) — bank statement narration is the only way to know which account a credit landed in (besides the file name).
- `Issuing_Bank` only populated for card txns (not UPI).
- `Card_Scheme` MASTER 1.80% rows are RuPay-on-MASTER (or older mis-classification); not material for ETL but watch.

## Open questions

1. **Where are the actual TMV payment receipts?** EZ PMS exports? The 12 `PrmPayRcpt-*.pdf` files are LIC personal receipts mistakenly bundled — should be removed from `data/payments/raw/`.
2. **Where is the real Tally journal export?** Currently `data/tally/raw/` is just duplicates. We need Tally's daybook / journal voucher export (Dr/Cr lines with bill-wise refs) to confirm posting status. The `tally-recon-todo.md` says the Tally posting exists "Dr CARD/UPI/PAYTM/G PAY, Cr Sundry Debtors, bill-wise New Ref = invoice no" — that is the join key we actually need. Without it, the EZ↔Bank reconciliation has no third leg.
3. **How to bridge PTM → EZ invoice?** Without receipt PDFs, fall back to (UDF2 guest-name fuzzy + Amount + date-window) match against EZ folio. Confirm acceptable confidence with Urvashi or get an EZ payment-allocation export.
4. **MakeMyTrip / Booking.com / Zomato (Eternal Li)** credits in bank statement aren't in the PTM file — separate aggregator data sources needed (MMT statement, Booking.com payout report). Confirm scope: are they in `data/booking/`?
5. The bank rooftop UPI narration has `XXXXX79158` masked-account followed by VPA + IFSC + payer-name — confirm if `payer_vpa` extraction is unambiguous (some narrations may break the format).
6. F&B and PTM ROOFTOP processed files exist but raw equivalents only for FRONT OFFICE. Are F&B / ROOFTOP raw exports available somewhere?
