"""Tally-compatible SQLAlchemy models.

Sign convention (per Tally):
- Debit entries: is_debit=True, amount can be positive or negative
- Credit entries: is_debit=False, amount can be positive or negative
- Per-voucher entries must balance to zero (sum of Dr - sum of Cr = 0)

Alternative convention from reference models:
- Tally signs amounts: Dr=negative, Cr=positive in voucher entries
- ISDEEMEDPOSITIVE flag carries the side independently
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Date,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    financial_year_start: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    vouchers: Mapped[list["Voucher"]] = relationship(
        "Voucher", back_populates="company", cascade="all, delete-orphan"
    )


class Group(Base):
    """Tally group hierarchy (e.g., Sundry Debtors, Sundry Creditors, Sales Accounts)."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("groups.id"), nullable=True
    )
    is_revenue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expense: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_asset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_liability: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    parent: Mapped[Optional["Group"]] = relationship(
        "Group", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Group"]] = relationship(
        "Group", back_populates="parent", cascade="all, delete-orphan"
    )
    ledgers: Mapped[list["Ledger"]] = relationship(
        "Ledger", back_populates="group", cascade="all, delete-orphan"
    )


class Ledger(Base):
    """Tally ledger master (e.g., specific debtor/creditor, bank account)."""

    __tablename__ = "ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    opening_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="ledgers")
    entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry", back_populates="ledger", cascade="all, delete-orphan"
    )


class VoucherType(Base):
    """Voucher types: Sales, Purchase, Receipt, Payment, Journal, Contra."""

    __tablename__ = "voucher_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # Relationships
    vouchers: Mapped[list["Voucher"]] = relationship(
        "Voucher", back_populates="voucher_type", cascade="all, delete-orphan"
    )


class Voucher(Base):
    """Tally voucher (transaction document)."""

    __tablename__ = "vouchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voucher_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("voucher_types.id"), nullable=False
    )
    voucher_number: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    narration: Mapped[str] = mapped_column(Text, default="", nullable=False)
    company_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("companies.id"), nullable=False
    )
    currency_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=True
    )
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    foreign_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    voucher_type: Mapped["VoucherType"] = relationship("VoucherType", back_populates="vouchers")
    company: Mapped["Company"] = relationship("Company", back_populates="vouchers")
    currency: Mapped[Optional["Currency"]] = relationship("Currency")
    entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry", back_populates="voucher", cascade="all, delete-orphan"
    )


class Currency(Base):
    """Currency master for multi-currency support."""

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    exchange_rates: Mapped[list["ExchangeRate"]] = relationship(
        "ExchangeRate", back_populates="currency", cascade="all, delete-orphan"
    )


class ExchangeRate(Base):
    """Historical exchange rates for currencies."""

    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    currency: Mapped["Currency"] = relationship("Currency", back_populates="exchange_rates")


class LedgerEntry(Base):
    """Individual ledger entry within a voucher.

    Sign convention:
    - is_debit=True: Debit entry (Dr)
    - is_debit=False: Credit entry (Cr)
    - amount: Can be positive or negative
    - Per-voucher balance: sum(amount where is_debit) - sum(amount where not is_debit) = 0
    """

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vouchers.id"), nullable=False
    )
    ledger_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ledgers.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_debit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    voucher: Mapped["Voucher"] = relationship("Voucher", back_populates="entries")
    ledger: Mapped["Ledger"] = relationship("Ledger", back_populates="entries")
    cost_center_allocations: Mapped[list["CostCenterAllocation"]] = relationship(
        "CostCenterAllocation", back_populates="ledger_entry", cascade="all, delete-orphan"
    )


class CostCenter(Base):
    """Cost center for department/project tracking."""

    __tablename__ = "cost_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # Department, Project, Location
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    parent: Mapped[Optional["CostCenter"]] = relationship(
        "CostCenter", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["CostCenter"]] = relationship(
        "CostCenter", back_populates="parent", cascade="all, delete-orphan"
    )
    allocations: Mapped[list["CostCenterAllocation"]] = relationship(
        "CostCenterAllocation", back_populates="cost_center", cascade="all, delete-orphan"
    )


class CostCenterAllocation(Base):
    """Allocation of ledger entry amount to cost centers."""

    __tablename__ = "cost_center_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ledger_entries.id"), nullable=False
    )
    cost_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For proportional allocation
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    ledger_entry: Mapped["LedgerEntry"] = relationship("LedgerEntry", back_populates="cost_center_allocations")
    cost_center: Mapped["CostCenter"] = relationship("CostCenter", back_populates="allocations")


class BankReconciliation(Base):
    """Bank reconciliation tracking for vouchers."""

    __tablename__ = "bank_reconciliations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vouchers.id"), nullable=False, unique=True
    )
    bank_statement_date: Mapped[Date] = mapped_column(Date, nullable=False)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciliation_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    difference_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    voucher: Mapped["Voucher"] = relationship("Voucher", backref="bank_reconciliation")


class Cheque(Base):
    """Cheque tracking for payment/receipt vouchers."""

    __tablename__ = "cheques"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vouchers.id"), nullable=False
    )
    cheque_number: Mapped[str] = mapped_column(String(50), nullable=False)
    cheque_date: Mapped[Date] = mapped_column(Date, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="issued", nullable=False
    )  # issued, presented, cleared, dishonored
    clearance_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    is_post_dated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    voucher: Mapped["Voucher"] = relationship("Voucher", backref="cheques")


class BankStatement(Base):
    """Bank statement entries for reconciliation."""

    __tablename__ = "bank_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_ledger_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ledgers.id"), nullable=False
    )
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False)
    cheque_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # NEFT/RTGS/UPI ref
    debit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    matched_voucher_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vouchers.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    bank_ledger: Mapped["Ledger"] = relationship("Ledger", backref="bank_statements")
    matched_voucher: Mapped[Optional["Voucher"]] = relationship("Voucher", backref="bank_statement_matches")
