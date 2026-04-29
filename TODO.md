# TODO — when the real Tally data arrives

Current state in `docs/status-2026-04-28.md`. This file is the action queue for the moment Urvashi (or anyone with Tally access) sends one of:

- `<id>.tcb` — Tally backup file
- The folder `C:\TallyPrime\Data\<numeric-id>\` zipped
- `Day Book.xml` + `Vouchers.xml` + `Ledgers.xml` from Tally → E: Export

OR creates the test company `TMV Recon Test` on the VM via RDP (one-time, 30 sec).

## Immediate (when backup lands)

- [ ] **Restore on VM**: drop into `C:\Users\Public\TallyPrime\data\<id>\` (or run Tally → R: Restore on the .tcb). Tally auto-loads on next launch.
- [ ] **Update `.env`** `TALLY_COMPANY="THE MANGAL VIEW RESIDENCY Final"` (or whatever the real name is).
- [ ] Run `.venv/bin/python -m tmv_recon.tally.round_trip` — confirms Mac→VM→Tally→Mac round-trip works against the real company.
- [ ] Run `tmv-recon-pull --report list_companies` to verify the loaded company name.

## ETL — pull live signals from Tally

- [ ] **Build `etl/extract/tally_daybook.py`** — call `connectors.day_book(from, to)` over FY 25–26, save to `data/recon/canonical/tally_daybook.csv`. One row per voucher, `narration` field carries the canonical `INVOICE NO:<25-26/####>` token.
- [ ] **Build `etl/extract/tally_pending.py`** — call `connectors.ledger_outstandings("CARD / UPI / PAYTM / G PAY")` and same for `Sundry Debtors`. Output `data/recon/canonical/tally_pending_<ledger>.csv`. **This is the on-account backlog — the actual recon surface area.**
- [ ] **Add real signal to `tally_signal.py`** — replace file-presence proxy with: row in `tally_daybook.csv` with matching invoice/UTR ⇒ booked. Marries our extracted invoices/payments to actual Tally postings.
- [ ] **Validate matcher** against ground truth — for every voucher in Day Book with `INVOICE NO:<x>` in narration, our `recon.py` should produce the same link. Diff and report.

## Matcher upgrades that need real Tally narrations

- [ ] **Narration parser** — regex `INVOICE NO[:\-\s]*(\d{2}-\d{2}/\d+)` on Tally narrations to walk back from Journal → EZ invoice. Adds the gold join key the meeting context promised.
- [ ] **On-account resolver** — for each Tally pending bill (the "On Account" rows), find the best EZ invoice candidate via amount + date + guest fuzzy. Output `data/recon/matches/on_account_resolutions.csv`.

## Open questions to settle (one Urvashi call clears most)

- [ ] GST 12% (EZ data) vs 5% (Tally ledger label) — which is canonical?
- [ ] Voucher type for payments — Journal (current) vs Receipt?
- [ ] Sundry Debtors split — per OTA, or stay lumped?
- [ ] Commission + GST handling — separate expense ledger? Input GST credit claimed?
- [ ] Rate-change credit notes — Credit Note voucher or sales reversal?
- [ ] F&B / Rooftop / Hotel — separate companies or separate ledger groups in one company?
- [ ] TCS/TDS GoMT — where in chart of accounts?

## Data gaps to close (parallel asks)

- [ ] **Fresh EZ export** for Dec 25–Feb 26 (or full FY 25–26) — unlocks PTM↔Invoice matching. Currently only Apr 2025 in `data/invoices/raw/`.
- [ ] **PTM Rooftop + F&B raw** 123-col exports for Dec 25–Feb 26 — currently only processed slim subsets in `data/payments/processed/`.
- [ ] **GoMT exports Nov 25+** — single pooled CSV for Apr–Oct only.
- [ ] **Hotel main bank Dec 25+** statements.
- [ ] **AGODA.rar** — `brew install --cask the-unarchiver`, extract, re-bucket.
- [ ] **TMV PMS payment-receipt PDFs** (the real ones) — would carry invoice→payment bridge.

## Pipeline polish (nice-to-have)

- [ ] Refactor UI sidebar to show the new ETL bucket layout (`data/booking/raw`, etc.) instead of the legacy content-pattern groups.
- [ ] UI "Pull from Tally" button — runs `day_book`/`pending_bills` and renders results in-page.
- [ ] UI drill-down: click a pending row → show matching candidate invoices.
- [ ] GoMT extractor (`etl/extract/gomt.py`) — TCS/TDS-aware.
- [ ] Two-way diff: our canonical `payment.csv` vs Urvashi's `data/payments/processed/` — find where her manual additions add value.
- [ ] Idempotency layer for live Tally pushes (track which (date, ref, amount) we've already POSTed to avoid duplicates on re-run).
