#!/usr/bin/env python3
"""Example: Creating vouchers of all 16 types."""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tally_mac_clone.database import Database
from tally_mac_clone.models import Voucher

db = Database("sqlite:///./example_all_vouchers.db")
db.create_tables()
db.seed_default_data()

# Create company
company = db.create_company("Example Corp", date(2024, 4, 1))

# Create ledgers
cash = db.create_ledger("Cash", db.get_group_by_name("Cash-in-Hand").id, 10000)
bank = db.create_ledger("HDFC Bank", db.get_group_by_name("Bank Accounts").id, 50000)
customer = db.create_ledger("ABC Customer", db.get_group_by_name("Sundry Debtors").id)
supplier = db.create_ledger("XYZ Supplier", db.get_group_by_name("Sundry Creditors").id)
sales_acc = db.create_ledger("Sales A/c", db.get_group_by_name("Sales Accounts").id)
purchase_acc = db.create_ledger("Purchase A/c", db.get_group_by_name("Purchase Accounts").id)

print("Creating examples of all 16 voucher types...\n")

# 1. SALES
sales_type = db.get_voucher_type_by_name("Sales")
sales = db.create_voucher(
    voucher_type_id=sales_type.id,
    voucher_number="S001",
    date=date.today(),
    company_id=company.id,
    narration="Sale to ABC Customer",
    entries=[
        {"ledger_id": customer.id, "amount": 10000, "is_debit": True},
        {"ledger_id": sales_acc.id, "amount": 10000, "is_debit": False},
    ],
)
# Set type-specific fields
with db.session() as session:
    v = session.get(Voucher, sales.id)
    v.affects_inventory = True
    v.due_date = date.today() + timedelta(days=30)
print("✓ Sales voucher created (S001)")

