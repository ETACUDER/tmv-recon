# Invoices bucket — discovery

Source: `data/invoices/raw/transaction_detail20250428.xlsx`, single sheet `Sheet1`, **1,399 rows × 55 cols**. EZ PMS export. Each row = one transaction line within a folio. Folio rolls up to one Invoice. Period observed: invoices `2024-2025/1..4` (carryover) + `2025/2026/1..305`.

## 1. Schema (per column)

| col | dtype | null% | uniq | sample |
|---|---|---|---|---|
| `Transaction Type` | str | 0 | 1 | `FrontOffice` |
| `Reservation #` | obj | 1.5 | 391 | `6669`, `6803-1` |
| `Group Code` | float | 69.0 | 59 | `1635.0` |
| `Reservation Date` | str | 0 | 60 | `2025-03-27` |
| `Folio #` | int | 0 | 393 | `4844` |
| `Invoice #` | str | 14.2 | 304 | `2025/2026/96` |
| `Invoice date` | str | 14.2 | 28 | `2025-04-12` |
| `Arrival` | str | 0 | 44 | `2025-04-09` |
| `Dept.` | str | 0 | 44 | `2025-04-11` |
| `Room Type` | str | 0 | 6 | `Premium Room` |
| `Rate Type` | str | 0 | 3 | `CP` (CP/EP/MAP) |
| `Room #` | float | 2.5 | 39 | `301.0` |
| `Owner Name` | – | **100** | 0 | – |
| `Is Paymaster` | float | 2.5 | 1 | `0.0` |
| `Pax` | str | 0 | 12 | `2/0` |
| `Guest Name` | str | 0 | 298 | `indrajeet tiwari` |
| `VIP Status` | – | **100** | 0 | – |
| `Nationality` | str | 37.8 | 17 | `India` |
| `Market Code` | – | **100** | 0 | – |
| `Travel Agent` | str | 35.7 | 3 | `Booking.com` / `Agoda` / `Goibibo` |
| `Travel Agent Voucher #` | obj | 35.5 | 269 | `4559498628/5469177348` |
| `Business Source` | str | 5.9 | 5 | `AGODA`, `Rovers Network Pvt. Ltd.`, `BOOKING.com`, `DIRECT`, `Goibibo-MMT` |
| `Company Name` | str | 99.1 | 2 | `MANSHAPURN KARNI MATA…` |
| `Sales Person Name` | – | **100** | 0 | – |
| `Reservation Type` | str | 0 | 1 | `Confirm Booking` |
| `Booking Status` | str | 0 | 5 | `Checked Out`/`Cancel`/`Confirmed Reservation`/`Stayover`/`No Show` |
| `Bill To Name` | str | 0 | 297 | `indrajeet tiwari` |
| `RegNo.` | str | 98.3 | 5 | `29AAJCP0446R1ZP` (B2B GSTIN) |
| `Transaction` | str | 0 | 2 | `b2c` (1375) / `b2b` (24) |
| `Transaction Date` | str | 0 | 28 | `2025-04-09` |
| `Charge` | str | 37.9 | 12 | see §2 |
| `Extra Charge Type` | str | 82.9 | 1 | `Normal` |
| `HSN/SAC` | obj | 40.0 | 3 | `996311` / `RP` / `Extra Person` |
| `Settlement/Particular` | str | 62.1 | 8 | `UPI`/`Agoda`/`Cash`/`Credit Card`/`Debit Card`/`Goibibo`/`Round Off`/`Bank Transfer` |
| `Reference #` | obj | 58.8 | 366 | `24` |
| `User Name` | str | 0 | 4 | `frontoffice` |
| `Comment` | str | 84.1 | 212 | `EXTRA BREAKFAST C/IN…` |
| `Qty` | float | 82.9 | 3 | `1.0` |
| `Actual Rate(Configured Rate)` | int | 0 | 44 | `4500` |
| `Slab Information` | int | 0 | 3 | `0`/`12`/`18` |
| `Net Amount` | float | 0 | 196 | `2014.35` |
| `Discount Name`/`Discount %` | – | **100** | 0 | – |
| `Discount Amount` | int | 0 | 1 | `0` (always) |
| `Taxable Amount` | float | 0 | 196 | = Net Amount |
| `Tax Name` / `Tax %` / `Tax Amount` | mixed | 62.9 | – | `CGST` `6.0` `120.86` |
| `Tax Name.1` / `Tax %.1` / `Tax Amount.1` | mixed | 62.9 | – | `SGST` `6.0` `120.86` |
| `Adjustment(...)` | int | 0 | 1 | `0` (always) |
| `Gross Amount` | float | 0 | 194 | `2256.07` |
| `Settlement Amount` | float | 52.3 | 231 | `-2256.07` (negative on payment lines) |
| `Folio Status` | str | 0 | 3 | `Close` (1174) / `Void` (155) / `Active` (70) |

