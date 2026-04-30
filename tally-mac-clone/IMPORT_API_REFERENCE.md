# Import/ETL API Reference

Quick reference for all import/ETL endpoints.

## Endpoints

### 1. Download Import Templates

#### Get Ledger Template
```http
GET /api/import/template/ledgers
```
**Response:** Excel file with columns: Name, Group Name, Opening Balance, Notes

#### Get Group Template
```http
GET /api/import/template/groups
```
**Response:** Excel file with columns: Name, Parent Group, Type, Notes

#### Get Voucher Template
```http
GET /api/import/template/vouchers?voucher_type=Payment
```
**Query Params:**
- `voucher_type` (optional): Payment, Receipt, Journal, Sales, Purchase, Contra

**Response:** Excel file with columns: Date, Voucher Number, Ledger Name, Debit, Credit, Narration

#### Get Stock Item Template
```http
GET /api/import/template/stock-items
```
**Response:** Excel file with columns: Name, Unit, Opening Stock, Rate, Category, HSN Code, GST Rate

---

### 2. Import from Excel

#### Import Ledgers
```http
POST /api/import/excel/ledgers
Content-Type: multipart/form-data

file: <excel-file>
```

**Request:**
```bash
curl -X POST \
  -F "file=@ledgers.xlsx" \
  http://localhost:8000/api/import/excel/ledgers
```

**Response:**
```json
{
  "status": "completed",
  "total_records": 50,
  "success_count": 48,
  "error_count": 2,
  "errors": [
    {
      "row": 15,
      "error": "Group not found: Sales Accounts"
    },
    {
      "row": 23,
      "error": "Opening balance must be a number"
    }
  ],
  "created_ids": [101, 102, 103, ...]
}
```

#### Import Vouchers
```http
POST /api/import/excel/vouchers?voucher_type=Payment&company_id=1
Content-Type: multipart/form-data

file: <excel-file>
```

**Query Params:**
- `voucher_type` (default: Payment): Payment, Receipt, Journal, Sales, Purchase, Contra
- `company_id` (default: 1): Company ID

**Request:**
```bash
curl -X POST \
  -F "file=@payments.xlsx" \
  "http://localhost:8000/api/import/excel/vouchers?voucher_type=Payment&company_id=1"
```

**Response:**
```json
{
  "status": "completed",
  "total_vouchers": 25,
  "success_count": 24,
  "error_count": 1,
  "errors": [
    {
      "voucher": "PMT/105",
      "error": "Voucher doesn't balance: Dr=5000, Cr=5500"
    }
  ],
  "created_ids": [301, 302, 303, ...]
}
```

---

### 3. Import Bank Statement

```http
POST /api/import/bank-statement?ledger_id=5&file_format=excel
Content-Type: multipart/form-data

file: <csv-or-excel-file>
```

**Query Params:**
- `ledger_id` (required): Bank ledger ID
- `file_format` (default: excel): excel or csv

**Request:**
```bash
curl -X POST \
  -F "file=@hdfc_statement.xlsx" \
  "http://localhost:8000/api/import/bank-statement?ledger_id=5&file_format=excel"
```

**Response:**
```json
{
  "status": "completed",
  "total_records": 100,
  "imported_count": 98,
  "matched_count": 75,
  "unmatched_count": 23,
  "error_count": 2,
  "errors": [
    {
      "row": 45,
      "error": "Invalid date format"
    }
  ],
  "suggestions": [
    {
      "statement_id": 123,
      "description": "NEFT-SALARY-APR2026",
      "amount": 50000,
      "suggested_ledger": "Salary Expense"
    },
    {
      "statement_id": 124,
      "description": "ELECTRICITY PAYMENT",
      "amount": 2500,
      "suggested_ledger": "Electricity Expense"
    }
  ]
}
```

**Auto-detected Bank Formats:**
- **HDFC:** Date, Narration, Withdrawal Amt., Deposit Amt., Closing Balance
- **ICICI:** Transaction Date, Description, Debit, Credit, Balance

**Generic Required Columns:**
- date
- description
- debit
- credit
- balance (optional)
- cheque_number (optional)
- reference (optional)

---

### 4. Import Tally XML

```http
POST /api/import/xml?company_id=1
Content-Type: multipart/form-data

file: <xml-file>
```

**Query Params:**
- `company_id` (default: 1): Company ID

**Request:**
```bash
curl -X POST \
  -F "file=@tally_vouchers.xml" \
  "http://localhost:8000/api/import/xml?company_id=1"
```

**Response:**
```json
{
  "status": "completed",
  "total_vouchers": 50,
  "success_count": 48,
  "error_count": 2,
  "errors": [
    {
      "voucher": "JV/2026/105",
      "error": "Ledger not found: ABC Corporation"
    }
  ],
  "created_ids": [401, 402, 403, ...]
}
```

