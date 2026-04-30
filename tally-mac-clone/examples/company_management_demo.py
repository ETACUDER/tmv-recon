"""Demo: Enhanced Company model with Tally-compatible fields.

Shows creating companies with full details, updating settings, and retrieving configuration.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import date
from tally_mac_clone.database import Database

def demo_company_management():
    """Demonstrate complete company management features."""
    db = Database("sqlite:///./tally_demo.db")
    db.create_tables()
    db.seed_default_data()

    # Create INR currency as base
    inr = db.create_currency(
        code="INR",
        symbol="₹",
        name="Indian Rupee",
        decimal_places=2,
        is_base=True
    )

    # Create company with complete details
    company = db.create_company(
        name="Acme Corporation Pvt Ltd",
        financial_year_start=date(2026, 4, 1),
        books_beginning_from=date(2025, 4, 1),

        # Company details
        mailing_name="Acme Corp",
        address="123 Business Park, MG Road\nBangalore, Karnataka",
        state="Karnataka",
        country="India",
        pincode="560001",
        phone="+91-80-12345678",
        email="accounts@acmecorp.com",
        website="https://acmecorp.com",

        # Tax registration
        pan="AAACA1234A",
        gstin="29AAACA1234A1Z5",
        gst_registration_type="Regular",
        tan="BLRA12345A",
        cin="U72900KA2020PTC123456",

        # Feature flags
        maintain_bill_wise=True,
        use_cost_centers=True,
        enable_multi_currency=True,
        maintain_payroll=False,
        maintain_inventory=True,
        enable_gst=True,

        # Base currency
        base_currency_id=inr.id
    )

    print(f"Created company: {company.name}")
    print(f"  GSTIN: {company.gstin}")
    print(f"  State: {company.state}")
    print(f"  Features enabled: Bill-wise={company.maintain_bill_wise}, "
          f"Cost Centers={company.use_cost_centers}, "
          f"Multi-currency={company.enable_multi_currency}")

    # Get company settings
    settings = db.get_company_settings(company.id)
    print("\nCompany Settings:")
    for key, value in settings.items():
        if value is not None and key not in ['created_at']:
            print(f"  {key}: {value}")

    # Update company details
    updated = db.update_company(
        company.id,
        phone="+91-80-98765432",
        email="finance@acmecorp.com",
        use_cost_centers=True,
        maintain_payroll=True
    )

    print(f"\nUpdated company phone: {updated.phone}")
    print(f"Payroll enabled: {updated.maintain_payroll}")

    # Create second company with minimal details
    company2 = db.create_company(
        name="Small Business",
        financial_year_start=date(2026, 4, 1),
        maintain_accounts_only=True,
        enable_gst=False,
        maintain_bill_wise=False
    )

    print(f"\nCreated minimal company: {company2.name}")
    print(f"  Accounts only: {company2.maintain_accounts_only}")
    print(f"  GST enabled: {company2.enable_gst}")

    # List all companies
    all_companies = db.list_companies()
    print(f"\nTotal companies: {len(all_companies)}")
    for c in all_companies:
        print(f"  - {c.name} (FY: {c.financial_year_start})")


if __name__ == "__main__":
    demo_company_management()
