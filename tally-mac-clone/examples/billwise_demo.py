"""Bill-wise details demonstration workflow.

This example demonstrates:
1. Creating a sales invoice with bill tracking
2. Recording a payment receipt
3. Allocating payment to outstanding bills
4. Generating aging report
"""
from datetime import date, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tally_mac_clone.database import db


def setup_test_data():
    """Set up test ledgers and initial data."""
    print("\n=== Setting Up Test Data ===")

    # Create tables
    db.create_tables()
    db.seed_default_data()

    # Create company
    companies = db.list_companies()
    if not companies:
        company = db.create_company("Demo Company", date(2026, 4, 1))
        print(f"Created company: {company.name}")
    else:
        company = companies[0]
        print(f"Using existing company: {company.name}")

    # Get groups
    debtors_group = db.get_group_by_name("Sundry Debtors")
    sales_group = db.get_group_by_name("Sales Accounts")

    # Create customer ledger
    customer = db.get_ledger_by_name("ABC Industries")
    if not customer:
        customer = db.create_ledger("ABC Industries", debtors_group.id, 0)
        print(f"Created ledger: {customer.name}")
    else:
        print(f"Using existing ledger: {customer.name}")

    # Create sales ledger
    sales = db.get_ledger_by_name("Product Sales")
    if not sales:
        sales = db.create_ledger("Product Sales", sales_group.id, 0)
        print(f"Created ledger: {sales.name}")

    return company, customer, sales


def create_sales_invoices(company, customer, sales):
    """Create multiple sales invoices with bills."""
    print("\n=== Creating Sales Invoices with Bills ===")

    sales_vtype = db.get_voucher_type_by_name("Sales")

    # Invoice 1: INV-001, 45 days old, overdue
    inv_date_1 = date.today() - timedelta(days=45)
    due_date_1 = inv_date_1 + timedelta(days=30)

    voucher_1 = db.create_voucher(
        voucher_type_id=sales_vtype.id,
        voucher_number="INV-001",
        date=inv_date_1,
        company_id=company.id,
        narration="Sales to ABC Industries - Order #1001",
        entries=[
            {"ledger_id": customer.id, "amount": 50000, "is_debit": True},
            {"ledger_id": sales.id, "amount": 50000, "is_debit": False},
        ]
    )

    bill_1 = db.create_bill(
        ledger_id=customer.id,
        bill_number="INV-001",
        bill_date=inv_date_1,
        due_date=due_date_1,
        amount=50000,
        bill_type="Receivable",
        voucher_id=voucher_1.id,
    )
    print(f"Created bill: {bill_1.bill_number}, Amount: ₹{bill_1.original_amount}, Due: {bill_1.due_date}")

    # Invoice 2: INV-002, 20 days old, current
    inv_date_2 = date.today() - timedelta(days=20)
    due_date_2 = inv_date_2 + timedelta(days=30)

    voucher_2 = db.create_voucher(
        voucher_type_id=sales_vtype.id,
        voucher_number="INV-002",
        date=inv_date_2,
        company_id=company.id,
        narration="Sales to ABC Industries - Order #1002",
        entries=[
            {"ledger_id": customer.id, "amount": 75000, "is_debit": True},
            {"ledger_id": sales.id, "amount": 75000, "is_debit": False},
        ]
    )

    bill_2 = db.create_bill(
        ledger_id=customer.id,
        bill_number="INV-002",
        bill_date=inv_date_2,
        due_date=due_date_2,
        amount=75000,
        bill_type="Receivable",
        voucher_id=voucher_2.id,
    )
    print(f"Created bill: {bill_2.bill_number}, Amount: ₹{bill_2.original_amount}, Due: {bill_2.due_date}")

    # Invoice 3: INV-003, 65 days old, overdue
    inv_date_3 = date.today() - timedelta(days=65)
    due_date_3 = inv_date_3 + timedelta(days=30)

    voucher_3 = db.create_voucher(
        voucher_type_id=sales_vtype.id,
        voucher_number="INV-003",
        date=inv_date_3,
        company_id=company.id,
        narration="Sales to ABC Industries - Order #1003",
        entries=[
            {"ledger_id": customer.id, "amount": 100000, "is_debit": True},
            {"ledger_id": sales.id, "amount": 100000, "is_debit": False},
        ]
    )

    bill_3 = db.create_bill(
        ledger_id=customer.id,
        bill_number="INV-003",
        bill_date=inv_date_3,
        due_date=due_date_3,
        amount=100000,
        bill_type="Receivable",
        voucher_id=voucher_3.id,
    )
    print(f"Created bill: {bill_3.bill_number}, Amount: ₹{bill_3.original_amount}, Due: {bill_3.due_date}")

    return voucher_1, voucher_2, voucher_3, bill_1, bill_2, bill_3


def show_outstanding_bills(customer):
    """Display outstanding bills for customer."""
    print("\n=== Outstanding Bills Report ===")

    bills = db.get_outstanding_bills(customer.id)

    print(f"\nCustomer: {customer.name}")
    print(f"Total Outstanding Bills: {len(bills)}")
    print(f"Total Pending Amount: ₹{sum(b['pending_amount'] for b in bills):,.2f}")
    print("\nBill Details:")
    print(f"{'Bill No':<12} {'Bill Date':<12} {'Due Date':<12} {'Pending':<12} {'Days Out':<10} {'Status':<10}")
    print("-" * 80)

    for bill in bills:
        print(f"{bill['bill_number']:<12} {bill['bill_date']:<12} {bill['due_date']:<12} "
              f"₹{bill['pending_amount']:>9,.2f} {bill['days_outstanding']:<10} {bill['status']:<10}")


