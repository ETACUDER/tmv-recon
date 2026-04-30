# Cost Center Module Implementation

## Overview
Implemented full cost center tracking for department/project allocation in the Tally Mac Clone accounting system.

## Components Implemented

### 1. Models (models.py)

**CostCenter Model:**
- `id`: Primary key
- `name`: Unique cost center name (e.g., "Sales Department", "Project ABC")
- `parent_id`: Self-referencing FK for hierarchical structure
- `category`: Type classification (Department, Project, Location)
- `is_active`: Active status flag
- Relationships: parent, children (self-referential), allocations

**CostCenterAllocation Model:**
- `id`: Primary key
- `ledger_entry_id`: FK to LedgerEntry
- `cost_center_id`: FK to CostCenter
- `amount`: Allocated amount
- `percentage`: Optional percentage for proportional allocation
- Relationships: ledger_entry, cost_center

**LedgerEntry Enhancement:**
- Added `cost_center_allocations` relationship for multiple allocations per entry

### 2. Database Functions (database.py)

**create_cost_center(name, parent_id, category)**
- Creates new cost center with hierarchical support
- Returns created CostCenter object

**get_cost_center(cost_center_id)**
- Retrieves single cost center by ID

**get_cost_center_by_name(name)**
- Retrieves cost center by name

**list_cost_centers(active_only=True)**
- Lists all cost centers with optional active filter

**allocate_to_cost_centers(entry_id, allocations[])**
- Allocates ledger entry amount to multiple cost centers
- Validates total allocation matches entry amount (within 0.01 tolerance)
- Format: [{"cost_center_id": int, "amount": float, "percentage": float}]
- Raises ValueError if allocations don't sum correctly

**get_cost_center_report(cost_center_id, from_date, to_date)**
- Generates comprehensive report for cost center in date range
- Returns:
  - Cost center details
  - Total debit/credit/net amounts
  - List of all allocated entries with voucher details

### 3. API Endpoints (app.py)

**POST /api/cost-centers**
- Creates new cost center
- Body: {name, parent_id?, category?}
- Returns: Created cost center with ID

**GET /api/cost-centers?active_only=true**
- Lists cost centers in tree structure
- Returns hierarchical JSON with children nested

**POST /api/allocations**
- Allocates entry to cost centers
- Body: {entry_id, allocations: [{cost_center_id, amount, percentage?}]}
- Validates allocation totals match entry amount

**GET /api/cost-center-report?id=1&from=2026-01-01&to=2026-04-30**
- Generates cost center report for date range
- Returns comprehensive report with all entries and totals

## Usage Examples

### Create Cost Centers
```python
# Department
sales_dept = db.create_cost_center("Sales Department", category="Department")

# Project
project_abc = db.create_cost_center("Project ABC", category="Project")

# Hierarchical (sub-department)
sales_team_a = db.create_cost_center(
    "Sales Team A",
    parent_id=sales_dept.id,
    category="Department"
)
```

### Allocate Entry to Multiple Cost Centers
```python
# After creating a voucher with entries
allocations = db.allocate_to_cost_centers(
    entry_id=salary_entry.id,
    allocations=[
        {"cost_center_id": 1, "amount": 75000.0, "percentage": 50.0},
        {"cost_center_id": 2, "amount": 45000.0, "percentage": 30.0},
        {"cost_center_id": 3, "amount": 30000.0, "percentage": 20.0}
    ]
)
# Total must equal entry amount (150000.0)
```

### Generate Report
```python
report = db.get_cost_center_report(
    cost_center_id=1,
    from_date=date(2026, 4, 1),
    to_date=date(2026, 4, 30)
)

# Returns:
{
    "cost_center_id": 1,
    "cost_center_name": "Sales Department",
    "category": "Department",
    "from_date": "2026-04-01",
    "to_date": "2026-04-30",
    "total_debit": 75000.0,
    "total_credit": 0.0,
    "net_amount": 75000.0,
    "entries": [
        {
            "date": "2026-04-15",
            "voucher_number": "PAY-001",
            "voucher_type": "Payment",
            "ledger_name": "Salary Expense",
            "amount": 75000.0,
            "is_debit": true,
            "percentage": 50.0
        }
    ]
}
```

## Validation Rules

1. **Allocation Totals**: Sum of allocations must equal entry amount (tolerance: 0.01)
2. **Cost Center Names**: Must be unique
3. **Hierarchical Structure**: Self-referential parent-child relationships supported
4. **Active Status**: Can filter by active/inactive cost centers

## Demo Script

Run `examples/cost_center_demo.py` to see:
- 8 cost centers created (departments, projects, locations)
- Hierarchical structure (Sales Team A under Sales Department)
- 2 vouchers with entries
- 5 allocations across multiple cost centers
- 2 detailed reports with entry breakdowns
- Tree structure visualization

## Database Schema

Tables created:
- `cost_centers`: Master cost center data
- `cost_center_allocations`: Junction table linking entries to cost centers

Foreign Keys:
- cost_centers.parent_id → cost_centers.id
- cost_center_allocations.ledger_entry_id → ledger_entries.id
- cost_center_allocations.cost_center_id → cost_centers.id

## Files Modified

1. `/src/tally_mac_clone/models.py` - Added CostCenter, CostCenterAllocation models
2. `/src/tally_mac_clone/database.py` - Added cost center CRUD and reporting functions
3. `/src/tally_mac_clone/app.py` - Added 4 API endpoints
4. `/examples/cost_center_demo.py` - Created comprehensive demo

## Testing

Run demo:
```bash
python3 examples/cost_center_demo.py
```

Expected output: 8 cost centers, 2 vouchers, 5 allocations, hierarchical tree display, detailed reports.
