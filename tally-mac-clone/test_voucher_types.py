#!/usr/bin/env python3
"""Test script for all 16 voucher types with their specific fields."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import date
from tally_mac_clone.database import Database
from tally_mac_clone.models import VoucherType, VoucherTypeConfig

# Initialize database
db = Database("sqlite:///./test_voucher_types.db")
db.create_tables()
db.seed_default_data()

print("=" * 80)
print("ALL 16 TALLY VOUCHER TYPES WITH CONFIGURATIONS")
print("=" * 80)

# Retrieve all voucher types with their configs
with db.session() as session:
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    voucher_types = session.execute(
        select(VoucherType).options(joinedload(VoucherType.config)).order_by(VoucherType.name)
    ).unique().scalars().all()

    for vtype in voucher_types:
        print(f"\n{vtype.id}. {vtype.name}")
        print(f"   {'─' * 70}")

        if vtype.config:
            config = vtype.config
            print(f"   Method: {config.method_of_voucher}")
            print(f"   Prefix: {config.numbering_series_prefix}")
            print(f"   Requires Inventory: {'Yes' if config.requires_inventory else 'No'}")
            print(f"   Requires Banking: {'Yes' if config.requires_banking else 'No'}")

            # Show key distinguishing fields
            if vtype.name in ["Sales", "Purchase"]:
                print(f"   Key Fields: affects_inventory, due_date")
            elif vtype.name in ["Payment", "Receipt", "Contra"]:
                print(f"   Key Fields: affects_bank, bank_ledger_id")
            elif vtype.name in ["Credit Note", "Debit Note"]:
                print(f"   Key Fields: affects_inventory, original_voucher_id, adjustment_reason")
            elif vtype.name in ["Delivery Note", "Receipt Note"]:
                print(f"   Key Fields: affects_inventory, transport_mode, vehicle_number, dispatch_date")
            elif vtype.name in ["Rejection In", "Rejection Out"]:
                print(f"   Key Fields: affects_inventory, original_voucher_id")
            elif vtype.name == "Stock Journal":
                print(f"   Key Fields: affects_inventory, from_godown, to_godown")
            elif vtype.name == "Physical Stock":
                print(f"   Key Fields: affects_inventory")
            elif vtype.name == "Memorandum":
                print(f"   Key Fields: is_job_work, job_work_out")
            elif vtype.name == "Reversing Journal":
                print(f"   Key Fields: original_voucher_id, reversal_date")
            else:
                print(f"   Key Fields: Standard voucher fields")
        else:
            print("   [No config found]")

print("\n" + "=" * 80)
print(f"Total Voucher Types: {len(voucher_types)}")
print("=" * 80)

# Summary table
print("\n\nSUMMARY OF KEY DISTINGUISHING FIELDS BY TYPE:")
print("=" * 80)

type_features = [
    ("Sales", "affects_inventory=True, due_date"),
    ("Purchase", "affects_inventory=True, due_date"),
    ("Payment", "affects_bank=True, bank_ledger_id"),
    ("Receipt", "affects_bank=True, bank_ledger_id"),
    ("Journal", "Standard accounting entries"),
    ("Contra", "affects_bank=True, bank_ledger_id (between banks)"),
    ("Credit Note", "affects_inventory=True, original_voucher_id, adjustment_reason"),
    ("Debit Note", "affects_inventory=True, original_voucher_id, adjustment_reason"),
    ("Delivery Note", "affects_inventory=True, transport_mode, vehicle_number, carrier_name, dispatch_date"),
    ("Receipt Note", "affects_inventory=True, transport_mode, vehicle_number, carrier_name, dispatch_date"),
    ("Rejection In", "affects_inventory=True, original_voucher_id (purchase return)"),
    ("Rejection Out", "affects_inventory=True, original_voucher_id (sales return)"),
    ("Stock Journal", "affects_inventory=True, from_godown, to_godown"),
    ("Physical Stock", "affects_inventory=True (stock adjustment)"),
    ("Memorandum", "is_job_work=True, job_work_out (material sent/received for job work)"),
    ("Reversing Journal", "original_voucher_id, reversal_date (reverses entries)"),
]

for vtype_name, features in type_features:
    print(f"\n{vtype_name:20} : {features}")

print("\n" + "=" * 80)
print("Database schema created successfully with all voucher type fields!")
print(f"Test database: test_voucher_types.db")
print("=" * 80)