**Supported XML Structure:**
```xml
<ENVELOPE>
  <BODY>
    <IMPORTDATA>
      <REQUESTDATA>
        <TALLYMESSAGE>
          <VOUCHER>
            <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
            <VOUCHERNUMBER>PMT/001</VOUCHERNUMBER>
            <DATE>20260415</DATE>
            <NARRATION>Payment to supplier</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>HDFC Bank</LEDGERNAME>
              <AMOUNT>-10000</AMOUNT>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>ABC Suppliers</LEDGERNAME>
              <AMOUNT>10000</AMOUNT>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Validation error (missing columns, invalid data) |
| 404 | Resource not found (ledger, group, etc.) |
| 500 | Server error (file read error, database error) |

---

## Common Error Messages

### Excel Import Errors
- `"Missing required columns: Name, Group Name"`
- `"Group not found: {group_name}"`
- `"Opening balance must be a number"`
- `"Ledger not found: {ledger_name}"`
- `"Voucher doesn't balance: Dr={debit}, Cr={credit}"`

### Bank Statement Errors
- `"ledger_id is required"`
- `"Failed to read file: {error}"`
- `"Missing columns after mapping: date, description"`
- `"Invalid date format"`

### XML Import Errors
- `"Invalid XML: {parse_error}"`
- `"Unknown voucher type: {voucher_type}"`
- `"Ledger not found: {ledger_name}"`

---

## Rate Limits

No rate limits currently implemented. All imports are synchronous.

For large files (>10MB or >1000 records), consider:
- Splitting into smaller batches
- Using background job processing (future enhancement)

---

## Best Practices

### Excel Import
1. Download template first to ensure correct format
2. Keep sample data row for reference
3. Don't modify column headers
4. Ensure all referenced masters (groups, ledgers) exist
5. For vouchers, group entries by voucher number
6. Always verify Dr = Cr for vouchers

### Bank Statement Import
1. Use consistent date format (YYYY-MM-DD preferred)
2. Include cheque numbers for better matching
3. Review suggestions for unmatched transactions
4. Create missing ledgers before import if needed
5. For HDFC/ICICI, use default column names for auto-detection

### XML Import
1. Validate XML structure before upload
2. Ensure all ledgers exist in target company
3. Use Tally's native export for best compatibility
4. Check voucher type names match exactly
5. Verify date format (YYYYMMDD or YYYY-MM-DD)

---

## Integration Examples

### Python
```python
import requests

# Download template
response = requests.get('http://localhost:8000/api/import/template/ledgers')
with open('ledgers_template.xlsx', 'wb') as f:
    f.write(response.content)

# Import ledgers
with open('ledgers_filled.xlsx', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/import/excel/ledgers',
        files=files
    )
    result = response.json()
    print(f"Imported {result['success_count']} ledgers")
```

### JavaScript/Fetch
```javascript
// Download template
fetch('/api/import/template/ledgers')
  .then(res => res.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ledgers_template.xlsx';
    a.click();
  });

// Import ledgers
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('/api/import/excel/ledgers', {
  method: 'POST',
  body: formData
})
  .then(res => res.json())
  .then(result => {
    console.log(`Imported ${result.success_count} ledgers`);
    if (result.errors.length > 0) {
      console.error('Errors:', result.errors);
    }
  });
```

### cURL
```bash
# Download template
curl -o template.xlsx \
  http://localhost:8000/api/import/template/vouchers?voucher_type=Payment

# Import vouchers
curl -X POST \
  -F "file=@vouchers.xlsx" \
  "http://localhost:8000/api/import/excel/vouchers?voucher_type=Payment&company_id=1" \
  | jq .

# Import bank statement
curl -X POST \
  -F "file=@statement.csv" \
  "http://localhost:8000/api/import/bank-statement?ledger_id=5&file_format=csv" \
  | jq .
```

---

## Troubleshooting

### "pandas required for Excel import"
```bash
pip install pandas openpyxl
```

### "Group not found" errors
Ensure groups exist before importing ledgers:
1. Check `/api/groups` for available groups
2. Create missing groups via UI or API
3. Match group names exactly (case-sensitive)

### Voucher doesn't balance
- Sum of debits must equal sum of credits
- Check for missing entries
- Verify amounts are positive numbers
- Tolerance: ±0.01

### Bank statement not matching
- Verify bank ledger ID is correct
- Check date formats are consistent
- Include cheque numbers when available
- Review suggestions for manual matching

### XML parse errors
- Validate XML syntax
- Check for required elements (VOUCHER, VOUCHERTYPENAME, etc.)
- Ensure proper nesting of ENVELOPE/BODY/TALLYMESSAGE
- Use UTF-8 encoding
