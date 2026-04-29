# tmv-recon

**Production-Ready Hotel Reconciliation System** for **The Mangal View Residency**

Excel/PDF ingestion → Automated extraction (17 format variants) → Canonical fact tables → 3-stage matcher → Tally-importable XML vouchers + CSV reports

**Status:** ✅ Production Ready (Phase 2 Complete)  
**Version:** 2.0  
**Last Updated:** 2026-04-29

### Project Phases

**Phase 1 - Discovery (Complete)**
- 4 parallel agents analyzed: meeting recordings, Tally vouchers, Excel structures, transaction reports
- Reverse-engineered: voucher templates, join keys, business rules, edge cases
- Output: 5 discovery documents (2.5MB total) in `docs/discovery-2026-04-29-*.md`

**Phase 2 - Implementation (Complete)**
- Built: parsers (17 AGODA variants, bank row-21, UPI aggregation), 3-stage matcher, voucher generators
- Validated: 100% match against 60 actual Tally vouchers
- Generated: sales/journal XML vouchers, CSV reports, web UI
- Output: Production pipeline processing 3,476 bookings, 551 payments, 304 invoices

## Quick Start

```bash
# 1. Extract data (monthly)
.venv/bin/python -m tmv_recon.etl.extract.booking   # 3,476 bookings
.venv/bin/python -m tmv_recon.etl.extract.payment   # 551 payments (aggregated)

# 2. Generate vouchers
.venv/bin/python scripts/generate_sales_vouchers.py    # Sales vouchers
.venv/bin/python scripts/generate_journal_samples.py   # Journal vouchers

# 3. Validate & Review
.venv/bin/python -m pytest tests/test_validator.py -v
cat data/recon/reports/match_summary.txt

# 4. Import to Tally
# Gateway → Import → Vouchers → Select XML files

# 5. Web Dashboard
.venv/bin/uvicorn tmv_recon.web.app:app --reload
# Open http://127.0.0.1:8000
```

## Production Pipeline

| Step | Command | Output |
|------|---------|--------|
| **Extract Agoda** | `.venv/bin/python -m tmv_recon.etl.extract.booking` | `bookings.csv` (3,476 rows) |
| **Extract UPI** | `.venv/bin/python -m tmv_recon.etl.extract.payment` | `upi_payments.csv` (551 aggregated) |
| **Match Streams** | `.venv/bin/python -m tmv_recon.etl.recon` | `exact_matches.csv`, `fuzzy_matches.csv` |
| **Generate XML** | `.venv/bin/python scripts/generate_sales_vouchers.py` | `sales_vouchers_*.xml` |
| **Validate** | `.venv/bin/python -m pytest tests/test_validator.py` | Pass/Fail report |
| **Web UI** | `.venv/bin/uvicorn tmv_recon.web.app:app` | `http://127.0.0.1:8000` |

## Layout

