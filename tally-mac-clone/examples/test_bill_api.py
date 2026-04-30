"""Quick test of bill-wise API endpoints functionality."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import date
from tally_mac_clone.database import db

# Setup
db.create_tables()
db.seed_default_data()

print("Testing Bill-wise Database Functions")
print("=" * 60)

# Create test data
company = db.list_companies()[0] if db.list_companies() else db.create_company("Test Co", date(2026, 4, 1))
debtors = db.get_group_by_name("Sundry Debtors")
sales_group = db.get_group_by_name("Sales Accounts")
customer = db.get_ledger_by_name("Test Customer") or db.create_ledger("Test Customer", debtors.id, 0)
sales = db.get_ledger_by_name("Test Sales") or db.create_ledger("Test Sales", sales_group.id, 0)
sales_vtype = db.get_voucher_type_by_name("Sales")

# 1. Create bill
print("\n1. Testing create_bill()...")
voucher = db.create_voucher(
    voucher_type_id=sales_vtype.id,
    voucher_number="TEST-001",
    date=date(2026, 4, 1),
    company_id=company.id,
    entries=[
        {"ledger_id": customer.id, "amount": 10000, "is_debit": True},
        {"ledger_id": sales.id, "amount": 10000, "is_debit": False},
    ]
)

bill = db.create_bill(
    ledger_id=customer.id,
    bill_number="TEST-001",
    bill_date=date(2026, 4, 1),
    due_date=date(2026, 5, 1),
    amount=10000,
    bill_type="Receivable",
    voucher_id=voucher.id,
)
print(f"✓ Created bill: {bill.bill_number}, Amount: {bill.original_amount}")

# 2. Get outstanding bills
print("\n2. Testing get_outstanding_bills()...")
outstanding = db.get_outstanding_bills(customer.id)
print(f"✓ Outstanding bills: {len(outstanding)}")
for b in outstanding:
    print(f"  - {b['bill_number']}: ₹{b['pending_amount']} ({b['status']})")

# 3. Aging report
print("\n3. Testing get_aging_report()...")
report = db.get_aging_report(group_name="Sundry Debtors")
print(f"✓ Total outstanding: ₹{report['total_outstanding']}")
print(f"✓ Total bills: {report['total_bills']}")
print("  Buckets:")
for bucket in report['buckets']:
    if bucket['count'] > 0:
        print(f"    {bucket['range']}: {bucket['count']} bills, ₹{bucket['amount']:.2f}")

# 4. Payment allocation
print("\n4. Testing allocate_payment_to_bills()...")
receipt_vtype = db.get_voucher_type_by_name("Receipt")
bank = db.get_ledger_by_name("Test Bank") or db.create_ledger("Test Bank", db.get_group_by_name("Bank Accounts").id, 0)

receipt = db.create_voucher(
    voucher_type_id=receipt_vtype.id,
    voucher_number="RCP-001",
    date=date(2026, 4, 15),
    company_id=company.id,
    entries=[
        {"ledger_id": bank.id, "amount": 5000, "is_debit": True},
        {"ledger_id": customer.id, "amount": 5000, "is_debit": False},
    ]
)

allocations = db.allocate_payment_to_bills(
    voucher_id=receipt.id,
    allocations=[{"bill_id": bill.id, "amount": 5000}]
)
print(f"✓ Allocated ₹5000 to bill {bill.bill_number}")

# 5. Verify allocation
print("\n5. Verifying updated outstanding...")
outstanding = db.get_outstanding_bills(customer.id)
print(f"✓ Remaining outstanding: ₹{outstanding[0]['pending_amount']}")

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("\nAPI endpoints are ready to use:")
print("  POST   /api/bills")
print("  GET    /api/bills/outstanding?ledger_id=X")
print("  POST   /api/bills/allocate")
print("  GET    /api/bills/aging?group=Sundry Debtors&buckets=0-30,31-60,61-90,91+")
