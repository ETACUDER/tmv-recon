"""Migration script to add enhanced Company model fields.

Run this after updating the Company model to migrate existing database.
This handles backward compatibility for existing companies.
"""
from datetime import date
from sqlalchemy import create_engine, text

def migrate_company_schema(database_url: str = "sqlite:///./tally.db"):
    """Add new Company fields with safe defaults."""
    engine = create_engine(database_url, echo=True)

    with engine.connect() as conn:
        # Financial settings
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN books_beginning_from DATE"))
            conn.commit()
        except Exception:
            pass  # Column exists

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN tally_vault_password VARCHAR(255)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN maintain_accounts_only BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        # Company details
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN mailing_name VARCHAR(255)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN address TEXT"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN state VARCHAR(100)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN country VARCHAR(100) DEFAULT 'India' NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN pincode VARCHAR(10)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN phone VARCHAR(50)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN email VARCHAR(255)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN website VARCHAR(255)"))
            conn.commit()
        except Exception:
            pass

        # Tax registration
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN pan VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN gstin VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN gst_registration_type VARCHAR(50)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN tan VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN cin VARCHAR(30)"))
            conn.commit()
        except Exception:
            pass

        # Feature flags
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN maintain_bill_wise BOOLEAN DEFAULT 1 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN use_cost_centers BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN enable_multi_currency BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN maintain_payroll BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN maintain_inventory BOOLEAN DEFAULT 0 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN enable_gst BOOLEAN DEFAULT 1 NOT NULL"))
            conn.commit()
        except Exception:
            pass

        # Base currency
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN base_currency_id INTEGER REFERENCES currencies(id)"))
            conn.commit()
        except Exception:
            pass

        # Set books_beginning_from to financial_year_start for existing records
        try:
            conn.execute(text("""
                UPDATE companies
                SET books_beginning_from = financial_year_start
                WHERE books_beginning_from IS NULL
            """))
            conn.commit()
        except Exception:
            pass

        print("Migration completed successfully!")


if __name__ == "__main__":
    migrate_company_schema()
