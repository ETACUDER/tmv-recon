# Prior art — GitHub repos consulted

Surveyed during the column-mapping design phase to anchor this project on conventions the Tally community already uses.

## What we adopted

### [ShwetaSoftwares/excel-to-tally-templates](https://github.com/ShwetaSoftwares/excel-to-tally-templates) — XML tag templates per voucher type

The most useful repo. Provides UDIMagic-style XML configuration files mapping Excel columns to Tally XML tags for ~30 voucher/master types (V11 + V12). Particularly useful: `Vouchers-V11-Bank-statement-xml-tags.xml` shows how a single bank-statement row gets fanned out into a `<VOUCHER>` with two `<ALLLEDGERENTRIES.LIST>` children, with column letters (A, B, C…) mapped to specific XML elements.

**Adopted from this**:
- The dual-ledger-entry pattern for bank statements (suspense + bank ledger) — informed our `row_per_voucher` mode.
- Header-tag canonical names (`LEDGERNAME`, `ISDEEMEDPOSITIVE`, `AMOUNT`, `BANKALLOCATIONS.LIST`) — used verbatim in `tally/xml.py`.

### [sridharxp/excel2tally](https://github.com/sridharxp/excel2tally) — VchUpdate.dll-based row → voucher converter

VBA macro family that loops Excel rows and emits XML imports through the official `VchUpdate.dll` shipped with Tally. Key insight from its README: **multi-line vouchers (Daybook style) require an ID column to identify row boundaries**. Sales and Purchase need date values. Tool can't update existing vouchers — Create-only.

**Adopted from this**:
- Our `compound` mode in `integration/pipeline.py` uses a `group_by` column for exactly this reason — multi-line vouchers grouped by `Voucher No`.
- The Create-only constraint informs our idempotency notes (use stable `voucher_number`, dedup before re-run).

### [adarshmadrecha/excel-to-tally](https://github.com/adarshmadrecha/excel-to-tally) — Excel macro family by Vijaykumar Alwal

Excel-side macros that ship with column conventions for various voucher types. Less code, more conventions. Useful as a reference for what column names accountants are used to.

**Adopted from this**:
- Default column names in our presets (e.g. `Invoice No`, `Voucher No`, `Date`, `Particulars`, `Narration`, `Dr/Cr`).

### [aadil-sengupta/Tally.Py](https://github.com/aadil-sengupta/Tally.Py) — Python TallyClient pattern

Python-first SDK with a clean class API: `TallyClient.get_companies()`, `get_ledgers()`, `create_voucher()`, `create_ledger()`, `test_connection()`. Defaults to `http://localhost:9000`.

**Adopted from this**:
- The function naming pattern (one Python function per logical Tally operation) — used in our `tally/connectors.py` (`list_companies()`, `day_book()`, `ledger_outstandings()`, etc.).
- The `test_connection()` health-check idea — implemented as `/api/tally-ping` in the web UI.

### [Accounting-Companion/TallyConnector](https://github.com/Accounting-Companion/TallyConnector) — production-grade C# XML-API client

The most thorough public Tally integration. Has rich type definitions, `TallyEnvelope<T>` generics, retry logic, and supports the entire request matrix (Data/Object/Collection/Function for both Import and Export). C#-native, but the model classes are illustrative.

**Adopted from this**:
- Our envelope-builder pattern in `tally/xml.py` and `tally/connectors.py` mirrors its `RequestEnvelope`/`ResponseEnvelope` split.
- Error handling — checking `<STATUS>` and `<LINEERROR>` was lifted from how this lib handles responses.

### [tally-integration on PyPI](https://pypi.org/project/tally-integration/) — tiny PyPI client

Pip-installable thin wrapper. Confirmed the `localhost:9000` default and basic envelope structure. Doesn't go deep — useful only as proof that this is a known pattern.

## What we did NOT use

- **udiMagic** ([commercial](https://www.rtslink.com/products/udimagic/templates/)) — has the most polished column-mapping templates, but commercial. We learned from the templates' shape, didn't copy.
- **NIKASH / SMAART** (web UIs at nikash.in / xltally.in) — no schema docs, useful only as feature reference.
- **`dhananjay1405/excelkida-power-query-library/tally/ledger-vouchers.pq`** — Power Query for pulling from Tally; relevant if we ever wanted Excel-side connection, but we're Python-first.

## Where to look in this repo for what came from where

| File | Origin influence |
|---|---|
| `src/tmv_recon/tally/xml.py` | ShwetaSoftwares + TallyConnector |
| `src/tmv_recon/integration/pipeline.py` | sridharxp/excel2tally (compound mode) |
| `src/tmv_recon/integration/presets/*.yaml` | adarshmadrecha defaults + ShwetaSoftwares' XML tags |
| `src/tmv_recon/tally/connectors.py` | aadil-sengupta/Tally.Py (function naming) + TallyConnector (envelope split) |
| `src/tmv_recon/tally/round_trip.py` | tally-integration's connection-test + custom |

All references are linked in `docs/excel-integration.md` § "Prior art consulted".
