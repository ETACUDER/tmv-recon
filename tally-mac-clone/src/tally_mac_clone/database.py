"""Database session management and CRUD operations."""
from datetime import date, datetime
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Base, Company, Group, Ledger, VoucherType, VoucherTypeConfig, Voucher, LedgerEntry,
    CostCenter, CostCenterAllocation, BankReconciliation, Cheque, BankStatement,
    Currency, ExchangeRate, Bill, BillAllocation
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
    def create_company(
        self,
        name: str,
        financial_year_start: date,
        books_beginning_from: Optional[date] = None,
        tally_vault_password: Optional[str] = None,
        maintain_accounts_only: bool = False,
        mailing_name: Optional[str] = None,
        address: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "India",
        pincode: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        pan: Optional[str] = None,
        gstin: Optional[str] = None,
        gst_registration_type: Optional[str] = None,
        tan: Optional[str] = None,
        cin: Optional[str] = None,
        maintain_bill_wise: bool = True,
        use_cost_centers: bool = False,
        enable_multi_currency: bool = False,
        maintain_payroll: bool = False,
        maintain_inventory: bool = False,
        enable_gst: bool = True,
        base_currency_id: Optional[int] = None,
    ) -> Company:
        with self.session() as session:
            company = Company(
                name=name,
                financial_year_start=financial_year_start,
                books_beginning_from=books_beginning_from or financial_year_start,
                tally_vault_password=tally_vault_password,
                maintain_accounts_only=maintain_accounts_only,
                mailing_name=mailing_name,
                address=address,
                state=state,
                country=country,
                pincode=pincode,
                phone=phone,
                email=email,
                website=website,
                pan=pan,
                gstin=gstin,
                gst_registration_type=gst_registration_type,
                tan=tan,
                cin=cin,
                maintain_bill_wise=maintain_bill_wise,
                use_cost_centers=use_cost_centers,
                enable_multi_currency=enable_multi_currency,
                maintain_payroll=maintain_payroll,
                maintain_inventory=maintain_inventory,
                enable_gst=enable_gst,
                base_currency_id=base_currency_id,
            )
            session.add(company)
            session.flush()
            session.refresh(company)
            return company

    def get_company(self, company_id: int) -> Optional[Company]:
        with self.session() as session:
            from sqlalchemy.orm import joinedload
            company = session.execute(
                select(Company)
                .options(joinedload(Company.base_currency))
                .where(Company.id == company_id)
            ).unique().scalar_one_or_none()
            return company

    def list_companies(self) -> list[Company]:
        with self.session() as session:
            return list(session.execute(select(Company)).scalars().all())

    def update_company(self, company_id: int, **kwargs) -> Optional[Company]:
        """Update company details with provided kwargs."""
        with self.session() as session:
            company = session.get(Company, company_id)
            if not company:
                return None

            for key, value in kwargs.items():
                if hasattr(company, key):
                    setattr(company, key, value)

            session.flush()
            session.refresh(company)
            return company

    def get_company_settings(self, company_id: int) -> Optional[dict]:
        """Get company configuration as dict."""
        with self.session() as session:
            from sqlalchemy.orm import joinedload
            company = session.execute(
                select(Company)
                .options(joinedload(Company.base_currency))
                .where(Company.id == company_id)
            ).unique().scalar_one_or_none()

            if not company:
                return None

            return {
                "id": company.id,
                "name": company.name,
                "financial_year_start": company.financial_year_start.isoformat(),
                "books_beginning_from": company.books_beginning_from.isoformat() if company.books_beginning_from else None,
                "maintain_accounts_only": company.maintain_accounts_only,
                "mailing_name": company.mailing_name,
                "address": company.address,
                "state": company.state,
                "country": company.country,
                "pincode": company.pincode,
                "phone": company.phone,
                "email": company.email,
                "website": company.website,
                "pan": company.pan,
                "gstin": company.gstin,
                "gst_registration_type": company.gst_registration_type,
                "tan": company.tan,
                "cin": company.cin,
                "maintain_bill_wise": company.maintain_bill_wise,
                "use_cost_centers": company.use_cost_centers,
                "enable_multi_currency": company.enable_multi_currency,
                "maintain_payroll": company.maintain_payroll,
                "maintain_inventory": company.maintain_inventory,
                "enable_gst": company.enable_gst,
                "base_currency_id": company.base_currency_id,
                "base_currency": {
                    "id": company.base_currency.id,
                    "code": company.base_currency.code,
                    "symbol": company.base_currency.symbol,
                    "name": company.base_currency.name,
                } if company.base_currency else None,
            }

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
        # All 16 Tally voucher types with their configurations
        voucher_type_configs = [
            {"name": "Sales", "method": "Invoice", "inventory": True, "banking": False, "prefix": "S"},
            {"name": "Purchase", "method": "Invoice", "inventory": True, "banking": False, "prefix": "P"},
            {"name": "Payment", "method": "Banking", "inventory": False, "banking": True, "prefix": "PAY"},
            {"name": "Receipt", "method": "Banking", "inventory": False, "banking": True, "prefix": "RCP"},
            {"name": "Journal", "method": "Regular", "inventory": False, "banking": False, "prefix": "JV"},
            {"name": "Contra", "method": "Banking", "inventory": False, "banking": True, "prefix": "CON"},
            {"name": "Credit Note", "method": "Invoice", "inventory": True, "banking": False, "prefix": "CN"},
            {"name": "Debit Note", "method": "Invoice", "inventory": True, "banking": False, "prefix": "DN"},
            {"name": "Delivery Note", "method": "Inventory", "inventory": True, "banking": False, "prefix": "DEL"},
            {"name": "Receipt Note", "method": "Inventory", "inventory": True, "banking": False, "prefix": "RN"},
            {"name": "Rejection In", "method": "Inventory", "inventory": True, "banking": False, "prefix": "REJ-IN"},
            {"name": "Rejection Out", "method": "Inventory", "inventory": True, "banking": False, "prefix": "REJ-OUT"},
            {"name": "Stock Journal", "method": "Inventory", "inventory": True, "banking": False, "prefix": "STK"},
            {"name": "Physical Stock", "method": "Inventory", "inventory": True, "banking": False, "prefix": "PS"},
            {"name": "Memorandum", "method": "Inventory", "inventory": True, "banking": False, "prefix": "MEM"},
            {"name": "Reversing Journal", "method": "Regular", "inventory": False, "banking": False, "prefix": "RJ"},
        ]

        for vtype_config in voucher_type_configs:
            vtype = self.get_voucher_type_by_name(vtype_config["name"])
            if not vtype:
                vtype = self.create_voucher_type(vtype_config["name"])

            # Create config if not exists
            with self.session() as session:
                existing_config = session.execute(
                    select(VoucherTypeConfig).where(VoucherTypeConfig.voucher_type_id == vtype.id)
                ).scalar_one_or_none()

                if not existing_config:
                    config = VoucherTypeConfig(
                        voucher_type_id=vtype.id,
                        method_of_voucher=vtype_config["method"],
                        requires_inventory=vtype_config["inventory"],
                        requires_banking=vtype_config["banking"],
                        numbering_series_prefix=vtype_config["prefix"],
                    )
                    session.add(config)

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

    # Bill CRUD
    def create_bill(
        self,
        ledger_id: int,
        bill_number: str,
        bill_date: date,
        due_date: date,
        amount: float,
        bill_type: str,
        voucher_id: int,
    ) -> Bill:
        """Create bill for receivable/payable tracking.

        Args:
            ledger_id: Party ledger (debtor/creditor)
            bill_number: Invoice/bill reference number
            bill_date: Bill date
            due_date: Payment due date
            amount: Bill amount
            bill_type: 'Receivable' or 'Payable'
            voucher_id: Source voucher (Sales/Purchase)
        """
        with self.session() as session:
            bill = Bill(
                ledger_id=ledger_id,
                bill_number=bill_number,
                bill_date=bill_date,
                due_date=due_date,
                original_amount=amount,
                pending_amount=amount,
                bill_type=bill_type,
                created_from_voucher_id=voucher_id,
            )
            session.add(bill)
            session.flush()
            session.refresh(bill)
            return bill

    def allocate_payment_to_bills(
        self, voucher_id: int, allocations: list[dict]
    ) -> list[BillAllocation]:
        """Allocate payment/receipt to outstanding bills.

        Args:
            voucher_id: Payment/Receipt voucher
            allocations: [{"bill_id": int, "amount": float}, ...]

        Returns:
            List of created allocations
        """
        with self.session() as session:
            voucher = session.get(Voucher, voucher_id)
            if not voucher:
                raise ValueError(f"Voucher {voucher_id} not found")

            created_allocations = []
            for alloc_data in allocations:
                bill = session.get(Bill, alloc_data["bill_id"])
                if not bill:
                    raise ValueError(f"Bill {alloc_data['bill_id']} not found")

                amount = alloc_data["amount"]
                if amount > bill.pending_amount:
                    raise ValueError(
                        f"Allocation amount {amount} exceeds pending amount {bill.pending_amount} for bill {bill.bill_number}"
                    )

                # Create allocation
                allocation = BillAllocation(
                    bill_id=bill.id,
                    voucher_id=voucher_id,
                    allocated_amount=amount,
                    allocation_date=voucher.date,
                )
                session.add(allocation)

                # Update pending amount
                bill.pending_amount -= amount

                created_allocations.append(allocation)

            session.flush()
            for alloc in created_allocations:
                session.refresh(alloc)

            return created_allocations

    def get_outstanding_bills(
        self, ledger_id: int, as_of_date: Optional[date] = None
    ) -> list[dict]:
        """Get outstanding bills for a ledger.

        Args:
            ledger_id: Party ledger ID
            as_of_date: Calculate outstanding as of this date (default: today)

        Returns:
            List of outstanding bills with aging info
        """
        if as_of_date is None:
            as_of_date = date.today()

        with self.session() as session:
            bills = session.execute(
                select(Bill)
                .where(
                    Bill.ledger_id == ledger_id,
                    Bill.pending_amount > 0.01,
                    Bill.bill_date <= as_of_date,
                )
                .order_by(Bill.bill_date.asc())
            ).scalars().all()

            result = []
            for bill in bills:
                days_outstanding = (as_of_date - bill.bill_date).days
                days_overdue = (as_of_date - bill.due_date).days if as_of_date > bill.due_date else 0

                result.append({
                    "bill_id": bill.id,
                    "bill_number": bill.bill_number,
                    "bill_date": bill.bill_date.isoformat(),
                    "due_date": bill.due_date.isoformat(),
                    "bill_type": bill.bill_type,
                    "original_amount": bill.original_amount,
                    "pending_amount": bill.pending_amount,
                    "days_outstanding": days_outstanding,
                    "days_overdue": max(0, days_overdue),
                    "status": "overdue" if days_overdue > 0 else "current",
                })

            return result

    def get_aging_report(
        self,
        ledger_id: Optional[int] = None,
        group_name: Optional[str] = None,
        as_of_date: Optional[date] = None,
        aging_buckets: list[tuple[int, int]] = None,
    ) -> dict:
        """Generate aging report for receivables/payables.

        Args:
            ledger_id: Specific ledger (optional)
            group_name: Group name like 'Sundry Debtors' (optional)
            as_of_date: Calculate aging as of this date (default: today)
            aging_buckets: [(0, 30), (31, 60), (61, 90), (91, 180), (181, 9999)]

        Returns:
            Aging summary with buckets
        """
        if as_of_date is None:
            as_of_date = date.today()

        if aging_buckets is None:
            aging_buckets = [
                (0, 30),
                (31, 60),
                (61, 90),
                (91, 180),
                (181, 9999),
            ]

        with self.session() as session:
            # Build query
            query = select(Bill).where(
                Bill.pending_amount > 0.01,
                Bill.bill_date <= as_of_date,
            )

            if ledger_id:
                query = query.where(Bill.ledger_id == ledger_id)
            elif group_name:
                query = (
                    query.join(Ledger)
                    .join(Group)
                    .where(Group.name == group_name)
                )

            bills = session.execute(query).scalars().all()

            # Initialize buckets
            bucket_labels = []
            for start, end in aging_buckets:
                if end >= 9999:
                    bucket_labels.append(f"{start}+")
                else:
                    bucket_labels.append(f"{start}-{end}")

            buckets = {label: {"count": 0, "amount": 0.0} for label in bucket_labels}
            total_outstanding = 0.0
            bill_details = []

            # Categorize bills
            for bill in bills:
                days_outstanding = (as_of_date - bill.bill_date).days
                total_outstanding += bill.pending_amount

                # Find bucket
                bucket_label = None
                for i, (start, end) in enumerate(aging_buckets):
                    if start <= days_outstanding <= end:
                        bucket_label = bucket_labels[i]
                        break

                if bucket_label:
                    buckets[bucket_label]["count"] += 1
                    buckets[bucket_label]["amount"] += bill.pending_amount

                bill_details.append({
                    "ledger_name": bill.ledger.name,
                    "bill_number": bill.bill_number,
                    "bill_date": bill.bill_date.isoformat(),
                    "due_date": bill.due_date.isoformat(),
                    "pending_amount": bill.pending_amount,
                    "days_outstanding": days_outstanding,
                    "bucket": bucket_label,
                })

            return {
                "as_of_date": as_of_date.isoformat(),
                "total_outstanding": total_outstanding,
                "total_bills": len(bills),
                "buckets": [
                    {
                        "range": label,
                        "count": buckets[label]["count"],
                        "amount": buckets[label]["amount"],
                        "percentage": (buckets[label]["amount"] / total_outstanding * 100) if total_outstanding > 0 else 0,
                    }
                    for label in bucket_labels
                ],
                "bills": bill_details,
            }


# Global database instance
db = Database()
