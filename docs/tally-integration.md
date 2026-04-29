# Tally Integration — Reference Notes

Target: TallyPrime (also compatible with Tally.ERP 9 for the XML envelope shape).
Scope of this project: programmatic **import** of vouchers + masters generated
from PDF/Excel reconciliation, and optional **export** queries against a running
Tally instance.

---

## 1. Integration channels

| Channel | Use | Notes |
|---|---|---|
| **HTTP + XML** (port 9000) | Live push/pull to a running Tally desktop | Tally itself runs an HTTP server. POST XML, get XML back. |
| **File-based XML import** | Offline batch import via Tally UI (`Gateway > Import`) | No running listener needed. We default to this. |
| **ODBC** | Read-only DB queries | Out of scope here. |

Enable HTTP server: TallyPrime → **F1 Help → Settings → Connectivity → Client/Server config** → role *Both* or *Server*, port `9000`. Endpoint becomes `http://<host>:9000` (POST, `Content-Type: text/xml; charset=utf-8`). [^integration] [^xml-int]

---

## 2. Universal envelope

Every request — import, export, execute — wraps in:

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Import | Export | Execute</TALLYREQUEST>
    <TYPE>Data | Object | Collection | Function</TYPE>
    <ID>Vouchers | All Masters | Trial Balance | …</ID>
  </HEADER>
  <BODY>
    <DESC> … STATICVARIABLES, FETCHLIST, TDL … </DESC>
    <DATA>
      <TALLYMESSAGE> … payload … </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
```

Response carries `<HEADER><STATUS>1</STATUS></HEADER>` (1 = ok, 0 = warn, −1 = error)
plus, for imports, an `IMPORTRESULT` with `CREATED / ALTERED / COMBINED / IGNORED / ERRORS / LASTVCHID / LASTMID`. [^case1]

### Date format
**`YYYYMMDD`** everywhere (no separators). Example: `20260428`.

---

## 3. Voucher import (the recon target)

Header values: `TALLYREQUEST=Import`, `TYPE=Data`, `ID=Vouchers`. [^sample]

```xml
<TALLYMESSAGE xmlns:UDF="TallyUDF">
  <VOUCHER VCHTYPE="Payment" ACTION="Create">
    <DATE>20260428</DATE>
    <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
    <VOUCHERNUMBER>1</VOUCHERNUMBER>
    <NARRATION>Office rent April</NARRATION>
    <REFERENCE>UTR-XYZ123</REFERENCE>
    <PARTYLEDGERNAME>HDFC Bank</PARTYLEDGERNAME>
    <ALLLEDGERENTRIES.LIST>
      <LEDGERNAME>Office Rent</LEDGERNAME>
      <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
      <AMOUNT>-12000.00</AMOUNT>
    </ALLLEDGERENTRIES.LIST>
    <ALLLEDGERENTRIES.LIST>
      <LEDGERNAME>HDFC Bank</LEDGERNAME>
      <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
      <AMOUNT>12000.00</AMOUNT>
    </ALLLEDGERENTRIES.LIST>
  </VOUCHER>
</TALLYMESSAGE>
```

### Sign convention (the gotcha)

Tally signs voucher amounts oppositely from common accounting prose:

- `ISDEEMEDPOSITIVE=Yes` ↔ Debit. The numeric `<AMOUNT>` is **negative**.
- `ISDEEMEDPOSITIVE=No`  ↔ Credit. The numeric `<AMOUNT>` is **positive**.

Across a voucher, the signed `<AMOUNT>` values must sum to zero. [^case1] [^sample]

### Voucher types we care about for recon

| Type | Typical use | Party ledger? |
|---|---|---|
| `Receipt`  | money in (bank Dr, party Cr) | yes |
| `Payment`  | money out (party/expense Dr, bank Cr) | yes |
| `Contra`   | bank↔bank / bank↔cash | no |
| `Journal`  | adjustments | no |
| `Sales` / `Purchase` | invoices (use `ALLINVENTORYENTRIES.LIST` if inventory mode) | yes |

Inventory invoice mode example uses `<ISINVOICE>Yes</ISINVOICE>` and `<PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>` plus `<ALLINVENTORYENTRIES.LIST>` blocks with `STOCKITEMNAME`, `RATE`, `ACTUALQTY`, `BILLEDQTY`. [^sample]

### Idempotency / dedup

There is no native upsert for vouchers — repeated imports create duplicates.
Strategies:

1. Use a stable `<VOUCHERNUMBER>` per source row + a unique numbering series in Tally.
2. Stamp the source ID into `<REFERENCE>` and pre-query Tally for it before import.
3. Keep a local ledger of imported `(date, ref, amount)` to avoid re-sends.

---

## 4. Master import (ledgers, groups)

Header: `ID=All Masters`. Use `IMPORTDUPS` to control duplicates: [^case1]

| Flag | Behaviour |
|---|---|
| `@@DUPCOMBINE` | Combine opening balances |
| `@@DUPIGNORE`  | Skip if ledger exists |
| `@@DUPMODIFY`  | Overwrite |

```xml
<TALLYMESSAGE xmlns:UDF="TallyUDF">
  <LEDGER NAME="HDFC Bank" Action="Create">
    <NAME>HDFC Bank</NAME>
    <PARENT>Bank Accounts</PARENT>
    <OPENINGBALANCE>-12500.00</OPENINGBALANCE>
  </LEDGER>
