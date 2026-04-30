"""FastAPI backend for Tally Mac Clone."""
import os
from datetime import date, datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

from .database import db
from .models import Voucher, Ledger, Group, VoucherType, Company
from .ai import parse_accounting_command, get_context_aware_response
from .banking import BankingOperations
from .import_etl import ImportETL, ImportValidationError

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="RecordX.Finance", version="0.1.0")

# Initialize banking operations and import ETL
banking = BankingOperations(db)
import_etl = ImportETL(db)

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


class BillCreate(BaseModel):
    ledger_id: int
    bill_number: str
    bill_date: str
    due_date: str
    amount: float
    bill_type: str
    voucher_id: int


class BillAllocationCreate(BaseModel):
    voucher_id: int
    allocations: List[dict]


class AgingReportRequest(BaseModel):
    ledger_id: Optional[int] = None
    group_name: Optional[str] = None
    as_of_date: Optional[str] = None
    buckets: Optional[str] = None


class CompanyCreate(BaseModel):
    name: str
    financial_year_start: str
    books_beginning_from: Optional[str] = None
    mailing_name: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    gst_registration_type: Optional[str] = None
    tan: Optional[str] = None
    cin: Optional[str] = None
    maintain_bill_wise: bool = True
    use_cost_centers: bool = False
    enable_multi_currency: bool = False
    maintain_payroll: bool = False
    maintain_inventory: bool = False
    enable_gst: bool = True
    base_currency_id: Optional[int] = None


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
            "group_id": ledger.group_id,
            "opening_balance": ledger.opening_balance,
            "entries": entries,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/ledgers/{ledger_id}")