Always-null cols (drop on ingest): `Owner Name`, `VIP Status`, `Market Code`, `Sales Person Name`, `Discount Name`, `Discount %`. Constant cols: `Transaction Type=FrontOffice`, `Reservation Type=Confirm Booking`, `Discount Amount=0`, `Adjustment=0`, `Is Paymaster=0`.

## 2. Row-class breakdown

Rows split into three logical kinds:

A. **Charge lines** (`Charge` not null, `Settlement/Particular` null) — 869 rows. `Charge` distribution: `Room Charges` 605, `Room Posting` 207, `Late Checkout Charges` 15, `Extra mattress` 13, `Early check in` 7, `Cancellation Revenue` 6, `No Show Revenue` 4, `Extra Person` 3, `ROOM UPGRADE` 3, `SPOILED LINEN` 3, `LOST KEY` 2, `Extra Breakfast` 1.
B. **Settlement lines** (`Charge` null, `Settlement/Particular` not null) — 530 rows. Carry `Settlement Amount` (always negative on these), `Net/Tax/Gross = 0`. Modes: UPI 188, Agoda 174, Cash 66, Credit Card 64, Debit Card 18, Goibibo 14, Round Off 5, Bank Transfer 1.
C. **Voided/cancelled lines** — `Booking Status ∈ {Cancel, No Show}` and/or `Folio Status ∈ {Void, Active}`. All amounts zero. `Charge=Cancellation Revenue` (6) and `No Show Revenue` (4) are the explicit cancellation markers; other zero-rows (e.g. Room Charges with Slab=0, Net=0) are Cancel/Void leftovers.

`HSN/SAC` taxonomy: `996311` (taxable hotel accommodation, 630 rows) | `RP` = Room Posting tracker, untaxed internal entry (207) | `Extra Person` (3, taxed at 18%) | NaN on settlement and zero-value cancel rows.

## 3. Folio→Invoice rollup verification

- 1,201 rows have `Invoice #`. **304 distinct invoices**, **393 distinct folios**.
- 1 folio = 1 invoice (no folio splits across invoices). Invoice → folios: **all 1:1** (no multi-folio invoices in this dataset).
- Lines per invoice: median 3, mean 3.95, max 14.
- **Math check**: `Σ Net + Σ Tax Amount + Σ Tax Amount.1 == Σ Gross` for every invoice (0 mismatches > ₹1). Tax-vs-net ratio is 12.0000% (±0.002) for slab=12, 18.0000% for slab=18 — clean.
- 198 rows lack `Invoice #` → all are `Folio Status ∈ {Void, Active}` and `Booking Status ∈ {Cancel, Confirmed Reservation, Stayover, No Show}`. These are open/voided folios that never produced an invoice.
- Note: 27 rows on 13 invoices have `Folio Status=Void` despite having an `Invoice #` and `Booking Status=Checked Out` (e.g. `2025/2026/212`, `…/259`, `…/38`, `…/206`, `…/135/136/297`). All carry zero amounts. These look like cancelled-after-issue invoices; flag as `void_after_issue` and exclude from sales totals (or post a credit note).

## 4. GST patterns

Only one effective rate combination on revenue: **CGST 6% + SGST 6% = 12% total** on HSN `996311` (slab `12`, 517 lines). Two rows at **CGST 9% + SGST 9% = 18%** on `Extra Person` (slab `18`). No IGST observed → all bookings treated as intra-state (Rajasthan).

Tally convention says `SALE ACCOMODATION GST @ 5%` with CGST 2.5/SGST 2.5. **The PMS data is at 12% (6+6), not 5%.** Resolve before mapping: either Tally ledger label is misleading and the actual posting is 12%, or hotel switched regimes — confirm with accountant.

`Tax Name` variants observed: `CGST`, `CGST 6%`, `CGST @ 9%` (and SGST mirror). Normalize on ingest.

## 5. Invoice # patterns

- `2025/2026/###` — 854 rows
- `2025/2026/##` — 339 rows
- `2025/2026/#` — 6 rows
- `2024-2025/#` — 2 rows (carryover; only 2 invoices: `2024-2025/1`, `2024-2025/4`)

Normalizer: parse `^(\d{4})[/-](\d{4})/(\d+)$` → emit `{YY}-{YY}/{####}` (zero-pad to 4) → `2025/2026/96` ⇒ `25-26/0096`. Confirm desired pad width — sample brief shows `25-26/126` unpadded, so default = no padding, keep numeric as-is.

## 6. Candidate join keys (priority)

