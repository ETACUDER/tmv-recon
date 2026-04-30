# Bill-wise Details API Usage Guide

Quick reference for using the bill-wise details API endpoints.

## Endpoints Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/bills` | Create new bill |
| GET | `/api/bills/outstanding` | Get outstanding bills for ledger |
| POST | `/api/bills/allocate` | Allocate payment to bills |
| GET | `/api/bills/aging` | Generate aging report |

---

## 1. Create Bill

**Endpoint:** `POST /api/bills`

Creates a bill reference for tracking receivables/payables.

### Request
```json
{
  "ledger_id": 1,
  "bill_number": "INV-001",
  "bill_date": "2026-04-01",
  "due_date": "2026-05-01",
  "amount": 50000,
  "bill_type": "Receivable",
  "voucher_id": 10
}
```

### Fields
- `ledger_id` (int): Party ledger ID (debtor/creditor)
- `bill_number` (string): Invoice/bill reference number
- `bill_date` (date): Bill date (YYYY-MM-DD)
- `due_date` (date): Payment due date
- `amount` (float): Bill amount
- `bill_type` (string): "Receivable" or "Payable"
- `voucher_id` (int): Source Sales/Purchase voucher ID

### Response
```json
{
  "id": 1,
  "bill_number": "INV-001",
  "bill_date": "2026-04-01",
  "due_date": "2026-05-01",
  "original_amount": 50000,
  "pending_amount": 50000,
  "bill_type": "Receivable",
  "message": "Bill INV-001 created successfully"
}
```

### Example (curl)
```bash
curl -X POST http://localhost:8000/api/bills \
  -H "Content-Type: application/json" \
  -d '{
    "ledger_id": 1,
    "bill_number": "INV-001",
    "bill_date": "2026-04-01",
    "due_date": "2026-05-01",
    "amount": 50000,
    "bill_type": "Receivable",
    "voucher_id": 10
  }'
```

---

## 2. Get Outstanding Bills

**Endpoint:** `GET /api/bills/outstanding`

Retrieves all outstanding bills for a specific ledger with aging details.

### Query Parameters
- `ledger_id` (int, required): Ledger ID
- `as_of_date` (date, optional): Calculate outstanding as of date (default: today)

### Example Request
```
GET /api/bills/outstanding?ledger_id=1&as_of_date=2026-04-30
```

### Response
```json
{
  "ledger_id": 1,
  "as_of_date": "2026-04-30",
  "total_bills": 3,
  "total_pending": 225000,
  "bills": [
    {
      "bill_id": 1,
      "bill_number": "INV-001",
      "bill_date": "2026-03-16",
      "due_date": "2026-04-15",
      "bill_type": "Receivable",
      "original_amount": 50000,
      "pending_amount": 50000,
      "days_outstanding": 45,
      "days_overdue": 15,
      "status": "overdue"
    },
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

### Example (curl)
```bash
curl "http://localhost:8000/api/bills/outstanding?ledger_id=1"
```

---

## 3. Allocate Payment to Bills

**Endpoint:** `POST /api/bills/allocate`

Allocates a payment/receipt voucher to specific outstanding bills.

### Request
```json
{
  "voucher_id": 15,
  "allocations": [
    {
      "bill_id": 1,
      "amount": 50000
    },
    {
      "bill_id": 3,
      "amount": 70000
    }
  ]
}
```

### Fields
- `voucher_id` (int): Payment/Receipt voucher ID
- `allocations` (array): List of bill allocations
  - `bill_id` (int): Bill to allocate to
  - `amount` (float): Amount to allocate

### Validation
- Allocation amount cannot exceed bill's pending amount
- Bill must exist and belong to same ledger as voucher

### Response
```json
{
  "voucher_id": 15,
  "allocated_count": 2,
  "allocations": [
    {
      "id": 1,
      "bill_id": 1,
      "allocated_amount": 50000,
      "allocation_date": "2026-04-20"
    },
    {
      "id": 2,
      "bill_id": 3,
      "allocated_amount": 70000,
      "allocation_date": "2026-04-20"
    }
  ],
  "message": "Allocated payment to 2 bills"
}
```

### Example (curl)
```bash
curl -X POST http://localhost:8000/api/bills/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "voucher_id": 15,
    "allocations": [
      {"bill_id": 1, "amount": 50000},
      {"bill_id": 3, "amount": 70000}
    ]
  }'
