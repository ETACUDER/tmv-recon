# Bill-wise Details System Implementation

Complete implementation of bill-wise tracking for receivables and payables aging analysis.

## Features Implemented

### 1. Database Models (models.py)

#### Bill Model
Tracks individual invoices/bills for party ledgers:
- `bill_number`: Invoice/bill reference
- `bill_date`: Bill date
- `due_date`: Payment due date
- `original_amount`: Original bill amount
- `pending_amount`: Outstanding balance
- `bill_type`: 'Receivable' or 'Payable'
- `created_from_voucher_id`: Links to source Sales/Purchase voucher
- `ledger_id`: Party ledger (Sundry Debtor/Creditor)

#### BillAllocation Model
Tracks payment allocations against bills:
- `bill_id`: Bill being paid
- `voucher_id`: Payment/Receipt voucher
- `allocated_amount`: Amount allocated
- `allocation_date`: Date of allocation

### 2. Database Functions (database.py)

#### `create_bill()`
Creates bill from sales/purchase invoice:
```python
bill = db.create_bill(
    ledger_id=customer.id,
    bill_number="INV-001",
    bill_date=date(2026, 3, 16),
    due_date=date(2026, 4, 15),
    amount=50000,
    bill_type="Receivable",
    voucher_id=sales_voucher.id,
)
```

#### `allocate_payment_to_bills()`
Allocates payment/receipt to outstanding bills:
```python
allocations = db.allocate_payment_to_bills(
    voucher_id=receipt_voucher.id,
    allocations=[
        {"bill_id": 1, "amount": 50000},  # Full payment
        {"bill_id": 3, "amount": 70000},  # Partial payment
    ]
)
```
- Validates allocation amounts against pending balances
- Updates bill pending amounts automatically
- Links payment vouchers to bills

#### `get_outstanding_bills()`
Retrieves outstanding bills for a ledger with aging info:
```python
bills = db.get_outstanding_bills(
    ledger_id=customer.id,
    as_of_date=date(2026, 4, 30)
)
```
Returns:
- Bill details (number, dates, amounts)
- Days outstanding (from bill date)
- Days overdue (from due date)
- Status (current/overdue)

#### `get_aging_report()`
Generates comprehensive aging analysis:
```python
report = db.get_aging_report(
    group_name="Sundry Debtors",  # or ledger_id for specific ledger
    as_of_date=date(2026, 4, 30),
    aging_buckets=[
        (0, 30),    # Current
        (31, 60),   # 31-60 days
        (61, 90),   # 61-90 days
        (91, 180),  # 91-180 days
        (181, 9999) # 180+ days
    ]
)
```
Returns:
- Total outstanding amount
- Bucket-wise breakdown (count, amount, percentage)
- Individual bill details with aging classification

### 3. API Endpoints (app.py)

#### POST /api/bills
Create new bill:
```json
{
  "ledger_id": 1,
  "bill_number": "INV-001",
  "bill_date": "2026-03-16",
  "due_date": "2026-04-15",
  "amount": 50000,
  "bill_type": "Receivable",
  "voucher_id": 1
}
```

#### GET /api/bills/outstanding
Get outstanding bills for a ledger:
```
GET /api/bills/outstanding?ledger_id=1&as_of_date=2026-04-30
```
Response:
```json
{
  "ledger_id": 1,
  "as_of_date": "2026-04-30",
  "total_bills": 2,
  "total_pending": 105000,
  "bills": [
    {
      "bill_id": 2,
      "bill_number": "INV-002",
      "bill_date": "2026-04-10",
      "due_date": "2026-05-10",
      "bill_type": "Receivable",
      "original_amount": 75000,
      "pending_amount": 75000,
      "days_outstanding": 20,
      "days_overdue": 0,
      "status": "current"
    }
  ]
}
```

#### POST /api/bills/allocate
Allocate payment to bills:
```json
{
  "voucher_id": 5,
  "allocations": [
    {"bill_id": 1, "amount": 50000},
    {"bill_id": 3, "amount": 70000}
  ]
}
```

#### GET /api/bills/aging
Generate aging report:
```
GET /api/bills/aging?group=Sundry Debtors&buckets=0-30,31-60,61-90,91+
```
Response:
```json
{
  "as_of_date": "2026-04-30",
  "total_outstanding": 105000,
  "total_bills": 2,
  "buckets": [
    {
      "range": "0-30",
      "count": 1,
      "amount": 75000,
      "percentage": 71.4
    },
    {
      "range": "61-90",
      "count": 1,
      "amount": 30000,
      "percentage": 28.6
    }
  ],
  "bills": [
    {
      "ledger_name": "ABC Industries",
      "bill_number": "INV-002",
      "bill_date": "2026-04-10",
      "pending_amount": 75000,
      "days_outstanding": 20,
      "bucket": "0-30"
    }
  ]
}
```