1. **`Invoice #`** (normalized) — primary, links to Tally voucher_number.
2. **`Folio #`** — secondary, unique within PMS, links payments-against-folio.
3. **`Reservation #`** — for OTA/booking-side joins (note suffixes `-1/-2` for split reservations sharing a Group Code).
4. **`Travel Agent Voucher #`** — OTA cross-ref (Booking.com/Agoda/Goibibo voucher); 269 unique values, sometimes slash-joined (`A/B`).
5. **`Group Code`** — links related reservations (corporate/group bookings, 59 codes).
6. **`Bill To Name` / `Guest Name`** — fuzzy-join fallback only; near-duplicate (`Bill To Name` differs from `Guest Name` only on B2B invoices where Bill To = company).
7. **`RegNo.`** — GSTIN for B2B reverse-lookup (24 rows, 4 GSTINs).
8. Dates: prefer `Invoice date` for ledger; `Arrival/Dept.` for stay window; `Transaction Date` for line posting.

## 7. Canonical schema (ETL output)

**Invoice level** (one row per `Invoice #`):
- `invoice_no` (normalized `25-26/####`), `invoice_date`, `arrival`, `dept`, `nights`
- `folio_no`, `reservation_no`, `group_code`
- `guest_name`, `bill_to_name`, `nationality`, `pax`
- `room_type`, `rate_type`, `room_no`, `actual_rate`
- `transaction_kind` (`b2c`/`b2b`), `regno_gstin` (nullable), `company_name` (nullable)
- `travel_agent`, `travel_agent_voucher`, `business_source`
- `net_amount`, `cgst_amount`, `sgst_amount`, `igst_amount` (=0 here), `gst_rate` (12 / 18), `gross_amount`
- `settlement_modes` (set/list — invoice can have multi-mode settlement), `settlement_total`
- `booking_status`, `folio_status`, `is_void_after_issue` (bool — Void+invoiced)
- `hsn_codes` (set)
- `source_row_ids` (list of EZ row indices for traceability)

**Folio/line level** (preserve raw lines for audit):
- `folio_no`, `invoice_no`, `line_seq`, `line_kind` (`charge`/`settlement`/`zero`)
- `charge`, `hsn`, `qty`, `net`, `tax_cgst`, `tax_sgst`, `gross`
- `settlement_mode`, `settlement_amount`, `reference_no`, `comment`

## 8. Quirks / data quality

- 198 rows have no `Invoice #` (cancelled/active folios) — exclude from Tally sales push.
- 13 invoices are **issued then voided** (`Folio Status=Void`, all amounts 0) — needs business rule: skip vs credit-note.
- `Discount Amount`/`Discount Name`/`Adjustment` are all zero/null in this dump → no discount logic implemented in PMS export.
- `Tax Name` has 3 spellings (`CGST`, `CGST 6%`, `CGST @ 9%`) — normalize.
- `Reservation #` mixes int + `\d+-\d` (split-reservation suffix) → keep as string.
- `HSN/SAC=RP` is not a real HSN — internal `Room Posting` marker; `Net Amount` exists but tax is null. Confirm whether RP rows are duplicates of Room Charges (they sit alongside taxed Room Charges in same folio) or genuinely separate postings.
- `Settlement Amount` is negative on payment lines (PMS sign convention). Flip sign when comparing to bank statements.
- 2 rows have `Net Amount = -0.01` (rounding artifact, ignore).
- `RegNo.` exists on rows where `Bill To Name` ≠ `Guest Name` (B2B invoices) — use as B2B detector alongside `Transaction='b2b'`.
- `Travel Agent Voucher #` sometimes `A/B` slash-joined (multi-voucher reservations) — split on `/` for OTA matching.
- `Business Source=Rovers Network Pvt. Ltd.` (308 rows) is a channel-manager source separate from per-OTA `Travel Agent` field; use Travel Agent first, fall back to Business Source.
- Tally ledger says 5% GST; PMS data is 12% (and a tiny 18% slice). **Reconcile before automation.**

## 9. Open questions

1. Tally ledger `SALE ACCOMODATION GST @ 5%` vs PMS 12% — which is correct for FY 2025-26? Single ledger or split by rate?
2. For the 13 void-after-issue invoices, post credit notes or skip?
3. `Room Posting` (`RP`, 207 rows) — same revenue as `Room Charges` already-counted, or a separate posting that must also flow to Tally? They appear as additional lines in the same folio with non-zero `Net Amount` but no tax — likely duplicate of Room Charges in another view; confirm.
4. Invoice numbering format for Tally: `25-26/126` plain or zero-padded `25-26/0126`?
5. OTA settlement timing: `Settlement/Particular=Agoda/Goibibo` represents OTA-payable, not received cash — should this map to a separate ledger (e.g. `Agoda Receivable`) rather than `Sundry Debtors`?
6. How are `Group Code`-linked sibling reservations (e.g. folios 82+83 sharing code 1630) reconciled — separate invoices each, or one consolidated B2B invoice?
7. Carryover `2024-2025/1` and `…/4` — include in current-year recon or skip?