async def update_ledger(ledger_id: int, ledger: LedgerCreate):
    """Update an existing ledger."""
    try:
        with db.session() as session:
            existing = session.get(Ledger, ledger_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Ledger not found")

            group = db.get_group_by_name(ledger.group_name)
            if not group:
                raise HTTPException(status_code=400, detail=f"Group not found: {ledger.group_name}")

            existing.name = ledger.name
            existing.group_id = group.id
            existing.opening_balance = ledger.opening_balance
            session.flush()

            return {
                "id": existing.id,
                "name": existing.name,
                "group": group.name,
                "opening_balance": existing.opening_balance,
                "message": f"Ledger '{existing.name}' updated successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/ledgers/{ledger_id}")
async def delete_ledger(ledger_id: int):
    """Delete a ledger."""
    try:
        with db.session() as session:
            ledger = session.get(Ledger, ledger_id)
            if not ledger:
                raise HTTPException(status_code=404, detail="Ledger not found")

            # Check if ledger has entries
            if len(ledger.entries) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete ledger with existing entries"
                )

            name = ledger.name
            session.delete(ledger)
            session.flush()

            return {
                "message": f"Ledger '{name}' deleted successfully"
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


class GroupCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    is_revenue: bool = False
    is_expense: bool = False
    is_asset: bool = False
    is_liability: bool = False


@app.post("/api/groups")
async def create_group(group: GroupCreate):
    """Create a new group."""
    try:
        created = db.create_group(
            name=group.name,
            parent_id=group.parent_id,
            is_revenue=group.is_revenue,
            is_expense=group.is_expense,
            is_asset=group.is_asset,
            is_liability=group.is_liability,
        )
        return {
            "id": created.id,
            "name": created.name,
            "parent_id": created.parent_id,
            "message": f"Group '{created.name}' created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/groups/{group_id}")
async def get_group(group_id: int):
    """Get group details."""
    try:
        group = db.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        return {
            "id": group.id,
            "name": group.name,
            "parent_id": group.parent_id,
            "is_revenue": group.is_revenue,
            "is_expense": group.is_expense,
            "is_asset": group.is_asset,
            "is_liability": group.is_liability,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/groups/{group_id}")
async def update_group(group_id: int, group: GroupCreate):
    """Update an existing group."""
    try:
        with db.session() as session:
            existing = session.get(Group, group_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Group not found")

            existing.name = group.name
            existing.parent_id = group.parent_id
            existing.is_revenue = group.is_revenue
            existing.is_expense = group.is_expense
            existing.is_asset = group.is_asset
            existing.is_liability = group.is_liability
            session.flush()

            return {
                "id": existing.id,
                "name": existing.name,
                "parent_id": existing.parent_id,
                "message": f"Group '{existing.name}' updated successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/groups/{group_id}")
async def delete_group(group_id: int):
    """Delete a group."""
    try:
        with db.session() as session:
            group = session.get(Group, group_id)
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")

            # Check if group has ledgers
            if len(group.ledgers) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete group with existing ledgers"
                )

            # Check if group has children
            if len(group.children) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete group with child groups"
                )

            name = group.name
            session.delete(group)
            session.flush()

            return {
                "message": f"Group '{name}' deleted successfully"
            }
    except HTTPException:
        raise
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


@app.post("/api/companies")
async def create_company(company: CompanyCreate):
    """Create a new company."""
    try:
        fy_start = datetime.strptime(company.financial_year_start, "%Y-%m-%d").date()
        books_from = None
        if company.books_beginning_from:
            books_from = datetime.strptime(company.books_beginning_from, "%Y-%m-%d").date()

        created = db.create_company(
            name=company.name,
            financial_year_start=fy_start,
            books_beginning_from=books_from,
            mailing_name=company.mailing_name,
            address=company.address,
            state=company.state,
            country=company.country,
            pincode=company.pincode,
            phone=company.phone,
            email=company.email,
            website=company.website,
            pan=company.pan,
            gstin=company.gstin,
            gst_registration_type=company.gst_registration_type,
            tan=company.tan,
            cin=company.cin,
            maintain_bill_wise=company.maintain_bill_wise,
            use_cost_centers=company.use_cost_centers,
            enable_multi_currency=company.enable_multi_currency,
            maintain_payroll=company.maintain_payroll,
            maintain_inventory=company.maintain_inventory,
            enable_gst=company.enable_gst,
            base_currency_id=company.base_currency_id,
        )
        return {
            "id": created.id,
            "name": created.name,
            "message": f"Company '{created.name}' created successfully"
        }
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
                "books_beginning_from": c.books_beginning_from.isoformat() if c.books_beginning_from else None,
                "gstin": c.gstin,
                "pan": c.pan,
                "state": c.state,
                "country": c.country,
            }
            for c in companies
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies/{company_id}")
async def get_company(company_id: int):
    """Get company details."""
    try:
        company = db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/companies/{company_id}")
async def update_company(company_id: int, request: Request):
    """Update company details."""
    try:
        data = await request.json()
        updated = db.update_company(company_id, **data)
        if not updated:
            raise HTTPException(status_code=404, detail="Company not found")

        return {
            "id": updated.id,
            "name": updated.name,
            "message": f"Company '{updated.name}' updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies/{company_id}/settings")
async def get_company_settings(company_id: int):
    """Get company configuration."""
    try:
        settings = db.get_company_settings(company_id)
        if not settings:
            raise HTTPException(status_code=404, detail="Company not found")
        return settings
    except HTTPException:
        raise
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


# Bill-wise details endpoints
@app.post("/api/bills")
async def create_bill(bill: BillCreate):
    """Create bill for receivable/payable tracking."""
    try:
        bill_date = datetime.strptime(bill.bill_date, "%Y-%m-%d").date()
        due_date = datetime.strptime(bill.due_date, "%Y-%m-%d").date()

        created = db.create_bill(
            ledger_id=bill.ledger_id,
            bill_number=bill.bill_number,
            bill_date=bill_date,
            due_date=due_date,
            amount=bill.amount,
            bill_type=bill.bill_type,
            voucher_id=bill.voucher_id,
        )
        return {
            "id": created.id,
            "bill_number": created.bill_number,
            "bill_date": created.bill_date.isoformat(),
            "due_date": created.due_date.isoformat(),
            "original_amount": created.original_amount,
            "pending_amount": created.pending_amount,
            "bill_type": created.bill_type,
            "message": f"Bill {created.bill_number} created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bills/outstanding")
