# Excel → Tally integration

Pipeline: **Excel → ColumnMap → Voucher objects → Tally XML / CSV / live POST**.

## Mandatory Tally fields (per official import semantics)

`Voucher Type Name`, `Voucher Date`, `Voucher Number`, `Ledger Name`,
`Ledger Amount`. Ledger names in Excel must match Tally **exactly** — Tally
matches by name string. [^maas] [^tally-import]

Date stored as `YYYYMMDD` text; amounts numeric only (no `₹`/`Rs`/commas) —
the pipeline normalises both.[^markit]

## Two mapping modes

### `row_per_voucher` — bank statements

Each row = one Receipt (deposit) or Payment (withdrawal). Two amount-column
strategies:

- **Dr/Cr columns** (typical bank export): `debit_amount` + `credit_amount`,
  whichever is non-empty wins. *Withdrawal* → Payment, *Deposit* → Receipt.
- **Single signed column**: `signed_amount` — negative ⇒ Payment.

Other side ledger comes from `contra_ledger` column or `default_contra_ledger`
fallback (e.g. `"Suspense"` for unmapped rows you'll classify later).

### `compound` — journals, sales/purchase registers

Rows are grouped by `group_by` (e.g. `Voucher No`, `Invoice No`). All rows in
a group become entries of one voucher; each row defines `ledger`, `amount`,
and a Dr/Cr indicator.

## Mapping schema

```yaml
mode: row_per_voucher | compound

# Field reference: dict spec OR bare column name OR fixed value via {value: ...}
voucher_type:    { value: "Sales" }                       # fixed
date:            { column: "Invoice Date", transform: date, required: true }
voucher_number:  { column: "Invoice No" }
narration:       { column: "Narration" }
reference:       { column: "Invoice No" }
party:           { column: "Party Name" }

# compound only:
group_by: { column: "Invoice No" }
entries:
  - ledger: { column: "Ledger" }
    amount: { column: "Amount", transform: amount }
    is_deemed_positive: { column: "DrCr" }   # cell value Dr/Cr/True/False
    is_party_ledger: false

# row_per_voucher only:
bank_ledger: "HDFC Bank"
debit_amount:  { column: "Withdrawal", transform: amount }
credit_amount: { column: "Deposit",    transform: amount }
contra_ledger: { column: "Counterparty" }
default_contra_ledger: "Suspense"
payment_voucher_type: "Payment"
receipt_voucher_type: "Receipt"
```

### Field transforms

- `string` (default) — `.strip()`, NaN → empty
- `date` — accepts `YYYY-MM-DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `YYYYMMDD`,
  `DD-Mon-YYYY`, Python `datetime`/`date`, pandas `Timestamp`, **Excel serial**
- `amount` — strips `₹`, `Rs`, `INR`, commas, spaces; `(123.45)` → `-123.45`

### Sign convention (Tally)

The pipeline always emits Tally-compliant signs in `<AMOUNT>`:

- `ISDEEMEDPOSITIVE=Yes` (Dr) ⇒ `<AMOUNT>` negative
- `ISDEEMEDPOSITIVE=No`  (Cr) ⇒ `<AMOUNT>` positive
- Sum across a voucher = 0 (validator enforces this)

Excel can have positive magnitudes — the pipeline applies signs from the
Dr/Cr indicator. [^case1]

## CLI

```bash
# Bank statement → XML + CSV
python -m tmv_recon.integration.cli \
    --excel data/input/bank.xlsx \
    --preset bank_statement \
    --xml   data/output/bank.xml \
    --csv   data/output/bank.csv

# Custom mapping
python -m tmv_recon.integration.cli --excel x.xlsx --mapping my-map.yaml --xml out.xml

# Push live to TallyPrime on :9000 (must be running with HTTP server enabled)
python -m tmv_recon.integration.cli --excel x.xlsx --preset journal --post --company "ACME PVT LTD"
```

Built-in presets: `bank_statement`, `sales_register`, `purchase_register`, `journal`.

## Programmatic use

```python
from tmv_recon.parsers import excel as xls
from tmv_recon.integration import load_preset, build, validate, has_errors
from tmv_recon.tally.xml import vouchers_envelope
from tmv_recon.tally.http import post_xml

df = xls.sheet("data/input/bank.xlsx")
cmap = load_preset("bank_statement")
vs = build(df, cmap)

issues = validate(vs)
assert not has_errors(issues), issues

xml = vouchers_envelope(vs, company="ACME PVT LTD")
print(post_xml(xml))   # → <ENVELOPE><...IMPORTRESULT.../></ENVELOPE>
```

Pass `known_ledgers={...}` to `validate()` to flag ledgers missing from your
Tally master list before import.

## Idempotency

Tally has no native upsert — re-importing creates duplicates. The pipeline
preserves `voucher_number` and `reference` from your source rows, so:

1. Use a unique `<VOUCHERNUMBER>` per source row.
2. Keep a local audit of imported `(date, ref, amount)` and skip on retry.
3. Or query Tally for existing `<REFERENCE>` before each push.

## Prior art consulted

- [ShwetaSoftwares/excel-to-tally-templates](https://github.com/ShwetaSoftwares/excel-to-tally-templates) — XML tag templates per voucher type (V11/V12, bank statement, sales/purchase ±inventory, payroll, masters)
- [sridharxp/excel2tally](https://github.com/sridharxp/excel2tally) — VchUpdate.dll-based row→voucher converter; multi-line vouchers via row ID column
- [adarshmadrecha/excel-to-tally](https://github.com/adarshmadrecha/excel-to-tally) — Excel-macro template family (Alwal)
- [aadil-sengupta/Tally.Py](https://github.com/aadil-sengupta/Tally.Py) — Python TallyClient pattern (`get_*`, `create_voucher`, `create_ledger`)
- [tally-integration on PyPI](https://pypi.org/project/tally-integration/)
- [TallyConnector (C#)](https://github.com/Accounting-Companion/TallyConnector) — production XML-API client with rich type system
- [udiMagic templates](https://www.rtslink.com/products/udimagic/templates/) — commercial reference for column conventions
- [NIKASH](https://nikash.in/) — free converter, no schema docs but useful UI reference
- [Tally Master — sales/purchase voucher import guides](https://tallymaster.in/excel-to-tally/import-vouchers/)

## References

[^maas]: MAAS — *Import Data from Excel to Tally using Mapping*. https://maas.freshdesk.com/support/solutions/articles/501000041108-import-data-from-excel-to-tally-using-mapping
[^tally-import]: TallyHelp — *How to Import Data into TallyPrime*. https://help.tallysolutions.com/import-data-in-tally/
[^markit]: Mark IT — *Import Excel Data to TallyPrime: Complete Guide*. https://www.markitsolutions.in/blog-details/excel-to-tally-import-guide
[^case1]: TallyHelp — *Case Study 1: XML Request and Response Formats*. https://help.tallysolutions.com/case-study-1/
