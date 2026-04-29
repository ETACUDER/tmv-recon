# Recon flow + ER

## Narration in `data/tally/raw/`?

Inspected — **none of the 30 tally-bucket files carry narration columns.**
They are byte-identical (or cosmetic-diff) copies of the same Agoda settlement
sheets, PTM dumps, and bank statements that live in `booking/processed/` and
`payments/processed/`. There is no Tally Day Book / Voucher export in this
bundle. So the narrations Urvashi enters in Tally are **constructed** from
input columns; we have to rebuild them in the ETL.

The two narration templates seen in the meeting screenshots:

```
Sales voucher (per invoice):
   "INVOICE NO -<25-26/####> <GUEST NAME UPPERCASED>"
   ← built from EZ:  Invoice # → 25-26/####
                     Guest Name (upper)

Journal voucher (per payment, when matched to an invoice):
   "BEING PAID THROUGH <MODE> AGAINST INVOICE NO:<25-26/####> <GUEST>"
   ← built from PTM: Payment_Mode (UPI/CREDIT_CARD/UPI_CC)
                     matched invoice_no
                     pos_guest_name (UDF2) or matched invoice's Guest Name
```

Reverse-engineering for the matcher: the `INVOICE NO:<25-26/####>` token in
a real Tally narration would be the reliable bridge from Tally Journal back
to EZ invoice — but we never received that real Tally export.

---

## End-to-end recon flow (mermaid)

```mermaid
flowchart TB
  subgraph SRC["SOURCES (raw)"]
    EZ["EZ sheet<br/>transaction_detail*.xlsx<br/>1399 line items"]
    PTM["PTM Paytm raw<br/>123-col Dec-Feb<br/>316 txns"]
    BANK["Indian Bank<br/>statements Jul-Mar<br/>1363 lines"]
    AGO["Agoda batches<br/>20 settlement files<br/>Aug 25 - Apr 26"]
    GOMT["GoMT pooled<br/>CSV Apr-Oct 25<br/>295 bookings"]
  end

  subgraph CANON["CANONICAL FACTS<br/>data/recon/canonical/"]
    INV["fct_invoice<br/>304 rows<br/>Net + CGST + SGST = Gross"]
    PMT["fct_payment<br/>316 rows<br/>Settled = Gross - Comm - GST"]
    BNK["fct_bank<br/>1363 rows<br/>UTR extracted from desc"]
    BK["fct_booking<br/>3476 rows<br/>(rate*nights), CN pairs"]
  end

  subgraph MATCH["MATCH LAYER<br/>data/recon/matches/"]
    PB["ptm_bank<br/>amount + date + ONE 97 COM<br/>146/316 txns"]
    PI["ptm_invoice<br/>amount + date + guest fuzzy<br/>blocked: period mismatch"]
    BI["booking_invoice<br/>invoice_no exact + fuzzy<br/>40/3476 (period)"]
  end

  subgraph TLY["TALLY (target)"]
    SLS["Sales voucher<br/>Sundry Debtors / Sales+CGST+SGST<br/>narration: INVOICE NO -...GUEST"]
    JNL["Journal voucher<br/>Dr CARD/UPI/PAYTM/G PAY<br/>Cr Sundry Debtors<br/>New Ref = invoice_no"]
    SIG["tally/raw signal<br/>(file-presence proxy)<br/>1994/5459 already booked"]
  end

  EZ --> INV
  AGO --> BK
  GOMT -.->|extractor TBD| BK
  PTM --> PMT
  BANK --> BNK

  PMT -- "amount=credit AND value_date~=settled_dt AND desc~='ONE 97'" --> PB
  PMT -- "amount~=invoice.gross AND txn_dt in [inv_dt, +7d] AND fuzzy(VPA/UDF2 vs guest)" --> PI
  BK  -- "invoice_no exact" --> BI
  BK  -- "guest fuzzy + arrival match" --> BI

  INV --> SLS
  PI --> JNL
  PB -. UTR/payout cross-check .-> JNL
  BI -. invoice_no link .-> JNL

  SIG -.cross-checks.-> INV
  SIG -.cross-checks.-> PMT
  SIG -.cross-checks.-> BK

  classDef gap fill:#fee,stroke:#c00,color:#900;
  class PI,GOMT gap;
```

---

## ER: keys + cardinalities

```
                                EZ                                    Agoda
                          ┌────────────┐                       ┌────────────────┐
                          │ Invoice #  │                       │ agoda_booking_id│
                          │ Folio #    │                       │ invoice_no list │
                          │ Reservation│                       │ rate*nights     │
                          │ Guest Name │   travel_agent_       │ guest_name      │
                          │ Bill To    │  voucher cross-link   │ checkin/checkout│
                          └─────┬──────┘ ←──── (sparse) ────── └─────┬──────────┘
                                │                                    │
                                │ 1:1 folio↔invoice (this dump)      │ 1 booking → ≥1 invoice
                                │                                    │ (rate-change CN pair)
                                ▼                                    ▼
                          ┌──────────────────────────────────────────────┐
                          │              fct_invoice (304)               │
                          │ invoice_no • invoice_date • guest • travel_  │
                          │ agent • net • cgst • sgst • gross • channel  │
                          └──────────────────┬───────────────────────────┘
                                             │ inv.invoice_no
                                             │  (matched)
                       ┌─────────────────────┼──────────────────────┐
                       │                     │                      │
                  ┌────┴───────┐      ┌──────┴────────┐       ┌─────┴────────┐
                  │ fct_payment │ many │ fct_bank      │       │ fct_booking  │
                  │ (PTM, 316)  │  to  │ (1363)        │       │ (Agoda, 3476)│
                  │             │ many │               │       │              │
                  │ txn_id PK   │←─────┤ ref_no/utr_   │       │ booking_id   │
                  │ payout_id   │ amt+ │ extracted     │       │ invoice_no   │
                  │ utr (paytm) │ date │ value_date    │       │ guest_name   │
                  │ amount_gross│ ────►│ credit/debit  │       │ checkin      │
                  │ commission  │      │ description   │       │ rate*nights  │
                  │ gst (18%)   │      │ (NEFT/UTR)    │       │ comm+gst     │
                  │ settled_amt │      └───────────────┘       │ credit_note  │
                  │ payment_mode│                              └──────────────┘
                  │ utr,rrn     │
                  │ pos_guest   │
                  └─────────────┘
                          ▲
                          │ join keys (priority order)
                          │
      ┌───────────────────┴───────────────────────────────────────┐
      │ 1. UTR / Paytm payout: PTM ⊕ batch → bank credit          │
      │    (Paytm UTR ≠ NEFT UTR — link is amount + date + narr.) │
      │                                                            │
      │ 2. Amount + date window:                                   │
      │    PTM.amount_gross ≈ Invoice.gross                        │
      │    AND inv_date ≤ txn_dt ≤ inv_date + 7d                   │
      │                                                            │
      │ 3. Guest fuzzy:                                            │
      │    PTM.UDF2 (LASTNAME/FIRSTNAME) or VPA-handle             │
      │    fuzz.token_set_ratio(EZ.guest_name) ≥ 80                │
      │                                                            │
      │ 4. Booking → Invoice:                                      │
      │    Agoda.booking_id = EZ.travel_agent_voucher              │
      │    (sparse) OR guest+arrival fuzzy                         │
      │                                                            │
      │ 5. PDF receipt invoice_no — UNAVAILABLE                    │
      │    (LIC PDFs were misclassified, real ones never delivered)│
      └───────────────────────────────────────────────────────────┘
```
