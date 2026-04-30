"""Cost Center allocation demonstration."""
from datetime import date
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tally_mac_clone.database import db


def demo_cost_centers():
    """Demonstrate cost center functionality."""

    # Initialize database
    db.create_tables()
    db.seed_default_data()

    # Ensure company exists
    companies = db.list_companies()
    if not companies:
        company = db.create_company(
            name="Demo Company",
            financial_year_start=date(2026, 4, 1)
        )
    else:
        company = companies[0]

    print("\n=== Cost Center Implementation Demo ===\n")

    # 1. Create cost centers
    print("1. Creating cost centers...")

    # Department cost centers
    sales_dept = db.create_cost_center("Sales Department", category="Department")
    print(f"   Created: {sales_dept.name} (ID: {sales_dept.id})")

    marketing_dept = db.create_cost_center("Marketing Department", category="Department")
    print(f"   Created: {marketing_dept.name} (ID: {marketing_dept.id})")

    it_dept = db.create_cost_center("IT Department", category="Department")
    print(f"   Created: {it_dept.name} (ID: {it_dept.id})")

    # Project cost centers
    project_abc = db.create_cost_center("Project ABC", category="Project")
    print(f"   Created: {project_abc.name} (ID: {project_abc.id})")

    project_xyz = db.create_cost_center("Project XYZ", category="Project")
    print(f"   Created: {project_xyz.name} (ID: {project_xyz.id})")

    # Location cost centers
    bangalore = db.create_cost_center("Bangalore Office", category="Location")
    print(f"   Created: {bangalore.name} (ID: {bangalore.id})")

    mumbai = db.create_cost_center("Mumbai Office", category="Location")
    print(f"   Created: {mumbai.name} (ID: {mumbai.id})")

    # Hierarchical structure: Sub-department under Sales
    sales_team_a = db.create_cost_center(
        "Sales Team A",
        parent_id=sales_dept.id,
        category="Department"
    )
    print(f"   Created: {sales_team_a.name} (Parent: {sales_dept.name})")

    # 2. Create sample ledgers
    print("\n2. Creating sample ledgers...")

    # Get groups
    expense_group = db.get_group_by_name("Indirect Expenses")
    revenue_group = db.get_group_by_name("Sales Accounts")
    bank_group = db.get_group_by_name("Bank Accounts")

    # Create ledgers
    salary_ledger = db.create_ledger("Salary Expense", expense_group.id)
    print(f"   Created ledger: {salary_ledger.name}")

    marketing_ledger = db.create_ledger("Marketing Expense", expense_group.id)
    print(f"   Created ledger: {marketing_ledger.name}")

    sales_ledger = db.create_ledger("Product Sales", revenue_group.id)
    print(f"   Created ledger: {sales_ledger.name}")

    bank_ledger = db.create_ledger("HDFC Bank", bank_group.id, opening_balance=100000.0)
    print(f"   Created ledger: {bank_ledger.name}")

    # 3. Create voucher with entries
    print("\n3. Creating sample voucher...")

    payment_type = db.get_voucher_type_by_name("Payment")

    voucher = db.create_voucher(
        voucher_type_id=payment_type.id,
        voucher_number="PAY-001",
        date=date(2026, 4, 15),
        company_id=company.id,
        narration="Salary payment for April 2026",
        entries=[
            {"ledger_id": salary_ledger.id, "amount": 150000.0, "is_debit": True},
            {"ledger_id": bank_ledger.id, "amount": 150000.0, "is_debit": False},
        ]
    )
    print(f"   Created voucher: {voucher.voucher_number}")
    print(f"   Entry 1: Salary Expense Dr 150000")
    print(f"   Entry 2: HDFC Bank Cr 150000")

    # 4. Allocate entry to multiple cost centers
    print("\n4. Allocating salary expense to departments...")

    # Get the salary debit entry by querying fresh
    voucher_fresh = db.get_voucher(voucher.id)
    salary_entry = [e for e in voucher_fresh.entries if e.ledger_id == salary_ledger.id][0]

    allocations = db.allocate_to_cost_centers(
        entry_id=salary_entry.id,
        allocations=[
            {
                "cost_center_id": sales_dept.id,
                "amount": 75000.0,
                "percentage": 50.0
            },
            {
                "cost_center_id": marketing_dept.id,
                "amount": 45000.0,
                "percentage": 30.0
            },
            {
                "cost_center_id": it_dept.id,
                "amount": 30000.0,
                "percentage": 20.0
            }
        ]
    )

    print(f"   Allocated to {len(allocations)} cost centers:")
    for alloc in allocations:
        print(f"   - {alloc.cost_center.name}: {alloc.amount} ({alloc.percentage}%)")

    # 5. Create more vouchers for demonstration
    print("\n5. Creating additional vouchers...")

    # Marketing expense
    marketing_voucher = db.create_voucher(
        voucher_type_id=payment_type.id,
        voucher_number="PAY-002",
        date=date(2026, 4, 20),
        company_id=company.id,
        narration="Marketing campaign expense",
        entries=[
            {"ledger_id": marketing_ledger.id, "amount": 50000.0, "is_debit": True},
            {"ledger_id": bank_ledger.id, "amount": 50000.0, "is_debit": False},
        ]
    )

    marketing_voucher_fresh = db.get_voucher(marketing_voucher.id)
    marketing_entry = [e for e in marketing_voucher_fresh.entries if e.ledger_id == marketing_ledger.id][0]

    # Allocate to projects
    db.allocate_to_cost_centers(
        entry_id=marketing_entry.id,
        allocations=[
            {
                "cost_center_id": project_abc.id,
                "amount": 30000.0,
                "percentage": 60.0
            },
            {
                "cost_center_id": project_xyz.id,
                "amount": 20000.0,
                "percentage": 40.0
            }
        ]
    )
    print(f"   Created voucher: {marketing_voucher.voucher_number}")
    print(f"   Allocated to Project ABC (60%) and Project XYZ (40%)")

    # 6. Generate cost center reports
    print("\n6. Cost Center Reports:")
    print("   " + "="*60)

    # Sales department report
    sales_report = db.get_cost_center_report(
        cost_center_id=sales_dept.id,
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30)
    )

    print(f"\n   Cost Center: {sales_report['cost_center_name']}")
    print(f"   Category: {sales_report['category']}")
    print(f"   Period: {sales_report['from_date']} to {sales_report['to_date']}")
    print(f"   Total Debit: {sales_report['total_debit']:.2f}")
    print(f"   Total Credit: {sales_report['total_credit']:.2f}")
    print(f"   Net Amount: {sales_report['net_amount']:.2f}")
    print(f"   Entries:")
    for entry in sales_report['entries']:
        side = "Dr" if entry['is_debit'] else "Cr"
        print(f"     {entry['date']} | {entry['voucher_number']} | {entry['ledger_name']} {side} {entry['amount']:.2f}")

    # Project ABC report
    project_report = db.get_cost_center_report(
        cost_center_id=project_abc.id,
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30)
    )

    print(f"\n   Cost Center: {project_report['cost_center_name']}")
    print(f"   Category: {project_report['category']}")
    print(f"   Total Debit: {project_report['total_debit']:.2f}")
    print(f"   Total Credit: {project_report['total_credit']:.2f}")
    print(f"   Net Amount: {project_report['net_amount']:.2f}")

    # 7. Show hierarchical structure
    print("\n7. Cost Center Hierarchy:")
    print("   " + "="*60)

    all_centers = db.list_cost_centers(active_only=True)

    def print_tree(parent_id=None, indent=0):
        for cc in all_centers:
            if cc.parent_id == parent_id:
                prefix = "   " * indent + ("└─ " if indent > 0 else "")
                print(f"   {prefix}{cc.name} ({cc.category})")
                print_tree(cc.id, indent + 1)

    print_tree()

    print("\n=== Demo Complete ===\n")

    # Return summary
    return {
        "cost_centers_created": len(all_centers),
        "vouchers_created": 2,
        "allocations_created": 5,
        "reports_generated": 2,
    }


if __name__ == "__main__":
    try:
        summary = demo_cost_centers()
        print(f"Summary:")
        print(f"  - Cost Centers: {summary['cost_centers_created']}")
        print(f"  - Vouchers: {summary['vouchers_created']}")
        print(f"  - Allocations: {summary['allocations_created']}")
        print(f"  - Reports: {summary['reports_generated']}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
