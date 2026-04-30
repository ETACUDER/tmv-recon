"""Banking module for bank reconciliation, cheques, and statements."""
from datetime import date, datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BankReconciliation, Cheque, BankStatement, Voucher, LedgerEntry


class BankingOperations:
    """Banking operations for reconciliation and cheque management."""

    def __init__(self, db):
        self.db = db

    def create_cheque(
        self,
        voucher_id: int,
        cheque_number: str,
        cheque_date: date,
        bank_name: str,
        ifsc_code: Optional[str] = None,
        is_post_dated: bool = False,
    ) -> Cheque:
        """Create cheque record for a voucher."""
        with self.db.session() as session:
            cheque = Cheque(
                voucher_id=voucher_id,
                cheque_number=cheque_number,
                cheque_date=cheque_date,
                bank_name=bank_name,
                ifsc_code=ifsc_code,
                status="issued",
                is_post_dated=is_post_dated,
            )
            session.add(cheque)
            session.flush()
            session.refresh(cheque)
            return cheque

    def update_cheque_status(
        self, cheque_id: int, status: str, clearance_date: Optional[date] = None
    ) -> Cheque:
        """Update cheque status (issued, presented, cleared, dishonored)."""
        with self.db.session() as session:
            cheque = session.get(Cheque, cheque_id)
            if not cheque:
                raise ValueError(f"Cheque {cheque_id} not found")

            cheque.status = status
            if status == "cleared" and clearance_date:
                cheque.clearance_date = clearance_date

            session.flush()
            session.refresh(cheque)
            return cheque

    def get_pending_cheques(self, status: str = "issued") -> list[Cheque]:
        """Get cheques by status."""
        with self.db.session() as session:
            query = select(Cheque).where(Cheque.status == status).order_by(Cheque.cheque_date)
            return list(session.execute(query).scalars().all())

    def get_pdc_maturity_reminders(self, from_date: date, to_date: date) -> list[Cheque]:
        """Get post-dated cheques maturing in date range."""
        with self.db.session() as session:
            query = (
                select(Cheque)
                .where(
                    Cheque.is_post_dated == True,
                    Cheque.status.in_(["issued", "presented"]),
                    Cheque.cheque_date >= from_date,
                    Cheque.cheque_date <= to_date,
                )
                .order_by(Cheque.cheque_date)
            )
            return list(session.execute(query).scalars().all())

    def auto_clear_matured_pdc(self, as_of_date: date) -> list[Cheque]:
        """Auto-clear PDCs that have matured."""
        with self.db.session() as session:
            cheques = session.execute(
                select(Cheque).where(
                    Cheque.is_post_dated == True,
                    Cheque.status == "issued",
                    Cheque.cheque_date <= as_of_date,
                )
            ).scalars().all()

            cleared = []
            for cheque in cheques:
                cheque.status = "cleared"
                cheque.clearance_date = cheque.cheque_date
                cleared.append(cheque)

            session.flush()
            return cleared

    def import_bank_statement(
        self, ledger_id: int, statement_data: list[dict]
    ) -> list[BankStatement]:
        """Import bank statement entries.

        statement_data format:
        [{"date": date, "cheque_number": str, "reference": str, "debit": float, "credit": float, "balance": float, "description": str}, ...]
        """
        with self.db.session() as session:
            statements = []
            for data in statement_data:
                statement = BankStatement(
                    bank_ledger_id=ledger_id,
                    transaction_date=data["date"],
                    cheque_number=data.get("cheque_number"),
                    reference=data.get("reference"),
                    debit=data.get("debit", 0.0),
                    credit=data.get("credit", 0.0),
                    balance=data["balance"],
                    description=data.get("description"),
                )
                session.add(statement)
                statements.append(statement)

            session.flush()
            for statement in statements:
                session.refresh(statement)

            return statements

    def auto_reconcile(
        self, ledger_id: int, from_date: date, to_date: date, tolerance: float = 0.01
    ) -> dict:
        """Auto-reconcile bank statements with vouchers by amount and date.

        Matches bank statement entries with voucher entries within tolerance.
        Returns summary of matched and unmatched items.
        """
        with self.db.session() as session:
            # Get unmatched bank statements
            statements = session.execute(
                select(BankStatement).where(
                    BankStatement.bank_ledger_id == ledger_id,
                    BankStatement.transaction_date >= from_date,
                    BankStatement.transaction_date <= to_date,
                    BankStatement.matched_voucher_id.is_(None),
                )
            ).scalars().all()

            # Get vouchers with entries for this bank ledger (unreconciled)
            vouchers = session.execute(
                select(Voucher)
                .join(LedgerEntry)
                .outerjoin(BankReconciliation)
                .where(
                    LedgerEntry.ledger_id == ledger_id,
                    Voucher.date >= from_date,
                    Voucher.date <= to_date,
                    BankReconciliation.id.is_(None),
                )
                .distinct()
            ).scalars().all()

            matched_count = 0
            for statement in statements:
                amount = statement.debit if statement.debit > 0 else statement.credit

                for voucher in vouchers:
                    # Get voucher amount for this ledger
                    entry = next(
                        (e for e in voucher.entries if e.ledger_id == ledger_id), None
                    )
                    if not entry:
                        continue

                    # Match by amount and date proximity (within 3 days)
                    date_diff = abs((statement.transaction_date - voucher.date).days)
                    amount_diff = abs(amount - abs(entry.amount))

                    if date_diff <= 3 and amount_diff <= tolerance:
                        # Match found
                        statement.matched_voucher_id = voucher.id

                        # Create reconciliation record
                        reconciliation = BankReconciliation(
                            voucher_id=voucher.id,
                            bank_statement_date=statement.transaction_date,
                            reconciled=True,
                            reconciliation_date=datetime.now().date(),
                            difference_amount=amount_diff,
                        )
                        session.add(reconciliation)

                        matched_count += 1
                        break

            session.flush()

            # Get unmatched counts
            unmatched_statements = len([s for s in statements if s.matched_voucher_id is None])
            unmatched_vouchers = len(vouchers) - matched_count

            return {
                "matched_count": matched_count,
                "unmatched_statements": unmatched_statements,
                "unmatched_vouchers": unmatched_vouchers,
                "total_statements": len(statements),
                "total_vouchers": len(vouchers),
            }

    def manual_reconcile(
        self, statement_id: int, voucher_id: int, difference_amount: float = 0.0
    ) -> BankReconciliation:
        """Manually reconcile a bank statement with a voucher."""
        with self.db.session() as session:
            statement = session.get(BankStatement, statement_id)
            if not statement:
                raise ValueError(f"Bank statement {statement_id} not found")

            voucher = session.get(Voucher, voucher_id)
            if not voucher:
                raise ValueError(f"Voucher {voucher_id} not found")

            # Update statement
            statement.matched_voucher_id = voucher_id

            # Create/update reconciliation
            existing = session.execute(
                select(BankReconciliation).where(BankReconciliation.voucher_id == voucher_id)
            ).scalar_one_or_none()

            if existing:
                existing.bank_statement_date = statement.transaction_date
                existing.reconciled = True
                existing.reconciliation_date = datetime.now().date()
                existing.difference_amount = difference_amount
                reconciliation = existing
            else:
                reconciliation = BankReconciliation(
                    voucher_id=voucher_id,
                    bank_statement_date=statement.transaction_date,
                    reconciled=True,
                    reconciliation_date=datetime.now().date(),
                    difference_amount=difference_amount,
                )
                session.add(reconciliation)

            session.flush()
            session.refresh(reconciliation)
            return reconciliation

    def get_unreconciled_items(self, ledger_id: int) -> dict:
        """Get unreconciled bank statements and vouchers for a ledger."""
        with self.db.session() as session:
            # Unmatched bank statements
            unmatched_statements = session.execute(
                select(BankStatement).where(
                    BankStatement.bank_ledger_id == ledger_id,
                    BankStatement.matched_voucher_id.is_(None),
                ).order_by(BankStatement.transaction_date.desc())
            ).scalars().all()

            # Unreconciled vouchers
            unreconciled_vouchers = session.execute(
                select(Voucher)
                .join(LedgerEntry)
                .outerjoin(BankReconciliation)
                .where(
                    LedgerEntry.ledger_id == ledger_id,
                    BankReconciliation.id.is_(None),
                )
                .distinct()
                .order_by(Voucher.date.desc())
            ).scalars().all()

            return {
                "unmatched_statements": [
                    {
                        "id": s.id,
                        "date": s.transaction_date.isoformat(),
                        "cheque_number": s.cheque_number,
                        "reference": s.reference,
                        "debit": s.debit,
                        "credit": s.credit,
                        "balance": s.balance,
                        "description": s.description,
                    }
                    for s in unmatched_statements
                ],
                "unreconciled_vouchers": [
                    {
                        "id": v.id,
                        "voucher_number": v.voucher_number,
                        "date": v.date.isoformat(),
                        "voucher_type": v.voucher_type.name,
                        "narration": v.narration,
                        "amount": sum(
                            e.amount for e in v.entries if e.ledger_id == ledger_id
                        ),
                    }
                    for v in unreconciled_vouchers
                ],
            }

    def print_cheque(self, voucher_id: int, template: str = "default") -> dict:
        """Generate cheque print data."""
        with self.db.session() as session:
            voucher = session.get(Voucher, voucher_id)
            if not voucher:
                raise ValueError(f"Voucher {voucher_id} not found")

            cheques = session.execute(
                select(Cheque).where(Cheque.voucher_id == voucher_id)
            ).scalars().all()

            if not cheques:
                raise ValueError(f"No cheques found for voucher {voucher_id}")

            cheque = cheques[0]

            # Get payee (credit entry ledger)
            payee_entry = next((e for e in voucher.entries if not e.is_debit), None)
            payee_name = payee_entry.ledger.name if payee_entry else "Unknown"

            # Get amount
            amount = sum(e.amount for e in voucher.entries if not e.is_debit)

            return {
                "cheque_number": cheque.cheque_number,
                "date": cheque.cheque_date.isoformat(),
                "payee_name": payee_name,
                "amount": amount,
                "amount_in_words": self._amount_to_words(amount),
                "bank_name": cheque.bank_name,
                "ifsc_code": cheque.ifsc_code,
                "narration": voucher.narration,
                "template": template,
            }

    def _amount_to_words(self, amount: float) -> str:
        """Convert amount to words (simplified Indian format)."""
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        def convert_below_thousand(n):
            if n == 0:
                return ""
            elif n < 10:
                return units[n]
            elif n < 20:
                return teens[n - 10]
            elif n < 100:
                return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
            else:
                return units[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")

        rupees = int(amount)
        paise = int((amount - rupees) * 100)

        if rupees == 0:
            return "Zero Rupees"

        # Convert rupees
        crore = rupees // 10000000
        lakh = (rupees % 10000000) // 100000
        thousand = (rupees % 100000) // 1000
        hundred = rupees % 1000

        result = []
        if crore > 0:
            result.append(convert_below_thousand(crore) + " Crore")
        if lakh > 0:
            result.append(convert_below_thousand(lakh) + " Lakh")
        if thousand > 0:
            result.append(convert_below_thousand(thousand) + " Thousand")
        if hundred > 0:
            result.append(convert_below_thousand(hundred))

        words = " ".join(result) + " Rupees"
        if paise > 0:
            words += " and " + convert_below_thousand(paise) + " Paise"

        return words + " Only"
