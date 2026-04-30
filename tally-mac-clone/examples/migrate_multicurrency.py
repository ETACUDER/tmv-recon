"""Migrate database to support multi-currency."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "tally.db"

def migrate():
    """Add multi-currency columns to existing database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Migrating database for multi-currency support...")

    # Check if currencies table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='currencies'")
    currencies_exists = cursor.fetchone() is not None

    if currencies_exists:
        print("  Currencies table exists, checking for 'name' column...")
        cursor.execute("PRAGMA table_info(currencies)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'name' not in columns:
            print("  Adding 'name' column to currencies table...")
            cursor.execute("ALTER TABLE currencies ADD COLUMN name VARCHAR(100) DEFAULT 'Unknown'")
            conn.commit()
            print("  ✓ Added 'name' column")
        else:
            print("  ✓ 'name' column already exists")

        # Check for is_base column (renamed from is_base_currency)
        if 'is_base' not in columns and 'is_base_currency' in columns:
            print("  Renaming 'is_base_currency' to 'is_base'...")
            # SQLite doesn't support column rename directly, need to recreate table
            cursor.execute("""
                CREATE TABLE currencies_new (
                    id INTEGER PRIMARY KEY,
                    code VARCHAR(3) NOT NULL UNIQUE,
                    symbol VARCHAR(10) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    decimal_places INTEGER DEFAULT 2 NOT NULL,
                    is_base BOOLEAN DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            cursor.execute("""
                INSERT INTO currencies_new (id, code, symbol, name, decimal_places, is_base, created_at)
                SELECT id, code, symbol, COALESCE(name, 'Unknown'), decimal_places, is_base_currency, created_at
                FROM currencies
            """)
            cursor.execute("DROP TABLE currencies")
            cursor.execute("ALTER TABLE currencies_new RENAME TO currencies")
            conn.commit()
            print("  ✓ Renamed column to 'is_base'")
        elif 'is_base' in columns:
            print("  ✓ 'is_base' column already exists")

    # Check if vouchers table needs currency columns
    cursor.execute("PRAGMA table_info(vouchers)")
    voucher_columns = [row[1] for row in cursor.fetchall()]

    if 'currency_id' not in voucher_columns:
        print("  Adding currency columns to vouchers table...")
        cursor.execute("ALTER TABLE vouchers ADD COLUMN currency_id INTEGER")
        cursor.execute("ALTER TABLE vouchers ADD COLUMN exchange_rate REAL")
        cursor.execute("ALTER TABLE vouchers ADD COLUMN foreign_amount REAL")
        conn.commit()
        print("  ✓ Added currency_id, exchange_rate, foreign_amount columns")
    else:
        print("  ✓ Currency columns already exist in vouchers table")

    conn.close()
    print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