def record_payment(company, customer, bill_1, bill_3):
    """Record payment and allocate to specific bills."""
    print("\n=== Recording Payment Receipt ===")

    receipt_vtype = db.get_voucher_type_by_name("Receipt")
    bank_group = db.get_group_by_name("Bank Accounts")

    # Get or create bank ledger
    bank = db.get_ledger_by_name("HDFC Bank")
    if not bank:
        bank = db.create_ledger("HDFC Bank", bank_group.id, 0)

    # Record receipt of ₹120,000
    payment_date = date.today()
    receipt_voucher = db.create_voucher(
        voucher_type_id=receipt_vtype.id,
        voucher_number="RCP-001",
        date=payment_date,
        company_id=company.id,
        narration="Payment received from ABC Industries",
        entries=[
            {"ledger_id": bank.id, "amount": 120000, "is_debit": True},
            {"ledger_id": customer.id, "amount": 120000, "is_debit": False},
        ]
    )
    print(f"Created receipt voucher: {receipt_voucher.voucher_number}, Amount: ₹120,000")

    # Allocate payment to bills
    # Full payment for INV-001 (₹50,000) and partial for INV-003 (₹70,000 of ₹100,000)
    print("\nAllocating payment to bills:")
    allocations = db.allocate_payment_to_bills(
        voucher_id=receipt_voucher.id,
        allocations=[
            {"bill_id": bill_1.id, "amount": 50000},  # Full payment for INV-001
            {"bill_id": bill_3.id, "amount": 70000},  # Partial payment for INV-003
        ]
    )

    for alloc in allocations:
        print(f"  - Allocated ₹{alloc.allocated_amount:,.2f} to Bill #{alloc.bill_id}")

    return receipt_voucher


def generate_aging_report():
    """Generate aging report for all debtors."""
    print("\n=== Aging Report - Sundry Debtors ===")

    report = db.get_aging_report(
        group_name="Sundry Debtors",
        aging_buckets=[
            (0, 30),      # Current (0-30 days)
            (31, 60),     # 31-60 days
            (61, 90),     # 61-90 days
            (91, 180),    # 91-180 days
            (181, 9999),  # 180+ days
        ]
    )

    print(f"\nAs of Date: {report['as_of_date']}")
    print(f"Total Outstanding: ₹{report['total_outstanding']:,.2f}")
    print(f"Total Bills: {report['total_bills']}")

    print("\n=== Aging Buckets ===")
    print(f"{'Range':<15} {'Count':<10} {'Amount':<15} {'Percentage':<12}")
    print("-" * 60)

    for bucket in report['buckets']:
        print(f"{bucket['range']:<15} {bucket['count']:<10} ₹{bucket['amount']:>12,.2f} {bucket['percentage']:>10.1f}%")

    print("\n=== Bill Details ===")
    print(f"{'Customer':<20} {'Bill No':<12} {'Bill Date':<12} {'Pending':<12} {'Days':<8} {'Bucket':<10}")
    print("-" * 85)

    for bill in report['bills']:
        print(f"{bill['ledger_name']:<20} {bill['bill_number']:<12} {bill['bill_date']:<12} "
              f"₹{bill['pending_amount']:>9,.2f} {bill['days_outstanding']:<8} {bill['bucket']:<10}")


def main():
    """Run complete bill-wise workflow demonstration."""
    print("=" * 80)
    print("BILL-WISE DETAILS SYSTEM - COMPLETE WORKFLOW DEMONSTRATION")
    print("=" * 80)

    # Step 1: Setup
    company, customer, sales = setup_test_data()

    # Step 2: Create sales invoices with bills
    v1, v2, v3, bill_1, bill_2, bill_3 = create_sales_invoices(company, customer, sales)

    # Step 3: Show outstanding bills before payment
    show_outstanding_bills(customer)

    # Step 4: Record payment and allocate to bills
    receipt_voucher = record_payment(company, customer, bill_1, bill_3)

    # Step 5: Show outstanding bills after payment
    print("\n=== After Payment Allocation ===")
    show_outstanding_bills(customer)

    # Step 6: Generate aging report
    generate_aging_report()

    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print("""
1. Created 3 sales invoices with bills:
   - INV-001: ₹50,000 (45 days old, overdue)
   - INV-002: ₹75,000 (20 days old, current)
   - INV-003: ₹100,000 (65 days old, overdue)

2. Total outstanding before payment: ₹225,000

3. Recorded payment receipt: ₹120,000
   - Allocated ₹50,000 to INV-001 (fully paid)
   - Allocated ₹70,000 to INV-003 (partial payment)

4. Remaining outstanding: ₹105,000
   - INV-002: ₹75,000 (unpaid)
   - INV-003: ₹30,000 (partially paid)

5. Aging analysis shows:
   - Current (0-30 days): INV-002
   - Overdue (61-90 days): INV-003 (remaining balance)
    """)
    print("=" * 80)


if __name__ == "__main__":
    main()