async def get_outstanding_bills(ledger_id: int, as_of_date: Optional[str] = None):
    """Get outstanding bills for a ledger."""
    try:
        as_of = None
        if as_of_date:
            as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()

        bills = db.get_outstanding_bills(ledger_id, as_of)
        return {
            "ledger_id": ledger_id,
            "as_of_date": as_of.isoformat() if as_of else date.today().isoformat(),
            "total_bills": len(bills),
            "total_pending": sum(b["pending_amount"] for b in bills),
            "bills": bills,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bills/allocate")
async def allocate_payment(allocation: BillAllocationCreate):
    """Allocate payment/receipt to bills."""
    try:
        created = db.allocate_payment_to_bills(
            voucher_id=allocation.voucher_id,
            allocations=allocation.allocations,
        )
        return {
            "voucher_id": allocation.voucher_id,
            "allocated_count": len(created),
            "allocations": [
                {
                    "id": alloc.id,
                    "bill_id": alloc.bill_id,
                    "allocated_amount": alloc.allocated_amount,
                    "allocation_date": alloc.allocation_date.isoformat(),
                }
                for alloc in created
            ],
            "message": f"Allocated payment to {len(created)} bills"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/companies/{company_id}")
async def delete_company(company_id: int):
    """Delete a company."""
    try:
        with db.session() as session:
            company = session.get(Company, company_id)
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            company_name = company.name
            session.delete(company)
            session.flush()

        return {
            "message": f"Company '{company_name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/companies/{company_id}/set-active")
async def set_active_company(company_id: int):
    """Set active company (stored in session/client state)."""
    try:
        company = db.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        return {
            "id": company.id,
            "name": company.name,
            "financial_year_start": company.financial_year_start.isoformat(),
            "message": f"Switched to company '{company.name}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bills/aging")
async def get_aging_report(
    ledger_id: Optional[int] = None,
    group: Optional[str] = None,
    as_of_date: Optional[str] = None,
    buckets: Optional[str] = None,
):
    """Generate aging report for receivables/payables.

    Query params:
    - ledger_id: Specific ledger ID (optional)
    - group: Group name like 'Sundry Debtors' (optional)
    - as_of_date: Calculate aging as of date (default: today)
    - buckets: Comma-separated ranges like '0-30,31-60,61-90,91-180,181+' (default)
    """
    try:
        as_of = None
        if as_of_date:
            as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()

        aging_buckets = None
        if buckets:
            # Parse buckets like "0-30,31-60,61-90,91+"
            aging_buckets = []
            for bucket in buckets.split(","):
                if "+" in bucket:
                    start = int(bucket.replace("+", ""))
                    aging_buckets.append((start, 9999))
                else:
                    parts = bucket.split("-")
                    aging_buckets.append((int(parts[0]), int(parts[1])))

        report = db.get_aging_report(
            ledger_id=ledger_id,
            group_name=group,
            as_of_date=as_of,
            aging_buckets=aging_buckets,
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== IMPORT/ETL ENDPOINTS ====================

@app.get("/api/import/template/{master_type}")
async def download_import_template(master_type: str, voucher_type: Optional[str] = None):
    """Download Excel template for import.

    Supported master types: ledgers, groups, vouchers, stock-items
    For vouchers, specify voucher_type query param (Payment, Receipt, etc.)
    """
    try:
        if master_type == "ledgers":
            content = import_etl.generate_ledger_template()
            filename = "ledgers_import_template.xlsx"
        elif master_type == "groups":
            content = import_etl.generate_group_template()
            filename = "groups_import_template.xlsx"
        elif master_type == "vouchers":
            vtype = voucher_type or "Payment"
            content = import_etl.generate_voucher_template(vtype)
            filename = f"{vtype.lower()}_vouchers_template.xlsx"
        elif master_type == "stock-items":
            content = import_etl.generate_stock_item_template()
            filename = "stock_items_template.xlsx"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown master type: {master_type}")

        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Template generation requires openpyxl: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/excel/ledgers")
async def import_ledgers_excel(file: UploadFile = File(...)):
    """Import ledgers from Excel file."""
    try:
        content = await file.read()
        result = import_etl.import_ledgers_from_excel(content)
        return {
            "status": "completed",
            "total_records": result["total"],
            "success_count": result["success"],
            "error_count": len(result["errors"]),
            "errors": result["errors"],
            "created_ids": result["created_ids"]
        }
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Excel import requires pandas: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/excel/vouchers")
async def import_vouchers_excel(
    file: UploadFile = File(...),
    voucher_type: str = "Payment",
    company_id: int = 1
):
    """Import vouchers from Excel file.

    Query params:
    - voucher_type: Payment, Receipt, Journal, etc. (default: Payment)
    - company_id: Company ID (default: 1)
    """
    try:
        content = await file.read()
        result = import_etl.import_vouchers_from_excel(content, voucher_type, company_id)
        return {
            "status": "completed",
            "total_vouchers": result["total_vouchers"],
            "success_count": result["success"],
            "error_count": len(result["errors"]),
            "errors": result["errors"],
            "created_ids": result["created_ids"]
        }
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Excel import requires pandas: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/bank-statement")
async def import_bank_statement_file(
    file: UploadFile = File(...),
    ledger_id: int = None,
    file_format: str = "excel"
):
    """Import bank statement from CSV/Excel.

    Query params:
    - ledger_id: Bank ledger ID (required)
    - file_format: 'excel' or 'csv' (default: excel)

    File should have columns: date, description, debit, credit, balance (optional)
    """
    if not ledger_id:
        raise HTTPException(status_code=400, detail="ledger_id is required")

    try:
        content = await file.read()

        # Auto-detect common bank statement column mappings
        column_mapping = None
        filename_lower = file.filename.lower()
        if "hdfc" in filename_lower:
            column_mapping = {
                "Date": "date",
                "Narration": "description",
                "Withdrawal Amt.": "debit",
                "Deposit Amt.": "credit",
                "Closing Balance": "balance"
            }
        elif "icici" in filename_lower:
            column_mapping = {
                "Transaction Date": "date",
                "Description": "description",
                "Debit": "debit",
                "Credit": "credit",
                "Balance": "balance"
            }

        result = import_etl.import_bank_statement(
            file_content=content,
            ledger_id=ledger_id,
            file_format=file_format,
            column_mapping=column_mapping
        )

        return {
            "status": "completed",
            "total_records": result["total"],
            "imported_count": result["imported"],
            "matched_count": result["matched"],
            "unmatched_count": result["unmatched"],
            "error_count": len(result["errors"]),
            "errors": result["errors"],
            "suggestions": result["suggestions"]
        }
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Bank statement import requires pandas: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/import/xml")
async def import_xml_vouchers(file: UploadFile = File(...), company_id: int = 1):
    """Import vouchers from Tally XML format.

    Accepts ENVELOPE/BODY/TALLYMESSAGE/VOUCHER structure.

    Query params:
    - company_id: Company ID (default: 1)
    """
    try:
        content = await file.read()
        xml_content = content.decode('utf-8')

        result = import_etl.import_vouchers_from_xml(xml_content, company_id)

        return {
            "status": "completed",
            "total_vouchers": result["total"],
            "success_count": result["success"],
            "error_count": len(result["errors"]),
            "errors": result["errors"],
            "created_ids": result["created_ids"]
        }
    except ImportValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid XML file encoding")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REPORT ENDPOINTS ====================

@app.get("/api/reports/trial-balance")
async def report_trial_balance(
    company_id: int = 1,
):
    """Trial balance report."""
    try:
        data = db.get_trial_balance(company_id)
        return {
            "report": "trial_balance",
            "company_id": company_id,
            "data": data,
            "total_debit": sum(row["debit"] for row in data),
            "total_credit": sum(row["credit"] for row in data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/day-book")
async def report_day_book(
    company_id: int = 1,
    from_date: str = "2026-04-01",
    to_date: str = "2026-04-30",
):
    """Day book report (chronological voucher listing)."""
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

        data = db.get_day_book(company_id, from_dt, to_dt)
        return {
            "report": "day_book",
            "company_id": company_id,
            "from_date": from_date,
            "to_date": to_date,
            "voucher_count": len(data),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/balance-sheet")
async def report_balance_sheet(
    company_id: int = 1,
    as_of_date: str = "2026-04-30",
):
    """Balance sheet report."""
    try:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        data = db.get_balance_sheet(company_id, as_of)
        return {
            "report": "balance_sheet",
            "company_id": company_id,
            **data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/profit-loss")
async def report_profit_loss(
    company_id: int = 1,
    from_date: str = "2026-04-01",
    to_date: str = "2026-04-30",
):
    """Profit & loss statement."""
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

        data = db.get_profit_loss(company_id, from_dt, to_dt)
        return {
            "report": "profit_loss",
            "company_id": company_id,
            **data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/export")
async def export_report(
    report: str,
    format: str = "excel",
    company_id: int = 1,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    as_of_date: Optional[str] = None,
):
    """Export report to Excel.

    Query params:
    - report: trial-balance, day-book, balance-sheet, profit-loss
    - format: excel (only excel supported)
    - company_id: Company ID
    - from_date, to_date: For day-book and profit-loss
    - as_of_date: For balance-sheet
    """
    try:
        import pandas as pd
        from io import BytesIO

        # Get report data
        if report == "trial-balance":
            data = db.get_trial_balance(company_id)
            df = pd.DataFrame(data)
            filename = f"trial_balance_{company_id}.xlsx"

        elif report == "day-book":
            from_dt = datetime.strptime(from_date or "2026-04-01", "%Y-%m-%d").date()
            to_dt = datetime.strptime(to_date or "2026-04-30", "%Y-%m-%d").date()
            vouchers = db.get_day_book(company_id, from_dt, to_dt)

            # Flatten for Excel
            rows = []
            for v in vouchers:
                for entry in v["entries"]:
                    rows.append({
                        "Date": v["date"],
                        "Voucher Type": v["voucher_type"],
                        "Voucher Number": v["voucher_number"],
                        "Ledger": entry["ledger_name"],
                        "Debit": entry["debit"],
                        "Credit": entry["credit"],
                        "Narration": v["narration"],
                    })
            df = pd.DataFrame(rows)
            filename = f"day_book_{from_date}_to_{to_date}.xlsx"

        elif report == "balance-sheet":
            as_of = datetime.strptime(as_of_date or "2026-04-30", "%Y-%m-%d").date()
            bs_data = db.get_balance_sheet(company_id, as_of)

            # Create combined dataframe
            assets_df = pd.DataFrame(bs_data["assets"])
            assets_df["Type"] = "Asset"
            liabilities_df = pd.DataFrame(bs_data["liabilities"])
            liabilities_df["Type"] = "Liability"
            df = pd.concat([assets_df, liabilities_df], ignore_index=True)
            filename = f"balance_sheet_{as_of_date}.xlsx"

        elif report == "profit-loss":
            from_dt = datetime.strptime(from_date or "2026-04-01", "%Y-%m-%d").date()
            to_dt = datetime.strptime(to_date or "2026-04-30", "%Y-%m-%d").date()
            pl_data = db.get_profit_loss(company_id, from_dt, to_dt)

            # Create combined dataframe
            income_df = pd.DataFrame(pl_data["income"])
            income_df["Type"] = "Income"
            expenses_df = pd.DataFrame(pl_data["expenses"])
            expenses_df["Type"] = "Expense"
            df = pd.concat([income_df, expenses_df], ignore_index=True)
            filename = f"profit_loss_{from_date}_to_{to_date}.xlsx"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown report: {report}")

        # Export to Excel
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)

        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Excel export requires pandas and openpyxl. Install with: pip install pandas openpyxl"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
