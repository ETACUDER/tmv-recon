# Import/ETL System for RecordX.Finance

Comprehensive data import system for Tally clone supporting Excel templates, bank statements, and Tally XML format.

## Quick Start

### Installation

```bash
# Install dependencies
pip install pandas openpyxl

# Or using the project
pip install -e .
```

### Start Server

```bash
# From project root
uvicorn tally_mac_clone.app:app --reload

# Or
./start.sh
```

### Access Import UI

1. Open http://localhost:8000
2. Press `Alt+X` to open Import/Export menu
3. Select import type:
   - Import Excel
   - Bank Statement Import
   - Import Tally XML

## Features

### ✅ Excel Import Templates
- **Ledgers**: Name, Group, Opening Balance
- **Groups**: Name, Parent, Type
- **Vouchers**: Date, Number, Ledger, Dr, Cr, Narration
- **Stock Items**: Name, Unit, Stock, Rate, Category, HSN, GST

### ✅ Excel Import with Validation
- Column validation
- Data type checking
- Foreign key validation
- Voucher balancing (Dr = Cr)
- Row-level error reporting
- Bulk insert

### ✅ Bank Statement Import
- CSV and Excel support
- Auto-detection (HDFC, ICICI formats)
- Auto-matching by cheque number
- Auto-matching by amount + date (±3 days)
- Ledger suggestions for unmatched items
- Match rate statistics

### ✅ Tally XML Import
- ENVELOPE/BODY/TALLYMESSAGE structure
- All 16 voucher types
- Tally date format (YYYYMMDD)
- Negative/positive amount convention
- Batch voucher creation

### ✅ Frontend UI
- File upload with drag-drop
- Progress indicators
- Results dashboard
- Error reporting
- Template downloads
- Keyboard shortcuts (Alt+X)

## Files Created

```
src/tally_mac_clone/
├── import_etl.py              # Main ETL module
└── app.py                     # API endpoints (updated)

static/
├── components/
│   └── import-components.html # UI components
├── js/
│   └── import.js              # Frontend logic
└── menu.js                    # Menu (updated)

examples/
└── test_import.py             # Test suite

Documentation:
├── IMPORT_ETL_SUMMARY.md      # Detailed implementation
├── IMPORT_API_REFERENCE.md    # API docs
└── IMPORT_SYSTEM_README.md    # This file
```

## API Endpoints

### Download Templates
```bash
GET /api/import/template/ledgers
GET /api/import/template/groups
GET /api/import/template/vouchers?voucher_type=Payment
GET /api/import/template/stock-items
```

### Import Operations
```bash
POST /api/import/excel/ledgers
POST /api/import/excel/vouchers?voucher_type=Payment&company_id=1
POST /api/import/bank-statement?ledger_id=5&file_format=excel
POST /api/import/xml?company_id=1
```

## Usage Examples

### 1. Download and Import Ledgers

```bash
# Download template
curl -o ledgers.xlsx http://localhost:8000/api/import/template/ledgers

# Fill template with data, then import
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
    {"row": 15, "error": "Group not found: Sales"}
  ],
  "created_ids": [101, 102, 103, ...]
}
```

### 2. Import Vouchers

```bash
# Download template
curl -o payments.xlsx \
  "http://localhost:8000/api/import/template/vouchers?voucher_type=Payment"

# Import
curl -X POST \
  -F "file=@payments.xlsx" \
  "http://localhost:8000/api/import/excel/vouchers?voucher_type=Payment&company_id=1"
```

**Excel Format:**
```
Date        | Voucher No | Ledger Name  | Debit  | Credit | Narration
------------|------------|--------------|--------|--------|------------------
2026-04-15  | PMT/001    | HDFC Bank    |        | 10000  | Payment to ABC
2026-04-15  | PMT/001    | ABC Supplier | 10000  |        | Payment to ABC
```

### 3. Import Bank Statement

```bash
# Import HDFC statement
curl -X POST \
  -F "file=@hdfc_statement.xlsx" \
  "http://localhost:8000/api/import/bank-statement?ledger_id=5&file_format=excel"
```

**Response:**
```json
{
  "imported_count": 98,
  "matched_count": 75,
  "unmatched_count": 23,
  "suggestions": [
    {
      "description": "NEFT-SALARY-APR2026",
      "amount": 50000,
      "suggested_ledger": "Salary Expense"
    }
  ]
}
```

