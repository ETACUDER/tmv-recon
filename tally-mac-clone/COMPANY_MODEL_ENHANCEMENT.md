# Company Model Enhancement - Tally-Compatible Fields

Enhanced Company model with complete Tally ERP-compatible fields for comprehensive business management.

## Summary

**Files Modified:**
- `/src/tally_mac_clone/models.py` - Enhanced Company model
- `/src/tally_mac_clone/database.py` - Updated CRUD operations
- `/src/tally_mac_clone/app.py` - Added API endpoints

**Files Created:**
- `/examples/migrate_company_schema.py` - Database migration script
- `/examples/company_management_demo.py` - Usage demonstration

## Enhanced Company Model Fields

### 1. Financial Settings
- `books_beginning_from` (Date) - Accounting start date
- `tally_vault_password` (String, encrypted) - Security password
- `maintain_accounts_only` (Boolean) - Accounts-only mode flag

### 2. Company Details
- `mailing_name` (String) - Short name for correspondence
- `address` (Text) - Full company address
- `state` (String) - State/Province
- `country` (String, default="India") - Country
- `pincode` (String) - ZIP/Postal code
- `phone` (String) - Contact phone
- `email` (String) - Contact email
- `website` (String) - Company website

### 3. Tax Registration
- `pan` (String) - Permanent Account Number
- `gstin` (String) - GST Identification Number
- `gst_registration_type` (String) - Regular/Composition
- `tan` (String) - Tax Deduction Account Number
- `cin` (String) - Corporate Identity Number

### 4. Feature Flags
- `maintain_bill_wise` (Boolean, default=True) - Bill-wise tracking
- `use_cost_centers` (Boolean, default=False) - Cost center allocation
- `enable_multi_currency` (Boolean, default=False) - Multi-currency support
- `maintain_payroll` (Boolean, default=False) - Payroll management
- `maintain_inventory` (Boolean, default=False) - Inventory tracking
- `enable_gst` (Boolean, default=True) - GST compliance

### 5. Base Currency
- `base_currency_id` (Integer, FK) - Default currency reference
- `base_currency` (Relationship) - Currency object

## Database Operations

### create_company()
```python
db.create_company(
    name="Acme Corp",
    financial_year_start=date(2026, 4, 1),
    gstin="29AAACA1234A1Z5",
    state="Karnataka",
    enable_gst=True,
    maintain_bill_wise=True,
    base_currency_id=1
)
```

### update_company()
```python
db.update_company(
    company_id=1,
    phone="+91-80-12345678",
    email="finance@acme.com",
    use_cost_centers=True
)
```

### get_company_settings()
```python
settings = db.get_company_settings(company_id=1)
# Returns complete configuration dict
```

## API Endpoints

### GET /api/companies/{id}
Get complete company details with all fields.

**Response:**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "gstin": "29AAACA1234A1Z5",
  "state": "Karnataka",
  "maintain_bill_wise": true,
  "enable_gst": true,
  "base_currency": {
    "code": "INR",
    "symbol": "₹"
  }
}
```

### PATCH /api/companies/{id}
Update company details.

**Request:**
```json
{
  "phone": "+91-80-12345678",
  "email": "finance@acme.com",
  "use_cost_centers": true
}
```

### GET /api/companies/{id}/settings
Get company configuration.

**Response:** Complete settings object with all company fields.

## Backward Compatibility

All new fields are **optional** with sensible defaults:
- Existing companies continue working
- New fields can be added incrementally
- Migration script provided for existing databases

## Migration

For existing databases:
```bash
python examples/migrate_company_schema.py
```

This safely adds all new columns with defaults.

## Usage Example

```python
from datetime import date
from src.tally_mac_clone.database import Database

db = Database()
db.create_tables()

# Create company with full details
company = db.create_company(
    name="Acme Corporation Pvt Ltd",
    financial_year_start=date(2026, 4, 1),
    gstin="29AAACA1234A1Z5",
    state="Karnataka",
    pan="AAACA1234A",
    maintain_bill_wise=True,
    use_cost_centers=True,
    enable_gst=True
)

# Update settings
db.update_company(
    company.id,
    use_cost_centers=True,
    maintain_payroll=True
)

# Get configuration
settings = db.get_company_settings(company.id)
```

## Benefits

1. **Complete Tally Compatibility** - All essential company fields
2. **GST Compliance** - GSTIN, state, registration type
3. **Feature Flags** - Enable/disable modules per company
4. **Multi-Currency** - Base currency with conversion support
5. **Backward Compatible** - Existing data unaffected
6. **Flexible** - Optional fields with sensible defaults

## Notes

- `tally_vault_password` should be encrypted before storage
- `books_beginning_from` defaults to `financial_year_start` if not provided
- All tax fields (PAN, GSTIN, TAN, CIN) are optional
- Feature flags control which modules are active per company
- Base currency enables multi-currency accounting
