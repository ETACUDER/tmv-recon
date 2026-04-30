#!/usr/bin/env python3
"""Migration script to add all 16 voucher types and type-specific fields."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text
from tally_mac_clone.database import Database

print("=" * 80)
print("MIGRATING VOUCHER TYPES TO SUPPORT ALL 16 TALLY VOUCHER TYPES")
print("=" * 80)

db = Database("sqlite:///./tally.db")

# Add new columns to vouchers table
print("\nAdding new columns to vouchers table...")
migrations = [
    # Inventory fields
    "ALTER TABLE vouchers ADD COLUMN affects_inventory BOOLEAN DEFAULT 0 NOT NULL",

    # Banking fields
    "ALTER TABLE vouchers ADD COLUMN affects_bank BOOLEAN DEFAULT 0 NOT NULL",
    "ALTER TABLE vouchers ADD COLUMN bank_ledger_id INTEGER REFERENCES ledgers(id)",

    # Transport fields
    "ALTER TABLE vouchers ADD COLUMN transport_mode VARCHAR(50)",
    "ALTER TABLE vouchers ADD COLUMN vehicle_number VARCHAR(50)",
    "ALTER TABLE vouchers ADD COLUMN carrier_name VARCHAR(255)",
    "ALTER TABLE vouchers ADD COLUMN dispatch_date DATE",

    # Due date
    "ALTER TABLE vouchers ADD COLUMN due_date DATE",

    # Reference fields
    "ALTER TABLE vouchers ADD COLUMN original_voucher_id INTEGER REFERENCES vouchers(id)",
    "ALTER TABLE vouchers ADD COLUMN reversal_date DATE",
    "ALTER TABLE vouchers ADD COLUMN adjustment_reason TEXT",

    # Stock transfer
    "ALTER TABLE vouchers ADD COLUMN from_godown VARCHAR(255)",
    "ALTER TABLE vouchers ADD COLUMN to_godown VARCHAR(255)",

    # Job work
    "ALTER TABLE vouchers ADD COLUMN is_job_work BOOLEAN DEFAULT 0 NOT NULL",
    "ALTER TABLE vouchers ADD COLUMN job_work_out BOOLEAN DEFAULT 1 NOT NULL",
]

with db.session() as session:
    for migration in migrations:
        try:
            session.execute(text(migration))
            print(f"  ✓ {migration[:60]}...")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print(f"  ○ Column already exists: {migration[:60]}...")
            else:
                print(f"  ✗ Error: {e}")

print("\nCreating voucher_type_configs table...")
with db.session() as session:
    try:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS voucher_type_configs (
                id INTEGER PRIMARY KEY,
                voucher_type_id INTEGER NOT NULL UNIQUE,
                method_of_voucher VARCHAR(50) DEFAULT 'Regular' NOT NULL,
                requires_inventory BOOLEAN DEFAULT 0 NOT NULL,
                requires_banking BOOLEAN DEFAULT 0 NOT NULL,
                numbering_series_prefix VARCHAR(20),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (voucher_type_id) REFERENCES voucher_types(id)
            )
        """))
        print("  ✓ Table created")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\nSeeding all 16 voucher types...")
db.seed_default_data()
print("  ✓ Voucher types seeded")

print("\n" + "=" * 80)
print("MIGRATION COMPLETE")
print("=" * 80)

# Verify
with db.session() as session:
    from sqlalchemy import select
    from tally_mac_clone.models import VoucherType

    count = session.execute(select(VoucherType)).scalars().all()
    print(f"\nTotal voucher types in database: {len(count)}")

    print("\nVoucher types:")
    for vtype in sorted(count, key=lambda x: x.name):
        print(f"  - {vtype.name}")
