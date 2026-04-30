# Company Model Quick Reference

## Complete Field List (27 fields)

### Base Fields (4)
- `id` - Primary key
- `name` - Company name (unique)
- `financial_year_start` - Financial year start date
- `created_at` - Record creation timestamp

### Financial Settings (3)
- `books_beginning_from` - Accounting start date
- `tally_vault_password` - Security password (store encrypted)
- `maintain_accounts_only` - Accounts-only mode flag

### Company Details (8)
- `mailing_name` - Short name
- `address` - Full address
- `state` - State/Province
- `country` - Country (default: "India")
- `pincode` - ZIP/Postal code
- `phone` - Contact phone
- `email` - Contact email
- `website` - Company website

### Tax Registration (5)
- `pan` - Permanent Account Number
- `gstin` - GST Identification Number
- `gst_registration_type` - Regular/Composition
- `tan` - Tax Deduction Account Number
- `cin` - Corporate Identity Number

### Feature Flags (6)
- `maintain_bill_wise` - Bill-wise tracking (default: True)
- `use_cost_centers` - Cost center allocation (default: False)
- `enable_multi_currency` - Multi-currency support (default: False)
- `maintain_payroll` - Payroll management (default: False)
- `maintain_inventory` - Inventory tracking (default: False)
- `enable_gst` - GST compliance (default: True)

### Currency (1)
- `base_currency_id` - Foreign key to Currency table

## API Usage

### Create Company
```bash
POST /api/companies
{
  "name": "Acme Corp",
  "financial_year_start": "2026-04-01",
  "gstin": "29AAACA1234A1Z5",
  "state": "Karnataka",
  "enable_gst": true
}
```

### Get Company Details
```bash
GET /api/companies/1
```

### Update Company
```bash
PATCH /api/companies/1
{
  "phone": "+91-80-12345678",
  "use_cost_centers": true
}
```

### Get Settings
```bash
GET /api/companies/1/settings
```

## Database Usage

```python
from tally_mac_clone.database import Database

db = Database()

# Create
company = db.create_company(
    name="Acme Corp",
    financial_year_start=date(2026, 4, 1),
    gstin="29AAACA1234A1Z5",
    state="Karnataka"
)

# Update
db.update_company(
    company.id,
    phone="+91-80-12345678",
    use_cost_centers=True
)

# Get settings
settings = db.get_company_settings(company.id)
```

## Migration

For existing databases:
```bash
python examples/migrate_company_schema.py
```

## Notes

- All new fields are optional (nullable=True or have defaults)
- Existing companies work without modification
- Base currency links to Currency table
- Feature flags control module availability
- Tax fields support Indian GST compliance