</TALLYMESSAGE>
```

Common parent groups: `Bank Accounts`, `Sundry Debtors`, `Sundry Creditors`,
`Indirect Expenses`, `Indirect Incomes`, `Current Assets`, `Current Liabilities`,
`Duties & Taxes`. (These ship as built-in groups in Tally.)

Masters MUST exist before vouchers reference them — import order:
**groups → ledgers → vouchers**.

---

## 5. Bank reconciliation specifics

Tally accepts bank statements in **Excel, MT940, and CSV** via the
*Banking → Bank Statement* utility. There is no native BRS-only XML schema —
the recon path is:

1. Import bank statement (Excel/CSV) into Tally's Banking module, OR
2. Generate Receipt/Payment vouchers from the statement and import them via XML
   (our path), then run **Auto Bank Reconciliation** in Tally to match against
   book entries.[^brs1] [^brs2]

For Auto BRS to match, populate `<INSTRUMENTDATE>` (cheque/UTR date) and
`<BANKERSDATE>` on the bank-side ledger entry where applicable.

---

## 6. Export queries (read-back, optional)

Useful for verifying a recon push:

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE><ID>Remote Ledger Coll</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>ACME PVT LTD</SVCURRENTCOMPANY>
      </STATICVARIABLES>
      <TDL><TDLMESSAGE>
        <COLLECTION NAME="Remote Ledger Coll" ISINITIALIZE="Yes">
          <TYPE>Ledger</TYPE>
          <NATIVEMETHOD>Name</NATIVEMETHOD>
          <NATIVEMETHOD>OpeningBalance</NATIVEMETHOD>
        </COLLECTION>
      </TDLMESSAGE></TDL>
    </DESC>
  </BODY>
</ENVELOPE>
```

Object export (single ledger) uses `TYPE=OBJECT`, `SUBTYPE=Ledger`,
`<ID TYPE="Name">…</ID>` plus a `FETCHLIST`. [^case1]

---

## 7. Validation checklist before import

- [ ] Date in `YYYYMMDD`.
- [ ] Every voucher's signed `<AMOUNT>` sums to 0.
- [ ] All `<LEDGERNAME>` strings exist as masters in target company.
- [ ] `<VOUCHERTYPENAME>` matches a Tally voucher type (case sensitive).
- [ ] `<VOUCHERNUMBER>` unique within the numbering method, or duplicates handled.
- [ ] `<PARTYLEDGERNAME>` set for Receipt/Payment/Sales/Purchase.
- [ ] UTF-8 encoding; entities `& < >` escaped.

---

## References

[^sample]: TallyHelp — *Sample XML*. https://help.tallysolutions.com/sample-xml/
[^xml-int]: TallyHelp — *XML Integration*. https://help.tallysolutions.com/xml-integration/
[^case1]: TallyHelp — *Case Study 1: XML Request and Response Formats*. https://help.tallysolutions.com/case-study-1/
[^integration]: TallyHelp — *Integration With TallyPrime*. https://help.tallysolutions.com/integration-with-tallyprime/
[^brs1]: TallyHelp — *Bank Reconciliation in TallyPrime*. https://help.tallysolutions.com/tally-prime/banking-utilities/bank-reconciliation-tally/
[^brs2]: TallyHelp — *View / Import / Re-import Bank Statement for BRS (Tally.ERP 9)*. https://help.tallysolutions.com/article/Tally.ERP9/Banking/import_bank_stmt_in_bank_recon.htm
