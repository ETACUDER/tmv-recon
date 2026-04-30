"""Database session management and CRUD operations."""
from datetime import date, datetime
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Base, Company, Group, Ledger, VoucherType, Voucher, LedgerEntry,
    CostCenter, CostCenterAllocation, BankReconciliation, Cheque, BankStatement,
    Currency, ExchangeRate
)


class Database:
    def __init__(self, database_url: str = "sqlite:///./tally.db"):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Company CRUD
    def create_company(self, name: str, financial_year_start: date) -> Company:
        with self.session() as session:
            company = Company(name=name, financial_year_start=financial_year_start)
            session.add(company)
            session.flush()
            session.refresh(company)
            return company

    def get_company(self, company_id: int) -> Optional[Company]:
        with self.session() as session:
            return session.get(Company, company_id)

    def list_companies(self) -> list[Company]:
        with self.session() as session:
            return list(session.execute(select(Company)).scalars().all())

    # Group CRUD
    def create_group(
        self,
        name: str,
        parent_id: Optional[int] = None,
        is_revenue: bool = False,
        is_expense: bool = False,
        is_asset: bool = False,
        is_liability: bool = False,
    ) -> Group:
        with self.session() as session:
            group = Group(
                name=name,
                parent_id=parent_id,
                is_revenue=is_revenue,
                is_expense=is_expense,
                is_asset=is_asset,
                is_liability=is_liability,
            )
            session.add(group)
            session.flush()
            session.refresh(group)
            return group

    def get_group(self, group_id: int) -> Optional[Group]:
        with self.session() as session:
            return session.get(Group, group_id)

    def get_group_by_name(self, name: str) -> Optional[Group]:
        with self.session() as session:
            result = session.execute(select(Group).where(Group.name == name))
            return result.scalar_one_or_none()

    def list_groups(self) -> list[Group]:
        with self.session() as session:
            return list(session.execute(select(Group)).scalars().all())

    # Ledger CRUD
    def create_ledger(
        self, name: str, group_id: int, opening_balance: float = 0.0
    ) -> Ledger:
        with self.session() as session:
            ledger = Ledger(
                name=name, group_id=group_id, opening_balance=opening_balance
            )
            session.add(ledger)
            session.flush()
            session.refresh(ledger)
            return ledger

    def get_ledger(self, ledger_id: int) -> Optional[Ledger]:
        with self.session() as session:
            return session.get(Ledger, ledger_id)

    def get_ledger_by_name(self, name: str) -> Optional[Ledger]:
        with self.session() as session:
            result = session.execute(select(Ledger).where(Ledger.name == name))
            return result.scalar_one_or_none()

    def list_ledgers(self) -> list[Ledger]:
        with self.session() as session:
            return list(session.execute(select(Ledger)).scalars().all())

    # VoucherType CRUD
    def create_voucher_type(self, name: str) -> VoucherType:
        with self.session() as session:
            vtype = VoucherType(name=name)
            session.add(vtype)
            session.flush()
            session.refresh(vtype)
            return vtype

    def get_voucher_type_by_name(self, name: str) -> Optional[VoucherType]:
        with self.session() as session:
            result = session.execute(
                select(VoucherType).where(VoucherType.name == name)
            )
            return result.scalar_one_or_none()

    def list_voucher_types(self) -> list[VoucherType]:
        with self.session() as session:
            return list(session.execute(select(VoucherType)).scalars().all())

    # Voucher CRUD
    def create_voucher(
        self,
        voucher_type_id: int,
        voucher_number: str,
        date: date,
        company_id: int,
        narration: str = "",
        entries: list[dict] = None,
    ) -> Voucher:
        """Create voucher with ledger entries.

        entries format: [{"ledger_id": int, "amount": float, "is_debit": bool}, ...]
        """
        with self.session() as session:
            voucher = Voucher(
                voucher_type_id=voucher_type_id,
                voucher_number=voucher_number,
                date=date,
                company_id=company_id,
                narration=narration,
            )
            session.add(voucher)
            session.flush()

            if entries:
                for entry_data in entries:
                    entry = LedgerEntry(
                        voucher_id=voucher.id,
                        ledger_id=entry_data["ledger_id"],
                        amount=entry_data["amount"],
                        is_debit=entry_data["is_debit"],
                    )
                    session.add(entry)

            session.flush()
            session.refresh(voucher)
            return voucher

    def get_voucher(self, voucher_id: int) -> Optional[Voucher]:
        with self.session() as session:
            from sqlalchemy.orm import joinedload
            voucher = session.execute(
                select(Voucher)
                .options(joinedload(Voucher.entries))
                .where(Voucher.id == voucher_id)
            ).unique().scalar_one_or_none()
            return voucher

    def list_vouchers(
        self, company_id: Optional[int] = None, limit: int = 100
    ) -> list[Voucher]:
        with self.session() as session:
            query = select(Voucher).order_by(Voucher.date.desc(), Voucher.id.desc())
            if company_id:
                query = query.where(Voucher.company_id == company_id)
            query = query.limit(limit)
            return list(session.execute(query).scalars().all())

    # Trial Balance
    def get_trial_balance(self, company_id: int) -> list[dict]:
        """Calculate trial balance for a company.

        Returns: [{"ledger_id": int, "ledger_name": str, "debit": float, "credit": float}, ...]
        """
        with self.session() as session:
            # Get all ledgers with their opening balances
            ledgers = session.execute(
                select(Ledger).order_by(Ledger.name)
            ).scalars().all()

            result = []
            for ledger in ledgers:
                # Calculate balance from entries
                entries = session.execute(
                    select(LedgerEntry)
                    .join(Voucher)
                    .where(
                        LedgerEntry.ledger_id == ledger.id,
                        Voucher.company_id == company_id,
                    )
                ).scalars().all()

                debit_total = sum(e.amount for e in entries if e.is_debit)
                credit_total = sum(e.amount for e in entries if not e.is_debit)

                # Add opening balance
                balance = ledger.opening_balance + debit_total - credit_total

                result.append({
                    "ledger_id": ledger.id,
                    "ledger_name": ledger.name,
                    "debit": max(0, balance),
                    "credit": max(0, -balance),
                })

            return result

    # Cost Center CRUD
    def create_cost_center(
        self,
        name: str,
        parent_id: Optional[int] = None,
        category: str = "Department",
    ) -> CostCenter:
        with self.session() as session:
            cost_center = CostCenter(
                name=name,
                parent_id=parent_id,
                category=category,
                is_active=True,
            )
            session.add(cost_center)
            session.flush()
            session.refresh(cost_center)
            return cost_center

    def get_cost_center(self, cost_center_id: int) -> Optional[CostCenter]:
        with self.session() as session:
            return session.get(CostCenter, cost_center_id)

    def get_cost_center_by_name(self, name: str) -> Optional[CostCenter]:
        with self.session() as session:
            result = session.execute(select(CostCenter).where(CostCenter.name == name))
            return result.scalar_one_or_none()

    def list_cost_centers(self, active_only: bool = True) -> list[CostCenter]:
        with self.session() as session:
            query = select(CostCenter)
            if active_only:
                query = query.where(CostCenter.is_active == True)
            return list(session.execute(query).scalars().all())

    def allocate_to_cost_centers(
        self, entry_id: int, allocations: list[dict]
    ) -> list[CostCenterAllocation]:
        """Allocate entry amount to cost centers.

        allocations format: [{"cost_center_id": int, "amount": float, "percentage": float}, ...]
        Validates that allocations sum to entry amount.
        """
        with self.session() as session:
            from sqlalchemy.orm import joinedload

            entry = session.get(LedgerEntry, entry_id)
            if not entry:
                raise ValueError(f"Entry {entry_id} not found")

            # Validate total allocation
            total_allocated = sum(alloc["amount"] for alloc in allocations)
            if abs(total_allocated - abs(entry.amount)) > 0.01:
                raise ValueError(
                    f"Allocations ({total_allocated}) must sum to entry amount ({abs(entry.amount)})"
                )

            # Create allocations
            created_allocations = []
            for alloc_data in allocations:
                allocation = CostCenterAllocation(
                    ledger_entry_id=entry_id,
                    cost_center_id=alloc_data["cost_center_id"],
                    amount=alloc_data["amount"],
                    percentage=alloc_data.get("percentage"),
                )
                session.add(allocation)
                created_allocations.append(allocation)

            session.flush()

            # Reload with eager loading
            allocation_ids = [a.id for a in created_allocations]
            created_allocations = list(session.execute(
                select(CostCenterAllocation)
                .options(joinedload(CostCenterAllocation.cost_center))
                .where(CostCenterAllocation.id.in_(allocation_ids))
            ).scalars().unique().all())

            return created_allocations

    def get_cost_center_report(
        self, cost_center_id: int, from_date: date, to_date: date
    ) -> dict:
        """Generate cost center report for date range.

        Returns summary of allocations with ledger details.
        """
        with self.session() as session:
            cost_center = session.get(CostCenter, cost_center_id)
            if not cost_center:
                raise ValueError(f"Cost center {cost_center_id} not found")

            # Get allocations in date range
            allocations = session.execute(
                select(CostCenterAllocation)
                .join(LedgerEntry)
                .join(Voucher)
                .where(
                    CostCenterAllocation.cost_center_id == cost_center_id,
                    Voucher.date >= from_date,
                    Voucher.date <= to_date,
                )
                .order_by(Voucher.date.desc())
            ).scalars().all()

            # Build report
            entries = []
            total_debit = 0.0
            total_credit = 0.0

            for alloc in allocations:
                entry = alloc.ledger_entry
                voucher = entry.voucher

                entry_data = {
                    "date": voucher.date.isoformat(),
                    "voucher_number": voucher.voucher_number,
                    "voucher_type": voucher.voucher_type.name,
                    "ledger_name": entry.ledger.name,
                    "amount": alloc.amount,
                    "is_debit": entry.is_debit,
                    "percentage": alloc.percentage,
                }
                entries.append(entry_data)

                if entry.is_debit:
                    total_debit += alloc.amount
                else:
                    total_credit += alloc.amount

            return {
                "cost_center_id": cost_center_id,
                "cost_center_name": cost_center.name,
                "category": cost_center.category,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "total_debit": total_debit,
                "total_credit": total_credit,
                "net_amount": total_debit - total_credit,
                "entries": entries,
            }

    # Currency CRUD
    def create_currency(
        self,
        code: str,
        symbol: str,
        name: str,
        decimal_places: int = 2,
        is_base: bool = False,
    ) -> Currency:
        with self.session() as session:
            currency = Currency(
                code=code,
                symbol=symbol,
                name=name,
                decimal_places=decimal_places,
                is_base=is_base,
            )
            session.add(currency)
            session.flush()
            session.refresh(currency)
            return currency

    def get_currency(self, currency_id: int) -> Optional[Currency]:
        with self.session() as session:
            return session.get(Currency, currency_id)

    def get_currency_by_code(self, code: str) -> Optional[Currency]:
        with self.session() as session:
            result = session.execute(select(Currency).where(Currency.code == code))
            return result.scalar_one_or_none()

    def list_currencies(self) -> list[Currency]:
        with self.session() as session:
            return list(session.execute(select(Currency).order_by(Currency.code)).scalars().all())

    # Exchange Rate CRUD
    def create_exchange_rate(
        self, currency_id: int, date: date, rate: float
    ) -> ExchangeRate:
        with self.session() as session:
            exchange_rate = ExchangeRate(
                currency_id=currency_id,
                date=date,
                rate=rate,
            )
            session.add(exchange_rate)
            session.flush()
            session.refresh(exchange_rate)
            return exchange_rate

    def get_exchange_rate(self, currency_code: str, date: date) -> Optional[float]:
        """Get exchange rate for currency on specific date.

        Returns the rate for the exact date or nearest previous date.
        """
        with self.session() as session:
            currency = self.get_currency_by_code(currency_code)
            if not currency:
                return None

            result = session.execute(
                select(ExchangeRate)
                .where(
                    ExchangeRate.currency_id == currency.id,
                    ExchangeRate.date <= date,
                )
                .order_by(ExchangeRate.date.desc())
                .limit(1)
            )
            exchange_rate = result.scalar_one_or_none()
            return exchange_rate.rate if exchange_rate else None

    def list_exchange_rates(self, currency_id: int) -> list[ExchangeRate]:
        with self.session() as session:
            return list(
                session.execute(
                    select(ExchangeRate)
                    .where(ExchangeRate.currency_id == currency_id)
                    .order_by(ExchangeRate.date.desc())
                ).scalars().all()
            )

    # Seed data
    def seed_default_data(self):
        """Create default groups and voucher types."""
        # Default voucher types
        voucher_types = ["Sales", "Purchase", "Receipt", "Payment", "Journal", "Contra"]
        for vtype_name in voucher_types:
            if not self.get_voucher_type_by_name(vtype_name):
                self.create_voucher_type(vtype_name)

        # Default groups (Tally standard)
        default_groups = [
            {"name": "Sundry Debtors", "is_asset": True},
            {"name": "Sundry Creditors", "is_liability": True},
            {"name": "Bank Accounts", "is_asset": True},
            {"name": "Cash-in-Hand", "is_asset": True},
            {"name": "Sales Accounts", "is_revenue": True},
            {"name": "Purchase Accounts", "is_expense": True},
            {"name": "Indirect Expenses", "is_expense": True},
            {"name": "Indirect Incomes", "is_revenue": True},
            {"name": "Current Assets", "is_asset": True},
            {"name": "Current Liabilities", "is_liability": True},
            {"name": "Duties & Taxes", "is_liability": True},
        ]

        for group_data in default_groups:
            if not self.get_group_by_name(group_data["name"]):
                self.create_group(**group_data)


# Global database instance
db = Database()
