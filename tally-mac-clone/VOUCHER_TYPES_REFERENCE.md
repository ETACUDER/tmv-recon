# Tally Voucher Types - Complete Reference

## Overview
This document describes all 16 Tally voucher types supported in the system, their purposes, and type-specific fields.

---

## 1. Sales
**Method:** Invoice  
**Prefix:** S  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record sales transactions (both cash and credit).

### Key Fields
- `affects_inventory`: True (reduces stock)
- `due_date`: For credit sales
- Standard ledger entries for customer and sales account

### Example Usage
- Cash sales
- Credit sales with payment terms
- Sales invoice generation

---

## 2. Purchase
**Method:** Invoice  
**Prefix:** P  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record purchase transactions from suppliers.

### Key Fields
- `affects_inventory`: True (increases stock)
- `due_date`: For credit purchases
- Standard ledger entries for supplier and purchase account

### Example Usage
- Cash purchases
- Credit purchases
- Purchase invoice recording

---

## 3. Payment
**Method:** Banking  
**Prefix:** PAY  
**Requires Inventory:** No  
**Requires Banking:** Yes

### Purpose
Record all outgoing payments (cash, cheque, bank transfer).

### Key Fields
- `affects_bank`: True
- `bank_ledger_id`: Source bank/cash account
- Optional cheque details via `Cheque` model

### Example Usage
- Supplier payments
- Expense payments
- Salary payments
- Loan repayments

---

## 4. Receipt
**Method:** Banking  
**Prefix:** RCP  
**Requires Inventory:** No  
**Requires Banking:** Yes

### Purpose
Record all incoming receipts from customers or other sources.

### Key Fields
- `affects_bank`: True
- `bank_ledger_id`: Destination bank/cash account
- Optional cheque details via `Cheque` model

### Example Usage
- Customer receipts
- Cash receipts
- Income receipts

---

## 5. Journal
**Method:** Regular  
**Prefix:** JV  
**Requires Inventory:** No  
**Requires Banking:** No

### Purpose
Record non-cash accounting entries and adjustments.

### Key Fields
- Standard debit/credit entries
- No special fields required

### Example Usage
- Depreciation entries
- Provision entries
- Adjustment entries
- Period-end closing entries

---

## 6. Contra
**Method:** Banking  
**Prefix:** CON  
**Requires Inventory:** No  
**Requires Banking:** Yes

### Purpose
Record transfers between bank accounts or between cash and bank.

### Key Fields
- `affects_bank`: True
- `bank_ledger_id`: Primary bank account
- Both entries must be bank/cash accounts

### Example Usage
- Bank to bank transfer
- Cash deposit to bank
- Cash withdrawal from bank

---

## 7. Credit Note
**Method:** Invoice  
**Prefix:** CN  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record sales returns or adjustments reducing customer liability.

### Key Fields
- `affects_inventory`: True (increases stock)
- `original_voucher_id`: Reference to original sales voucher
- `adjustment_reason`: Reason for credit note

### Example Usage
- Sales returns
- Price adjustments (reduction)
- Discount corrections

---

## 8. Debit Note
**Method:** Invoice  
**Prefix:** DN  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record purchase returns or adjustments reducing supplier liability.

### Key Fields
- `affects_inventory`: True (reduces stock)
- `original_voucher_id`: Reference to original purchase voucher
- `adjustment_reason`: Reason for debit note

### Example Usage
- Purchase returns to supplier
- Price adjustments (increase)
- Quality issue adjustments

---

## 9. Delivery Note
**Method:** Inventory  
**Prefix:** DEL  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Track goods dispatched to customers (non-invoiced shipment).

### Key Fields
- `affects_inventory`: True (reduces stock)
- `transport_mode`: Road/Rail/Air/Ship
- `vehicle_number`: Transporter vehicle number
- `carrier_name`: Transporter name
- `dispatch_date`: Date of dispatch

### Example Usage
- Goods sent on approval
- Stock transfer to branch
- Consignment sales
- Delivery before invoicing

---

## 10. Receipt Note
**Method:** Inventory  
**Prefix:** RN  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Track goods received from suppliers (non-invoiced receipt).

### Key Fields
- `affects_inventory`: True (increases stock)
- `transport_mode`: Road/Rail/Air/Ship
- `vehicle_number`: Transporter vehicle number
- `carrier_name`: Transporter name
- `dispatch_date`: Date received

### Example Usage
- Goods received on approval
- Stock received from branch
- Receipt before invoice

---

## 11. Rejection In
**Method:** Inventory  
**Prefix:** REJ-IN  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record rejection of goods received (return to supplier without debit note).

### Key Fields
- `affects_inventory`: True (reduces stock)
- `original_voucher_id`: Reference to receipt note or purchase

### Example Usage
- Quality rejection to supplier
- Partial rejection of received goods

---

## 12. Rejection Out
**Method:** Inventory  
**Prefix:** REJ-OUT  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record goods rejected by customers (without credit note).

### Key Fields
- `affects_inventory`: True (increases stock)
- `original_voucher_id`: Reference to delivery note or sales

### Example Usage
- Customer rejection received back
- Quality issues from customer

---

