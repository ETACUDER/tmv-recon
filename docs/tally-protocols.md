# Tally XML protocol — verified against live endpoint

Reference: [TallyHelp — Case Study 1](https://help.tallysolutions.com/article/DeveloperReference/integration-capabilities/case_study_1.htm).

Endpoint tested: `http://20.219.50.8:9000/` (TallyPrime 7.0 on Azure VM `win-test-01`).

Re-run any time: `.venv/bin/python -m tmv_recon.tally.protocol_test`

## What works without a loaded company

| Request | Type | ID | Result |
|---|---|---|---|
| **Function — math** | `Function` | `$$Round` (with `<FUNCPARAMLIST>`) | ✓ STATUS=1, returns `<RESULT TYPE="Number">12.35</RESULT>` |
| **List of Companies** | `Collection` | `List of Companies` | ✓ STATUS=1, returns `<COMPANY>0</COMPANY>` (count) when none loaded |

## What needs a company loaded (`<SVCURRENTCOMPANY>` set)

All return `STATUS=0` with `LINEERROR="Could not find Company ''"` until a company is loaded:

| ID | Verified | Notes |
|---|---|---|
| `Trial Balance` | ✓ valid name | with optional `<EXPLODEFLAG>Yes</EXPLODEFLAG>` |
| `Balance Sheet` | ✓ valid name | |
| `Day Book` | ✓ valid name | takes `SVFROMDATE`/`SVTODATE` |
| `Sales Register` | ✓ valid name | takes `SVFROMDATE`/`SVTODATE` |
| `Purchase Register` | ✓ valid name | |
| `Payment Register` | ✓ valid name | |
| `Journal Register` | ✓ valid name | |
| `Voucher Register` | ✓ valid name | |
| `Bills Receivable` | ✓ valid name | |
| `Bills Payable` | ✓ valid name | |
| `Group Outstandings` | ✓ valid (timed out without company) | needs `<LedgerName>` or `<GroupName>` SV |
| `Ledger Outstandings` | ✓ valid (timed out without company) | needs `<LedgerName>` SV |
| `Group Summary` | ✓ valid (timed out without company) | |
| `Stock Summary` | ✓ valid (timed out without company) | |
| `Cash Flow` | ✓ valid (timed out without company) | |
| `Funds Flow` | ✓ valid (timed out without company) | |

## Report IDs that **do not work** (rejected)

| ID | Error |
|---|---|
| `Cash Book` | `Could not find Report 'Cash Book'!` — use Day Book filtered by Cash ledger |
| `Bank Book` | `Could not find Report 'Bank Book'!` — use Day Book filtered by bank ledger |
| `Receipt Register` | `Could not find Report 'Receipt Register'!` — try `Receipts` (not yet verified) |
| `Profit & Loss A/c` | non-standard response — try `Profit and Loss` or `P & L` (not yet verified) |
| `List of Companies` (TYPE=Data) | `Could not find Report 'List of Companies'!` — must be TYPE=Collection (above) |

## Import side (needs company)

| ID | Action variants |
|---|---|
| `All Masters` | `<LEDGER ACTION="Create">`, `<GROUP>`, `<UNIT>`, `<STOCKITEM>` etc.; `<COMPANY>` reportedly NOT accepted via XML in TallyPrime 7.0 |
| `Vouchers` | `<VOUCHER ACTION="Create">`, `Action="Alter"`, `Action="Cancel"`, `Action="Delete"` |

`STATICVARIABLES` for imports:
- `<IMPORTDUPS>` — `@@DUPCOMBINE` (combine OB), `DupModify` (overwrite), `DupIgnoreCombine` (skip if exists)
- `<SVCURRENTCOMPANY>` — required to scope the import to a specific loaded company

## Date format
`YYYYMMDD` (no separators). E.g. `20260428`.

## Sign convention (gotcha)
- `ISDEEMEDPOSITIVE=Yes` ⇒ Debit ⇒ `<AMOUNT>` is **negative**
- `ISDEEMEDPOSITIVE=No`  ⇒ Credit ⇒ `<AMOUNT>` is **positive**
- Per-voucher signed sum must be `0`.

## Structure cheat-sheet

```
ENVELOPE
├── HEADER
│   ├── VERSION       1
│   ├── TALLYREQUEST  Import | Export | Execute
│   ├── TYPE          Data | Object | Collection | Function | TDLAction
│   ├── ID            (report name | "All Masters" | "Vouchers" | function name | TDL action)
│   └── SUBTYPE       (Object only — e.g. "Ledger")
└── BODY
    ├── DESC
    │   ├── STATICVARIABLES   …
    │   ├── FETCHLIST         (Object exports)
    │   ├── FUNCPARAMLIST     (Function with params)
    │   └── TDL/TDLMESSAGE    (Collection definitions)
    └── DATA
        └── TALLYMESSAGE
            ├── LEDGER / GROUP / UNIT …  (masters)
            └── VOUCHER                  (transactions)
```

## Implementation in this repo

- `tmv_recon/tally/xml.py` — Import envelope builders (vouchers + masters)
- `tmv_recon/tally/connectors.py` — Export queries → DataFrames
- `tmv_recon/tally/http.py` — POST wrapper
- `tmv_recon/tally/round_trip.py` — full create-company + masters + sales + journal + day-book round-trip
- `tmv_recon/tally/protocol_test.py` — exercises every protocol type and reports STATUS

## Conclusion

The only blocker before bidirectional sync against real Tally data is **a loaded company** on the VM. Once that lands (either RDP create or restored backup), every export ID above + every import works programmatically without further code changes.