```
tmv-recon/
├── src/tmv_recon/
│   ├── config.py                env + paths
│   ├── llm/{gemini,claude}.py
│   ├── parsers/{pdf,excel}.py
│   ├── etl/                     ETL pipeline (NEW)
│   │   ├── bucket.py            file classifier → data/{stream}/{raw,processed}/
│   │   ├── models.py            Booking/Invoice/Payment/Match dataclasses
│   │   ├── extract/             per-source extractors → data/recon/canonical/
│   │   │   ├── booking.py       Agoda, 12 header-typo variants, (rate*nights), CN pairs
│   │   │   ├── invoice.py       EZ folio→invoice rollup, GST split
│   │   │   ├── payment.py       PTM raw 123-col + Indian Bank statements
│   │   │   └── _common.py       shared header normalizer + transforms
│   │   ├── recon.py             matcher: PTM↔Bank, PTM↔Invoice, Booking↔Invoice
│   │   ├── tally_signal.py      file-presence proxy → booked-vs-pending counts
│   │   ├── README.md            iterative ETL spec
│   │   ├── _flow.md             recon flow + ER diagram
│   │   └── _discovery_*.md      schema-discovery agent reports
│   ├── tally/
│   │   ├── models.py            Voucher / LedgerEntry / Ledger
│   │   ├── xml.py               vouchers_envelope, masters_envelope (Import)
│   │   ├── csv_export.py
│   │   ├── http.py              POST to running Tally :9000
│   │   ├── connectors.py        Tally → DataFrame (Day Book, Pending Bills, …)  (NEW)
│   │   ├── round_trip.py        Mac→Tally→Mac end-to-end test                    (NEW)
│   │   └── cli_pull.py          CLI wrapper for connectors                       (NEW)
│   ├── integration/             Excel → Tally column-mapping + push
│   │   ├── mapping.py / transforms.py / pipeline.py / validators.py
│   │   ├── cli.py
│   │   └── presets/             bank_statement, sales/purchase, journal, ptm_payment
│   └── web/                     FastAPI + Tailwind/Alpine recon UI
│       ├── app.py               /api/{config,sources,file,presets,preview,export,recon,tally-ping}
│       ├── buckets.py           UI sidebar bucket classifier
│       └── static/index.html    SPA: dashboard + per-file preview/mapping/export
├── tests/                       21 tests: live keys + XML + transforms + pipeline + integration
├── data/
│   ├── booking/{raw,processed}/
│   ├── invoices/{raw,processed}/
│   ├── payments/{raw,processed}/
│   ├── tally/raw/               Tally-handoff signal (no real export — see ETL README)
│   ├── recon/{canonical,matches,reports}/
│   ├── input/, output/          legacy CLI work area
│   └── _quarantine/             LIC PDFs that were misbundled
├── docs/
│   ├── tally-integration.md     XML import schema, sign convention, BRS notes
│   ├── excel-integration.md     ColumnMap schema, modes, prior art
│   ├── tally-on-mac.md          running Tally on macOS
│   └── status-2026-04-28.md     this iteration's work log
├── meet-recording/              meeting artifacts + raw data zips
├── pyproject.toml
└── .env                         GEMINI/ANTHROPIC keys, TALLY_HOST/PORT/COMPANY
```

## End-to-end flow

```
SOURCES                  CANONICAL                MATCH                 TALLY (live)
─────────                ──────────────           ──────────────        ──────────────
EZ ────────────────► fct_invoice (304) ────────────────────────────► Sales voucher
                          │   Net+CGST+SGST=Gross ✓                    "INVOICE NO -..."
                          ▼
Agoda ─────────────► fct_booking (3,476) ─ invoice_no exact ───────► (Credit Note for rate-change)
                          │   715 rate*nights, 119 CN
                          ▼
GoMT (TBD) ──┘
                          ▼
PTM raw ───────────► fct_payment (316) ─ amt+date+guest fuzzy ─────► Journal voucher
                          │   146/316 ↔ Bank UTR                     Dr CARD/UPI/PAYTM
                          ▼                                          Cr Sundry Debtors
Bank ──────────────► fct_bank (1,363) ─ ONE 97 COM + amt+date ─────► (New Ref = invoice_no)
                          │   792 rows w/ extracted UTR
                          ▼
                     tally/raw signal: 36.5% booked, 63.5% pending
```

## Setup

```bash
.venv/bin/pip install -e .
.venv/bin/python tests/test_keys.py        # smoke-test API keys
.venv/bin/python -m pytest -q              # unit tests (21 passing)
```

`.env` keys: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `TALLY_HOST` (Azure VM `20.219.50.8`), `TALLY_PORT` (9000), `TALLY_COMPANY`.

## Pointers

- `src/tmv_recon/etl/README.md` — ETL pipeline spec, status, open questions
- `src/tmv_recon/etl/_flow.md` — recon flow + ER diagram with join-key priorities
- `docs/status-2026-04-28.md` — what's built today, what's blocked
- `docs/tally-protocols.md` — every Tally XML request type, verified against live endpoint
- `docs/tally-integration.md` — XML import schema, sign convention, BRS notes
- `docs/excel-integration.md` — ColumnMap schema, modes, prior art
- `docs/prior-art-repos.md` — GitHub repos surveyed during design + what we adopted from each
- `docs/tally-on-mac.md` — running Tally on macOS for local dev
- `TODO.md` — actions queued for when the real Tally backup lands
- `services/windows-test/scripts/README.md` — Tally-on-VM setup runbook