## 13. Stock Journal
**Method:** Inventory  
**Prefix:** STK  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Record stock transfers between godowns/locations.

### Key Fields
- `affects_inventory`: True
- `from_godown`: Source location
- `to_godown`: Destination location

### Example Usage
- Inter-godown transfer
- Location-to-location movement
- Stock reallocation

---

## 14. Physical Stock
**Method:** Inventory  
**Prefix:** PS  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Adjust stock quantities based on physical verification.

### Key Fields
- `affects_inventory`: True
- Records difference between system and physical stock

### Example Usage
- Stock count adjustments
- Shortage/excess recording
- Inventory reconciliation

---

## 15. Memorandum
**Method:** Inventory  
**Prefix:** MEM  
**Requires Inventory:** Yes  
**Requires Banking:** No

### Purpose
Track materials sent/received for job work (not a sale/purchase).

### Key Fields
- `is_job_work`: True
- `job_work_out`: True for outward, False for inward
- `affects_inventory`: True (but tracked separately)

### Example Usage
- Materials sent for processing
- Materials received after processing
- Job work tracking

---

## 16. Reversing Journal
**Method:** Regular  
**Prefix:** RJ  
**Requires Inventory:** No  
**Requires Banking:** No

### Purpose
Automatically reverse a previous journal entry on specified date.

### Key Fields
- `original_voucher_id`: Reference to journal being reversed
- `reversal_date`: Date when reversal takes effect
- Creates opposite entries automatically

### Example Usage
- Reverse temporary provisions
- Undo accrual entries
- Period-end reversals

---

## Database Schema

### Voucher Table (Extended Fields)

```sql
-- Inventory fields
affects_inventory BOOLEAN DEFAULT 0 NOT NULL

-- Banking fields
affects_bank BOOLEAN DEFAULT 0 NOT NULL
bank_ledger_id INTEGER REFERENCES ledgers(id)

-- Transport fields
transport_mode VARCHAR(50)
vehicle_number VARCHAR(50)
carrier_name VARCHAR(255)
dispatch_date DATE

-- Due date
due_date DATE

-- Reference fields
original_voucher_id INTEGER REFERENCES vouchers(id)
reversal_date DATE
adjustment_reason TEXT

-- Stock transfer
from_godown VARCHAR(255)
to_godown VARCHAR(255)

-- Job work
is_job_work BOOLEAN DEFAULT 0 NOT NULL
job_work_out BOOLEAN DEFAULT 1 NOT NULL
```

### VoucherTypeConfig Table

```sql
CREATE TABLE voucher_type_configs (
    id INTEGER PRIMARY KEY,
    voucher_type_id INTEGER NOT NULL UNIQUE,
    method_of_voucher VARCHAR(50) DEFAULT 'Regular' NOT NULL,
    requires_inventory BOOLEAN DEFAULT 0 NOT NULL,
    requires_banking BOOLEAN DEFAULT 0 NOT NULL,
    numbering_series_prefix VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (voucher_type_id) REFERENCES voucher_types(id)
)
```

---

## Migration Notes

All new fields are **nullable** or have **defaults** to ensure backward compatibility with existing databases.

To migrate an existing database:
```bash
python3 migrate_voucher_types.py
```

This will:
1. Add all new columns to `vouchers` table
2. Create `voucher_type_configs` table
3. Seed all 16 voucher types with configurations
4. Preserve existing data

---

## Quick Reference Matrix

| Voucher Type      | Inventory | Banking | Key Distinguishing Fields                    |
|-------------------|-----------|---------|----------------------------------------------|
| Sales             | ✓         |         | due_date                                     |
| Purchase          | ✓         |         | due_date                                     |
| Payment           |           | ✓       | bank_ledger_id                               |
| Receipt           |           | ✓       | bank_ledger_id                               |
| Journal           |           |         | -                                            |
| Contra            |           | ✓       | bank_ledger_id (both entries)                |
| Credit Note       | ✓         |         | original_voucher_id, adjustment_reason       |
| Debit Note        | ✓         |         | original_voucher_id, adjustment_reason       |
| Delivery Note     | ✓         |         | transport_mode, vehicle_number, dispatch_date|
| Receipt Note      | ✓         |         | transport_mode, vehicle_number, dispatch_date|
| Rejection In      | ✓         |         | original_voucher_id                          |
| Rejection Out     | ✓         |         | original_voucher_id                          |
| Stock Journal     | ✓         |         | from_godown, to_godown                       |
| Physical Stock    | ✓         |         | -                                            |
| Memorandum        | ✓         |         | is_job_work, job_work_out                    |
| Reversing Journal |           |         | original_voucher_id, reversal_date           |

---

## Implementation Status

✅ Models updated with all type-specific fields  
✅ VoucherTypeConfig model added  
✅ Database seeding updated for all 16 types  
✅ Migration script provided  
✅ All fields nullable/defaulted for backward compatibility  

**Files Modified:**
- `/src/tally_mac_clone/models.py` - Extended Voucher and added VoucherTypeConfig
- `/src/tally_mac_clone/database.py` - Updated seed_default_data()
- `migrate_voucher_types.py` - Migration script for existing databases
- `test_voucher_types.py` - Verification test script