### 4. Import Tally XML

```bash
curl -X POST \
  -F "file=@vouchers.xml" \
  "http://localhost:8000/api/import/xml?company_id=1"
```

**XML Format:**
```xml
<ENVELOPE>
  <BODY>
    <TALLYMESSAGE>
      <VOUCHER>
        <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
        <VOUCHERNUMBER>PMT/001</VOUCHERNUMBER>
        <DATE>20260415</DATE>
        <NARRATION>Payment to supplier</NARRATION>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>HDFC Bank</LEDGERNAME>
          <AMOUNT>-10000</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>ABC Suppliers</LEDGERNAME>
          <AMOUNT>10000</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE>
  </BODY>
</ENVELOPE>
```

## Frontend Usage

### Via UI (Recommended)

1. **Open Import Menu**
   - Press `Alt+X` or click Import/Export
   - Select import type

2. **Import Excel**
   - Select type: Ledgers/Groups/Vouchers/Stock Items
   - Download template
   - Fill with data
   - Upload file
   - Review results

3. **Bank Statement**
   - Select bank ledger
   - Choose format (Excel/CSV)
   - Upload statement
   - Review match results
   - Check suggestions

4. **Tally XML**
   - Select company
   - Upload XML file
   - Review import results

### Via JavaScript

```javascript
// Download template
fetch('/api/import/template/ledgers')
  .then(res => res.blob())
  .then(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ledgers.xlsx';
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
    console.log(`Success: ${result.success_count}`);
    console.log(`Errors: ${result.error_count}`);
  });
```

## Validation Rules

### Ledgers
- ✓ Name required
- ✓ Group must exist
- ✓ Opening balance must be numeric

### Vouchers
- ✓ Voucher type must exist
- ✓ Date required and valid
- ✓ Minimum 2 entries
- ✓ All ledgers must exist
- ✓ Debits = Credits (tolerance ±0.01)

### Bank Statements
- ✓ Date parseable
- ✓ Amounts numeric
- ✓ Bank ledger exists

### XML
- ✓ Valid XML structure
- ✓ Required elements present
- ✓ Voucher type exists
- ✓ All ledgers exist

## Auto-Matching Logic

### Bank Statements
1. **By Cheque Number** (exact match)
   - Matches statement cheque_number to voucher cheque records

2. **By Amount + Date**
   - Amount within ±0.01
   - Date within ±3 days
   - Bank ledger matches

### Ledger Suggestions
Keyword-based mapping:
- "salary" → Salary Expense
- "rent" → Rent Expense
- "electricity" → Electricity Expense
- "interest" → Interest Paid
- "tax" → Tax Payment
- "neft/rtgs/charges" → Bank Charges

## Error Handling

### Common Errors

**Excel Import:**
```
Missing required columns: Name, Group Name
Group not found: Sales Accounts
Opening balance must be a number
Ledger not found: ABC Corp
Voucher doesn't balance: Dr=5000, Cr=5500
```

**Bank Statement:**
```
ledger_id is required
Invalid date format
Missing columns after mapping: date, description
```

**XML Import:**
```
Invalid XML: syntax error at line 5
Unknown voucher type: CustomVoucher
Ledger not found: ABC Corporation
```

### Response Format
```json
{
  "status": "completed",
  "total_records": 100,
  "success_count": 95,
  "error_count": 5,
  "errors": [
    {
      "row": 23,
      "error": "Ledger not found: ABC Corp"
    }
  ],
  "created_ids": [1, 2, 3, ...]
}
```

## Bank Format Auto-Detection

### HDFC Bank
```
Expected Columns:
- Date
- Narration
- Withdrawal Amt.
- Deposit Amt.
- Closing Balance
```

### ICICI Bank
```
Expected Columns:
- Transaction Date
- Description
- Debit
- Credit
- Balance
```

### Generic Format
```
Required Columns:
- date (YYYY-MM-DD)
- description
- debit (amount)
- credit (amount)
- balance (optional)
- cheque_number (optional)
- reference (optional)
```

## Testing

### Run Test Suite

```bash
cd examples
python test_import.py
```

**Output:**
- Downloads all templates
- Shows sample data formats
- Creates sample XML file
- Provides curl commands for testing

### Manual Testing