# 2. PURCHASE
purchase_type = db.get_voucher_type_by_name("Purchase")
purchase = db.create_voucher(
    voucher_type_id=purchase_type.id,
    voucher_number="P001",
    date=date.today(),
    company_id=company.id,
    narration="Purchase from XYZ Supplier",
    entries=[
        {"ledger_id": purchase_acc.id, "amount": 5000, "is_debit": True},
        {"ledger_id": supplier.id, "amount": 5000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, purchase.id)
    v.affects_inventory = True
    v.due_date = date.today() + timedelta(days=15)
print("✓ Purchase voucher created (P001)")

# 3. PAYMENT
payment_type = db.get_voucher_type_by_name("Payment")
payment = db.create_voucher(
    voucher_type_id=payment_type.id,
    voucher_number="PAY001",
    date=date.today(),
    company_id=company.id,
    narration="Payment to supplier",
    entries=[
        {"ledger_id": supplier.id, "amount": 2000, "is_debit": True},
        {"ledger_id": bank.id, "amount": 2000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, payment.id)
    v.affects_bank = True
    v.bank_ledger_id = bank.id
print("✓ Payment voucher created (PAY001)")

# 4. RECEIPT
receipt_type = db.get_voucher_type_by_name("Receipt")
receipt = db.create_voucher(
    voucher_type_id=receipt_type.id,
    voucher_number="RCP001",
    date=date.today(),
    company_id=company.id,
    narration="Receipt from customer",
    entries=[
        {"ledger_id": cash.id, "amount": 5000, "is_debit": True},
        {"ledger_id": customer.id, "amount": 5000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, receipt.id)
    v.affects_bank = True
    v.bank_ledger_id = cash.id
print("✓ Receipt voucher created (RCP001)")

# 5. JOURNAL
journal_type = db.get_voucher_type_by_name("Journal")
depreciation = db.create_ledger("Depreciation", db.get_group_by_name("Indirect Expenses").id)
journal = db.create_voucher(
    voucher_type_id=journal_type.id,
    voucher_number="JV001",
    date=date.today(),
    company_id=company.id,
    narration="Depreciation for the month",
    entries=[
        {"ledger_id": depreciation.id, "amount": 1000, "is_debit": True},
        {"ledger_id": customer.id, "amount": 1000, "is_debit": False},
    ],
)
print("✓ Journal voucher created (JV001)")

# 6. CONTRA
contra_type = db.get_voucher_type_by_name("Contra")
contra = db.create_voucher(
    voucher_type_id=contra_type.id,
    voucher_number="CON001",
    date=date.today(),
    company_id=company.id,
    narration="Cash deposit to bank",
    entries=[
        {"ledger_id": bank.id, "amount": 2000, "is_debit": True},
        {"ledger_id": cash.id, "amount": 2000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, contra.id)
    v.affects_bank = True
    v.bank_ledger_id = bank.id
print("✓ Contra voucher created (CON001)")

# 7. CREDIT NOTE
cn_type = db.get_voucher_type_by_name("Credit Note")
cn = db.create_voucher(
    voucher_type_id=cn_type.id,
    voucher_number="CN001",
    date=date.today(),
    company_id=company.id,
    narration="Sales return from customer",
    entries=[
        {"ledger_id": sales_acc.id, "amount": 500, "is_debit": True},
        {"ledger_id": customer.id, "amount": 500, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, cn.id)
    v.affects_inventory = True
    v.original_voucher_id = sales.id
    v.adjustment_reason = "Damaged goods returned"
print("✓ Credit Note created (CN001)")

# 8. DEBIT NOTE
dn_type = db.get_voucher_type_by_name("Debit Note")
dn = db.create_voucher(
    voucher_type_id=dn_type.id,
    voucher_number="DN001",
    date=date.today(),
    company_id=company.id,
    narration="Purchase return to supplier",
    entries=[
        {"ledger_id": supplier.id, "amount": 300, "is_debit": True},
        {"ledger_id": purchase_acc.id, "amount": 300, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, dn.id)
    v.affects_inventory = True
    v.original_voucher_id = purchase.id
    v.adjustment_reason = "Quality issue"
print("✓ Debit Note created (DN001)")

# 9. DELIVERY NOTE
del_type = db.get_voucher_type_by_name("Delivery Note")
delivery = db.create_voucher(
    voucher_type_id=del_type.id,
    voucher_number="DEL001",
    date=date.today(),
    company_id=company.id,
    narration="Goods dispatched to customer",
    entries=[
        {"ledger_id": customer.id, "amount": 3000, "is_debit": True},
        {"ledger_id": sales_acc.id, "amount": 3000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, delivery.id)
    v.affects_inventory = True
    v.transport_mode = "Road"
    v.vehicle_number = "MH-01-AB-1234"
    v.carrier_name = "Fast Transport"
    v.dispatch_date = date.today()
print("✓ Delivery Note created (DEL001)")

# 10. RECEIPT NOTE
rn_type = db.get_voucher_type_by_name("Receipt Note")
receipt_note = db.create_voucher(
    voucher_type_id=rn_type.id,
    voucher_number="RN001",
    date=date.today(),
    company_id=company.id,
    narration="Goods received from supplier",
    entries=[
        {"ledger_id": purchase_acc.id, "amount": 2000, "is_debit": True},
        {"ledger_id": supplier.id, "amount": 2000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, receipt_note.id)
    v.affects_inventory = True
    v.transport_mode = "Road"
    v.vehicle_number = "GJ-05-CD-5678"
    v.carrier_name = "Quick Logistics"
print("✓ Receipt Note created (RN001)")

# 11. REJECTION IN
rej_in_type = db.get_voucher_type_by_name("Rejection In")
rej_in = db.create_voucher(
    voucher_type_id=rej_in_type.id,
    voucher_number="REJ-IN001",
    date=date.today(),
    company_id=company.id,
    narration="Rejection to supplier",
    entries=[
        {"ledger_id": supplier.id, "amount": 200, "is_debit": True},
        {"ledger_id": purchase_acc.id, "amount": 200, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, rej_in.id)
    v.affects_inventory = True
    v.original_voucher_id = receipt_note.id
print("✓ Rejection In created (REJ-IN001)")

# 12. REJECTION OUT
rej_out_type = db.get_voucher_type_by_name("Rejection Out")
rej_out = db.create_voucher(
    voucher_type_id=rej_out_type.id,
    voucher_number="REJ-OUT001",
    date=date.today(),
    company_id=company.id,
    narration="Rejection from customer",
    entries=[
        {"ledger_id": sales_acc.id, "amount": 150, "is_debit": True},
        {"ledger_id": customer.id, "amount": 150, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, rej_out.id)
    v.affects_inventory = True
    v.original_voucher_id = delivery.id
print("✓ Rejection Out created (REJ-OUT001)")

# 13. STOCK JOURNAL
stk_type = db.get_voucher_type_by_name("Stock Journal")
stock_jrnl = db.create_voucher(
    voucher_type_id=stk_type.id,
    voucher_number="STK001",
    date=date.today(),
    company_id=company.id,
    narration="Stock transfer between godowns",
    entries=[],  # Stock journal typically doesn't affect ledger balances
)
with db.session() as session:
    v = session.get(Voucher, stock_jrnl.id)
    v.affects_inventory = True
    v.from_godown = "Main Warehouse"
    v.to_godown = "Branch Warehouse"
print("✓ Stock Journal created (STK001)")

# 14. PHYSICAL STOCK
ps_type = db.get_voucher_type_by_name("Physical Stock")
phys_stock = db.create_voucher(
    voucher_type_id=ps_type.id,
    voucher_number="PS001",
    date=date.today(),
    company_id=company.id,
    narration="Physical stock verification adjustment",
    entries=[],  # Physical stock typically recorded in stock items
)
with db.session() as session:
    v = session.get(Voucher, phys_stock.id)
    v.affects_inventory = True
print("✓ Physical Stock created (PS001)")

# 15. MEMORANDUM
mem_type = db.get_voucher_type_by_name("Memorandum")
memo = db.create_voucher(
    voucher_type_id=mem_type.id,
    voucher_number="MEM001",
    date=date.today(),
    company_id=company.id,
    narration="Materials sent for job work",
    entries=[],  # Memorandum tracks movement, not ownership transfer
)
with db.session() as session:
    v = session.get(Voucher, memo.id)
    v.is_job_work = True
    v.job_work_out = True  # Material sent out
    v.affects_inventory = True
print("✓ Memorandum created (MEM001)")

# 16. REVERSING JOURNAL
rj_type = db.get_voucher_type_by_name("Reversing Journal")
rev_jrnl = db.create_voucher(
    voucher_type_id=rj_type.id,
    voucher_number="RJ001",
    date=date.today(),
    company_id=company.id,
    narration="Reversal of depreciation entry",
    entries=[
        {"ledger_id": customer.id, "amount": 1000, "is_debit": True},
        {"ledger_id": depreciation.id, "amount": 1000, "is_debit": False},
    ],
)
with db.session() as session:
    v = session.get(Voucher, rev_jrnl.id)
    v.original_voucher_id = journal.id
    v.reversal_date = date.today() + timedelta(days=30)
print("✓ Reversing Journal created (RJ001)")

print("\n" + "="*80)
print("ALL 16 VOUCHER TYPES CREATED SUCCESSFULLY!")
print("="*80)
print(f"\nDatabase: example_all_vouchers.db")
print(f"Company: {company.name}")
print(f"Total vouchers: 16")
print("\nVouchers created:")
print("  1. Sales (S001)")
print("  2. Purchase (P001)")
print("  3. Payment (PAY001)")
print("  4. Receipt (RCP001)")
print("  5. Journal (JV001)")
print("  6. Contra (CON001)")
print("  7. Credit Note (CN001)")
print("  8. Debit Note (DN001)")
print("  9. Delivery Note (DEL001)")
print(" 10. Receipt Note (RN001)")
print(" 11. Rejection In (REJ-IN001)")
print(" 12. Rejection Out (REJ-OUT001)")
print(" 13. Stock Journal (STK001)")
print(" 14. Physical Stock (PS001)")
print(" 15. Memorandum (MEM001)")
print(" 16. Reversing Journal (RJ001)")