```

---

## 4. Generate Aging Report

**Endpoint:** `GET /api/bills/aging`

Generates comprehensive aging analysis for receivables/payables.

### Query Parameters
- `ledger_id` (int, optional): Specific ledger ID
- `group` (string, optional): Group name (e.g., "Sundry Debtors")
- `as_of_date` (date, optional): Calculate aging as of date (default: today)
- `buckets` (string, optional): Comma-separated ranges (default: "0-30,31-60,61-90,91-180,181+")

**Note:** Specify either `ledger_id` OR `group`, not both.

### Example Requests

#### Group-level aging (all debtors)
```
GET /api/bills/aging?group=Sundry Debtors
```

#### Specific ledger aging
```
GET /api/bills/aging?ledger_id=1
```

#### Custom aging buckets
```
GET /api/bills/aging?group=Sundry Debtors&buckets=0-15,16-30,31-45,46+
```

### Response
```json
{
  "as_of_date": "2026-04-30",
  "total_outstanding": 225000,
  "total_bills": 3,
  "buckets": [
    {
      "range": "0-30",
      "count": 1,
      "amount": 75000,
      "percentage": 33.3
    },
    {
      "range": "31-60",
      "count": 1,
      "amount": 50000,
      "percentage": 22.2
    },
    {
      "range": "61-90",
      "count": 1,
      "amount": 100000,
      "percentage": 44.4
    }
  ],
  "bills": [
    {
      "ledger_name": "ABC Industries",
      "bill_number": "INV-001",
      "bill_date": "2026-03-16",
      "due_date": "2026-04-15",
      "pending_amount": 50000,
      "days_outstanding": 45,
      "bucket": "31-60"
    },
    {
      "ledger_name": "ABC Industries",
      "bill_number": "INV-002",
      "bill_date": "2026-04-10",
      "due_date": "2026-05-10",
      "pending_amount": 75000,
      "days_outstanding": 20,
      "bucket": "0-30"
    }
  ]
}
```

### Example (curl)
```bash
# All debtors aging
curl "http://localhost:8000/api/bills/aging?group=Sundry%20Debtors"

# Custom buckets
curl "http://localhost:8000/api/bills/aging?group=Sundry%20Debtors&buckets=0-30,31-60,61-90,91+"
```

---

## Standard Aging Buckets

Default aging classification:

| Range | Description | Risk Level |
|-------|-------------|------------|
| 0-30 days | Current | Low |
| 31-60 days | Slightly overdue | Medium |
| 61-90 days | Moderately overdue | Medium-High |
| 91-180 days | Seriously overdue | High |
| 181+ days | Bad debt risk | Very High |

---

## Complete Workflow Example

### 1. Create Sales Invoice
```bash
# Create voucher
curl -X POST http://localhost:8000/api/vouchers \
  -H "Content-Type: application/json" \
  -d '{
    "voucher_type": "Sales",
    "voucher_number": "INV-001",
    "date": "2026-04-01",
    "company_id": 1,
    "narration": "Sales to ABC Industries",
    "entries": [
      {"ledger_id": 5, "amount": 50000, "is_debit": true},
      {"ledger_id": 10, "amount": 50000, "is_debit": false}
    ]
  }'
# Response: {"id": 10, ...}

# Create bill reference
curl -X POST http://localhost:8000/api/bills \
  -H "Content-Type: application/json" \
  -d '{
    "ledger_id": 5,
    "bill_number": "INV-001",
    "bill_date": "2026-04-01",
    "due_date": "2026-05-01",
    "amount": 50000,
    "bill_type": "Receivable",
    "voucher_id": 10
  }'
```

### 2. Check Outstanding
```bash
curl "http://localhost:8000/api/bills/outstanding?ledger_id=5"
```

### 3. Record Payment
```bash
# Create receipt voucher
curl -X POST http://localhost:8000/api/vouchers \
  -H "Content-Type: application/json" \
  -d '{
    "voucher_type": "Receipt",
    "voucher_number": "RCP-001",
    "date": "2026-04-15",
    "company_id": 1,
    "narration": "Payment received",
    "entries": [
      {"ledger_id": 3, "amount": 50000, "is_debit": true},
      {"ledger_id": 5, "amount": 50000, "is_debit": false}
    ]
  }'
# Response: {"id": 15, ...}

# Allocate to bill
curl -X POST http://localhost:8000/api/bills/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "voucher_id": 15,
    "allocations": [
      {"bill_id": 1, "amount": 50000}
    ]
  }'
```

### 4. Generate Aging Report
```bash
curl "http://localhost:8000/api/bills/aging?group=Sundry%20Debtors"
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Allocation amount 60000 exceeds pending amount 50000 for bill INV-001"
}
```

### 404 Not Found
```json
{
  "detail": "Bill 123 not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Database error message"
}
```

---

## Notes

1. **Bill Creation**: Typically created automatically when Sales/Purchase vouchers are recorded
2. **Pending Amount**: Automatically updated when payments are allocated
3. **Partial Payments**: Supported - allocate portion of payment to specific bills
4. **Multiple Bills**: Single payment can be allocated to multiple bills
5. **Aging Calculation**: Days outstanding = (as_of_date - bill_date)
6. **Overdue Calculation**: Days overdue = max(0, as_of_date - due_date)

---

## Testing

Use the included demo script:
```bash
python3 examples/billwise_demo.py
```

Or test individual functions:
```bash
python3 examples/test_bill_api.py
```