1. **Test Template Download**
   ```bash
   curl -o test.xlsx http://localhost:8000/api/import/template/ledgers
   # Open test.xlsx and verify format
   ```

2. **Test Import**
   - Fill template with valid data
   - Import via UI or API
   - Check results

3. **Test Error Handling**
   - Create invalid data (missing groups, unbalanced vouchers)
   - Import and verify error messages

## Best Practices

### Excel Import
1. Always download template first
2. Keep sample row for reference
3. Don't modify headers
4. Ensure referenced masters exist
5. For vouchers, group by voucher number
6. Verify Dr = Cr before import

### Bank Statement
1. Use consistent date format
2. Include cheque numbers
3. Review suggestions
4. Create missing ledgers first
5. Use default column names for auto-detection

### XML Import
1. Validate XML before upload
2. Ensure ledgers exist
3. Use Tally native export
4. Match voucher type names exactly
5. Use YYYYMMDD date format

### Performance
- Batch size: recommended ≤ 1000 records per file
- Large files: split into smaller batches
- Validate data locally before import
- Run imports during off-peak hours

## Troubleshooting

### pandas/openpyxl not installed
```bash
pip install pandas openpyxl
```

### "Group not found" errors
1. List groups: `curl http://localhost:8000/api/groups`
2. Create missing groups via UI
3. Match names exactly (case-sensitive)

### Voucher doesn't balance
- Sum debits = sum credits
- Check for missing entries
- Verify positive amounts
- Tolerance: ±0.01

### Bank statement not matching
- Verify ledger ID
- Check date formats
- Include cheque numbers
- Review suggestions

### XML parse errors
- Validate XML syntax
- Check element nesting
- Use UTF-8 encoding
- Include required elements

## Advanced Usage

### Custom Column Mapping

```python
# For non-standard bank formats
column_mapping = {
    "Txn Date": "date",
    "Particulars": "description",
    "Withdraw": "debit",
    "Deposit": "credit",
    "Running Balance": "balance"
}

# Upload with custom mapping
# (requires backend modification)
```

### Batch Processing

```python
import os
import requests

files = [f for f in os.listdir('.') if f.endswith('.xlsx')]

for file in files:
    with open(file, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/import/excel/ledgers',
            files={'file': f}
        )
        result = response.json()
        print(f"{file}: {result['success_count']} imported")
```

### Integration with ETL Pipelines

```python
# Example: Daily bank statement import
import schedule
import requests

def import_daily_statement():
    # Download from bank API
    statement = download_from_bank_api()

    # Import to RecordX
    with open('daily_statement.xlsx', 'wb') as f:
        f.write(statement)

    with open('daily_statement.xlsx', 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/import/bank-statement',
            files={'file': f},
            params={'ledger_id': 5, 'file_format': 'excel'}
        )

    result = response.json()
    notify_admin(f"Imported {result['matched_count']} transactions")

schedule.every().day.at("09:00").do(import_daily_statement)
```

## Roadmap

### Phase 1 (Current)
- ✅ Excel templates (ledgers, vouchers)
- ✅ Excel import with validation
- ✅ Bank statement import
- ✅ Tally XML import
- ✅ Frontend UI
- ✅ Auto-matching
- ✅ Ledger suggestions

### Phase 2 (Planned)
- ⏳ Groups import
- ⏳ Stock items import
- ⏳ Export functionality
- ⏳ Import history tracking
- ⏳ Rollback capability
- ⏳ Preview before commit
- ⏳ Duplicate detection

### Phase 3 (Future)
- 📋 Scheduled imports
- 📋 Webhook integration
- 📋 Custom mapping presets
- 📋 Bulk operations API
- 📋 Import analytics
- 📋 Data transformation rules

## Support

### Documentation
- [IMPORT_ETL_SUMMARY.md](./IMPORT_ETL_SUMMARY.md) - Detailed implementation
- [IMPORT_API_REFERENCE.md](./IMPORT_API_REFERENCE.md) - Complete API docs
- [examples/test_import.py](./examples/test_import.py) - Test suite

### Getting Help
1. Check error messages in import results
2. Review validation rules
3. Test with sample templates
4. Check server logs for details

### Common Issues
- Ensure server is running
- Install pandas & openpyxl
- Verify masters exist before import
- Check file format and encoding
- Review validation errors carefully

## License

Part of RecordX.Finance project.
