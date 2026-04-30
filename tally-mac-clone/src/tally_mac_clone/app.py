"""FastAPI backend for Tally Mac Clone."""
import os
from datetime import date, datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from .database import db
from .models import Voucher, Ledger, Group, VoucherType
from .ai import parse_accounting_command, get_context_aware_response
from .banking import BankingOperations

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="RecordX.Finance", version="0.1.0")

# Initialize banking operations
banking = BankingOperations(db)

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    action: str
    entity: Optional[str] = None
    data: Optional[dict] = None
    response: str


class VoucherCreate(BaseModel):
    voucher_type: str
    voucher_number: str
    date: str
    company_id: int
    narration: str = ""
    entries: List[dict]


class LedgerCreate(BaseModel):
    name: str
    group_name: str
    opening_balance: float = 0.0


class TrialBalanceRow(BaseModel):
    ledger_id: int
    ledger_name: str
    debit: float
    credit: float


class CostCenterCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    category: str = "Department"


class CostCenterAllocationCreate(BaseModel):
    entry_id: int
    allocations: List[dict]


class ChequeCreate(BaseModel):
    voucher_id: int
    cheque_number: str
    cheque_date: str
    bank_name: str
    ifsc_code: Optional[str] = None
    is_post_dated: bool = False


class ChequeUpdateStatus(BaseModel):
    status: str
    clearance_date: Optional[str] = None


class BankStatementImport(BaseModel):
    ledger_id: int
    statements: List[dict]


class ManualReconcileRequest(BaseModel):
    statement_id: int
    voucher_id: int
    difference_amount: float = 0.0


class AutoReconcileRequest(BaseModel):
    ledger_id: int
    from_date: str
    to_date: str
    tolerance: float = 0.01


class CurrencyCreate(BaseModel):
    code: str
    symbol: str
    name: str
    decimal_places: int = 2
    is_base: bool = False


class ExchangeRateCreate(BaseModel):
    currency_id: int
    date: str
    rate: float


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    db.create_tables()
    db.seed_default_data()

    # Create default company if none exists
    companies = db.list_companies()
    if not companies:
        db.create_company(
            name="Default Company",
            financial_year_start=date(2026, 4, 1)
        )


# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    index_file = static_dir / "index.html"
    return HTMLResponse(content=index_file.read_text())


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message and return structured response."""
    try:
        if request.context:
            result = get_context_aware_response(request.message, request.context)
        else:
            result = parse_accounting_command(request.message)

        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vouchers")
async def create_voucher(voucher: VoucherCreate):
    """Create a new voucher."""
    try:
        # Get voucher type
        vtype = db.get_voucher_type_by_name(voucher.voucher_type.capitalize())
        if not vtype:
            raise HTTPException(status_code=400, detail=f"Invalid voucher type: {voucher.voucher_type}")

        # Parse date
        voucher_date = datetime.strptime(voucher.date, "%Y-%m-%d").date()

        # Create voucher
        created = db.create_voucher(
            voucher_type_id=vtype.id,
            voucher_number=voucher.voucher_number,
            date=voucher_date,
            company_id=voucher.company_id,
            narration=voucher.narration,
            entries=voucher.entries,
        )

        return {
            "id": created.id,
            "voucher_number": created.voucher_number,
            "date": created.date.isoformat(),
            "message": f"Voucher {created.voucher_number} created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vouchers")
async def list_vouchers(company_id: Optional[int] = None, limit: int = 100):
    """List vouchers."""
    try:
        with db.session() as session:
            from sqlalchemy import select
            from .models import Voucher, VoucherType
            from sqlalchemy.orm import joinedload

            query = select(Voucher).options(joinedload(Voucher.voucher_type)).order_by(Voucher.date.desc(), Voucher.id.desc())
            if company_id:
                query = query.where(Voucher.company_id == company_id)
            query = query.limit(limit)
            vouchers = session.execute(query).scalars().unique().all()

            return [
                {
                    "id": v.id,
                    "voucher_type": v.voucher_type.name,
                    "voucher_number": v.voucher_number,
                    "date": v.date.isoformat(),
                    "narration": v.narration,
                    "entries_count": len(v.entries),
                }
                for v in vouchers
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vouchers/{voucher_id}")
async def get_voucher(voucher_id: int):
    """Get voucher details."""
    try:
        voucher = db.get_voucher(voucher_id)
        if not voucher:
            raise HTTPException(status_code=404, detail="Voucher not found")

        return {
            "id": voucher.id,
            "voucher_type": voucher.voucher_type.name,
            "voucher_number": voucher.voucher_number,
            "date": voucher.date.isoformat(),
            "narration": voucher.narration,
            "entries": [
                {
                    "ledger_id": e.ledger_id,
                    "ledger_name": e.ledger.name,
                    "amount": e.amount,
                    "is_debit": e.is_debit,
                }
                for e in voucher.entries
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ledgers")
async def create_ledger(ledger: LedgerCreate):
    """Create a new ledger."""
    try:
        # Get group
        group = db.get_group_by_name(ledger.group_name)
        if not group:
            raise HTTPException(status_code=400, detail=f"Group not found: {ledger.group_name}")

        # Create ledger
        created = db.create_ledger(
            name=ledger.name,
            group_id=group.id,
            opening_balance=ledger.opening_balance,
        )

        return {
            "id": created.id,
            "name": created.name,
            "group": group.name,
            "opening_balance": created.opening_balance,
            "message": f"Ledger '{created.name}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ledgers")
async def list_ledgers():
    """List all ledgers."""
    try:
        ledgers = db.list_ledgers()
        return [
            {
                "id": l.id,
                "name": l.name,
                "group": l.group.name,
                "opening_balance": l.opening_balance,
            }
            for l in ledgers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ledgers/{ledger_id}")
async def get_ledger(ledger_id: int):
    """Get ledger details with entries."""
    try:
        ledger = db.get_ledger(ledger_id)
        if not ledger:
            raise HTTPException(status_code=404, detail="Ledger not found")

        # Get entries
        entries = []
        for entry in ledger.entries:
            entries.append({
                "voucher_id": entry.voucher_id,
                "voucher_number": entry.voucher.voucher_number,
                "date": entry.voucher.date.isoformat(),
                "amount": entry.amount,
                "is_debit": entry.is_debit,
            })

        return {
            "id": ledger.id,
            "name": ledger.name,
            "group": ledger.group.name,
            "opening_balance": ledger.opening_balance,
            "entries": entries,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trial-balance", response_model=List[TrialBalanceRow])
async def get_trial_balance(company_id: int = 1):
    """Get trial balance for a company."""
    try:
        balance = db.get_trial_balance(company_id)
        return [TrialBalanceRow(**row) for row in balance]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/groups")
async def list_groups():
    """List all account groups."""
    try:
        groups = db.list_groups()
        return [
            {
                "id": g.id,
                "name": g.name,
                "parent_id": g.parent_id,
                "is_revenue": g.is_revenue,
                "is_expense": g.is_expense,
                "is_asset": g.is_asset,
                "is_liability": g.is_liability,
            }
            for g in groups
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/voucher-types")
async def list_voucher_types():
    """List all voucher types."""
    try:
        vtypes = db.list_voucher_types()
        return [{"id": vt.id, "name": vt.name} for vt in vtypes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies")
async def list_companies():
    """List all companies."""
    try:
        companies = db.list_companies()
        return [
            {
                "id": c.id,
                "name": c.name,
                "financial_year_start": c.financial_year_start.isoformat(),
            }
            for c in companies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats(company_id: int = 1):
    """Get dashboard statistics."""
    try:
        vouchers = db.list_vouchers(company_id=company_id, limit=1000)
        ledgers = db.list_ledgers()
        trial_balance = db.get_trial_balance(company_id)

        total_debit = sum(row["debit"] for row in trial_balance)
        total_credit = sum(row["credit"] for row in trial_balance)

        return {
            "total_vouchers": len(vouchers),
            "total_ledgers": len(ledgers),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balance_status": "balanced" if abs(total_debit - total_credit) < 0.01 else "unbalanced",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Cost Center endpoints
@app.post("/api/cost-centers")
async def create_cost_center(cost_center: CostCenterCreate):
    """Create a new cost center."""
    try:
        created = db.create_cost_center(
            name=cost_center.name,
            parent_id=cost_center.parent_id,
            category=cost_center.category,
        )
        return {
            "id": created.id,
            "name": created.name,
            "parent_id": created.parent_id,
            "category": created.category,
            "is_active": created.is_active,
            "message": f"Cost center '{created.name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cost-centers")
async def list_cost_centers(active_only: bool = True):
    """List cost centers in tree structure."""
    try:
        cost_centers = db.list_cost_centers(active_only=active_only)

        # Build tree structure
        def build_tree(parent_id=None):
            nodes = []
            for cc in cost_centers:
                if cc.parent_id == parent_id:
                    node = {
                        "id": cc.id,
                        "name": cc.name,
                        "category": cc.category,
                        "is_active": cc.is_active,
                        "children": build_tree(cc.id)
                    }
                    nodes.append(node)
            return nodes

        return {"cost_centers": build_tree()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/allocations")
async def create_allocation(allocation: CostCenterAllocationCreate):
    """Allocate ledger entry to cost centers."""
    try:
        created = db.allocate_to_cost_centers(
            entry_id=allocation.entry_id,
            allocations=allocation.allocations,
        )
        return {
            "entry_id": allocation.entry_id,
            "allocations": [
                {
                    "id": alloc.id,
                    "cost_center_id": alloc.cost_center_id,
                    "amount": alloc.amount,
                    "percentage": alloc.percentage,
                }
                for alloc in created
            ],
            "message": f"Allocated entry to {len(created)} cost centers"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cost-center-report")
async def get_cost_center_report(
    id: int,
    from_date: str = "2026-01-01",
    to_date: str = "2026-04-30"
):
    """Get cost center report for date range."""
    try:
        from_date_parsed = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_parsed = datetime.strptime(to_date, "%Y-%m-%d").date()

        report = db.get_cost_center_report(
            cost_center_id=id,
            from_date=from_date_parsed,
            to_date=to_date_parsed,
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Banking endpoints
@app.post("/api/cheques")
async def create_cheque(cheque: ChequeCreate):
    """Create cheque for a voucher."""
    try:
        cheque_date = datetime.strptime(cheque.cheque_date, "%Y-%m-%d").date()
        created = banking.create_cheque(
            voucher_id=cheque.voucher_id,
            cheque_number=cheque.cheque_number,
            cheque_date=cheque_date,
            bank_name=cheque.bank_name,
            ifsc_code=cheque.ifsc_code,
            is_post_dated=cheque.is_post_dated,
        )
        return {
            "id": created.id,
            "cheque_number": created.cheque_number,
            "status": created.status,
            "message": f"Cheque {created.cheque_number} created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/cheques/{cheque_id}")
async def update_cheque_status(cheque_id: int, update: ChequeUpdateStatus):
    """Update cheque status."""
    try:
        clearance_date = None
        if update.clearance_date:
            clearance_date = datetime.strptime(update.clearance_date, "%Y-%m-%d").date()

        updated = banking.update_cheque_status(
            cheque_id=cheque_id,
            status=update.status,
            clearance_date=clearance_date,
        )
        return {
            "id": updated.id,
            "status": updated.status,
            "clearance_date": updated.clearance_date.isoformat() if updated.clearance_date else None,
            "message": f"Cheque status updated to {updated.status}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cheques")
async def list_cheques(status: str = "issued"):
    """Get cheques by status."""
    try:
        cheques = banking.get_pending_cheques(status=status)
        return [
            {
                "id": c.id,
                "voucher_id": c.voucher_id,
                "cheque_number": c.cheque_number,
                "cheque_date": c.cheque_date.isoformat(),
                "bank_name": c.bank_name,
                "ifsc_code": c.ifsc_code,
                "status": c.status,
                "is_post_dated": c.is_post_dated,
                "clearance_date": c.clearance_date.isoformat() if c.clearance_date else None,
            }
            for c in cheques
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cheques/pdc-reminders")
async def pdc_reminders(from_date: str, to_date: str):
    """Get PDC maturity reminders."""
    try:
        from_date_parsed = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_parsed = datetime.strptime(to_date, "%Y-%m-%d").date()

        cheques = banking.get_pdc_maturity_reminders(from_date_parsed, to_date_parsed)
        return [
            {
                "id": c.id,
                "voucher_id": c.voucher_id,
                "cheque_number": c.cheque_number,
                "cheque_date": c.cheque_date.isoformat(),
                "bank_name": c.bank_name,
                "status": c.status,
            }
            for c in cheques
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cheques/auto-clear-pdc")
async def auto_clear_pdc(as_of_date: str):
    """Auto-clear matured PDCs."""
    try:
        as_of_date_parsed = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        cleared = banking.auto_clear_matured_pdc(as_of_date_parsed)
        return {
            "cleared_count": len(cleared),
            "cheques": [
                {
                    "id": c.id,
                    "cheque_number": c.cheque_number,
                    "cheque_date": c.cheque_date.isoformat(),
                }
                for c in cleared
            ],
            "message": f"Auto-cleared {len(cleared)} matured PDCs"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cheques/{voucher_id}/print")
async def print_cheque(voucher_id: int, template: str = "default"):
    """Generate cheque print data."""
    try:
        data = banking.print_cheque(voucher_id, template)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bank-statements/import")
async def import_bank_statement(data: BankStatementImport):
    """Import bank statement."""
    try:
        # Parse dates in statement data
        statement_data = []
        for stmt in data.statements:
            stmt_copy = stmt.copy()
            stmt_copy["date"] = datetime.strptime(stmt["date"], "%Y-%m-%d").date()
            statement_data.append(stmt_copy)

        imported = banking.import_bank_statement(data.ledger_id, statement_data)
        return {
            "imported_count": len(imported),
            "message": f"Imported {len(imported)} bank statement entries"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reconciliation/auto")
async def auto_reconcile(data: AutoReconcileRequest):
    """Auto-reconcile bank statements."""
    try:
        from_date = datetime.strptime(data.from_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(data.to_date, "%Y-%m-%d").date()

        result = banking.auto_reconcile(
            ledger_id=data.ledger_id,
            from_date=from_date,
            to_date=to_date,
            tolerance=data.tolerance,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reconciliation/manual")
async def manual_reconcile(data: ManualReconcileRequest):
    """Manually reconcile statement with voucher."""
    try:
        reconciliation = banking.manual_reconcile(
            statement_id=data.statement_id,
            voucher_id=data.voucher_id,
            difference_amount=data.difference_amount,
        )
        return {
            "id": reconciliation.id,
            "voucher_id": reconciliation.voucher_id,
            "reconciled": reconciliation.reconciled,
            "reconciliation_date": reconciliation.reconciliation_date.isoformat(),
            "difference_amount": reconciliation.difference_amount,
            "message": "Reconciliation successful"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reconciliation/pending")
async def get_unreconciled_items(ledger_id: int):
    """Get unreconciled items for a bank ledger."""
    try:
        result = banking.get_unreconciled_items(ledger_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Currency endpoints
@app.post("/api/currencies")
async def create_currency(currency: CurrencyCreate):
    """Create a new currency."""
    try:
        created = db.create_currency(
            code=currency.code,
            symbol=currency.symbol,
            name=currency.name,
            decimal_places=currency.decimal_places,
            is_base=currency.is_base,
        )
        return {
            "id": created.id,
            "code": created.code,
            "symbol": created.symbol,
            "name": created.name,
            "decimal_places": created.decimal_places,
            "is_base": created.is_base,
            "message": f"Currency {created.code} created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/currencies")
async def list_currencies():
    """List all currencies."""
    try:
        currencies = db.list_currencies()
        return [
            {
                "id": c.id,
                "code": c.code,
                "symbol": c.symbol,
                "name": c.name,
                "decimal_places": c.decimal_places,
                "is_base": c.is_base,
            }
            for c in currencies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exchange-rates")
async def create_exchange_rate(exchange_rate: ExchangeRateCreate):
    """Create a new exchange rate."""
    try:
        rate_date = datetime.strptime(exchange_rate.date, "%Y-%m-%d").date()
        created = db.create_exchange_rate(
            currency_id=exchange_rate.currency_id,
            date=rate_date,
            rate=exchange_rate.rate,
        )
        return {
            "id": created.id,
            "currency_id": created.currency_id,
            "date": created.date.isoformat(),
            "rate": created.rate,
            "message": f"Exchange rate created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/exchange-rate")
async def get_exchange_rate(currency: str, date: str):
    """Get exchange rate for currency on specific date."""
    try:
        rate_date = datetime.strptime(date, "%Y-%m-%d").date()
        rate = db.get_exchange_rate(currency, rate_date)

        if rate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Exchange rate not found for {currency} on {date}"
            )

        return {
            "currency": currency,
            "date": date,
            "rate": rate,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