## Example Workflow

### 1. Invoice Creation
```python
# Create sales invoice
sales_voucher = db.create_voucher(
    voucher_type_id=sales_type.id,
    voucher_number="INV-001",
    date=date(2026, 3, 16),
    company_id=1,
    entries=[
        {"ledger_id": customer.id, "amount": 50000, "is_debit": True},
        {"ledger_id": sales.id, "amount": 50000, "is_debit": False},
    ]
)

# Create corresponding bill
bill = db.create_bill(
    ledger_id=customer.id,
    bill_number="INV-001",
    bill_date=date(2026, 3, 16),
    due_date=date(2026, 4, 15),  # 30 days credit
    amount=50000,
    bill_type="Receivable",
    voucher_id=sales_voucher.id,
)
```

### 2. Payment Receipt
```python
# Record payment
receipt_voucher = db.create_voucher(
    voucher_type_id=receipt_type.id,
    voucher_number="RCP-001",
    date=date(2026, 4, 20),
    company_id=1,
    entries=[
        {"ledger_id": bank.id, "amount": 120000, "is_debit": True},
        {"ledger_id": customer.id, "amount": 120000, "is_debit": False},
    ]
)

# Allocate to bills
allocations = db.allocate_payment_to_bills(
    voucher_id=receipt_voucher.id,
    allocations=[
        {"bill_id": 1, "amount": 50000},  # Full payment for INV-001
        {"bill_id": 3, "amount": 70000},  # Partial for INV-003
    ]
)
```

### 3. Aging Analysis
```python
# Check outstanding bills
bills = db.get_outstanding_bills(customer.id)
# Returns bills with days_outstanding and days_overdue

# Generate aging report for all debtors
report = db.get_aging_report(group_name="Sundry Debtors")
# Returns categorized aging buckets with totals
```

## Standard Aging Buckets

Default configuration:
- **0-30 days**: Current (within credit period)
- **31-60 days**: Slightly overdue
- **61-90 days**: Moderately overdue
- **91-180 days**: Seriously overdue
- **181+ days**: Bad debts risk

Custom buckets can be specified:
```python
aging_buckets=[
    (0, 15),    # 0-15 days
    (16, 30),   # 16-30 days
    (31, 45),   # 31-45 days
    (46, 9999), # 45+ days
]
```

## Key Features

1. **Bill Tracking**: Every sales/purchase invoice creates a bill record
2. **Payment Allocation**: Link payments to specific invoices
3. **Partial Payments**: Support partial bill settlements
4. **Aging Analysis**: Automatic calculation of days outstanding
5. **Overdue Tracking**: Days overdue from due date
6. **Flexible Reporting**: Group-level or ledger-level aging reports
7. **Custom Buckets**: Configurable aging periods

## Testing

Run the demonstration:
```bash
python3 examples/billwise_demo.py
```

This demonstrates:
- Creating 3 sales invoices with bills
- Recording payment and allocating to specific bills
- Viewing outstanding bills before/after payment
- Generating comprehensive aging report

## Integration Points

### With Existing Systems
- **Vouchers**: Bills created from Sales/Purchase vouchers
- **Ledgers**: Bills linked to party ledgers (Debtors/Creditors)
- **Groups**: Aging reports can be group-based (Sundry Debtors)

### Future Enhancements
- Auto-create bills from vouchers (configurable)
- Payment reminders for overdue bills
- Interest calculation on overdue amounts
- Credit limit checks based on outstanding bills
- Bill discounting/factoring support

## Files Modified

1. `/src/tally_mac_clone/models.py` - Added Bill and BillAllocation models
2. `/src/tally_mac_clone/database.py` - Added bill CRUD functions
3. `/src/tally_mac_clone/app.py` - Added bill API endpoints
4. `/examples/billwise_demo.py` - Complete workflow demonstration

## Summary

Complete bill-wise details system enabling:
- Reference tracking: Link invoices to payments
- Aging analysis: Standard 0-30, 31-60, 61-90, 91-180, 180+ day buckets
- Outstanding management: Track pending amounts per bill
- Flexible allocation: Allocate payments to specific bills
- Comprehensive reporting: Group or ledger-level aging reports

System ready for production use with full API support and workflow demonstration.
