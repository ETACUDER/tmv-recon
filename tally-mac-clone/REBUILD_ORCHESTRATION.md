# RecordX.Finance UI Rebuild - Parallel Agent Orchestration

**Date:** 2026-04-30  
**Goal:** Transform chat-only UI into full Tally keyboard-driven interface + AI chat assistant  
**Agents:** 8 parallel agents working on independent modules

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ [F3: Company] RecordX.Finance              [F12: Settings]       │
├─────────────────┬────────────────────────────────────────────────┤
│                 │ Gateway | Masters | Reports | Import           │
│  AI CHAT        ├────────────────────────────────────────────────┤
│  (30%)          │                                                 │
│                 │  ┌──────────────────────────────────────────┐  │
│  "Show cash     │  │  Current View (70% workspace)            │  │
│   balance"      │  │                                          │  │
│                 │  │  • Voucher Entry Forms (F5-F9)           │  │
│  "Create sales  │  │  • Reports (Trial Balance, Day Book)     │  │
│   voucher"      │  │  • Masters (Ledger/Group lists)          │  │
│                 │  │  • Data Tables (searchable, sortable)    │  │
│  "Find payments │  │  • Company Settings                      │  │
│   to ABC"       │  │                                          │  │
│                 │  └──────────────────────────────────────────┘  │
│                 │                                                 │
├─────────────────┴────────────────────────────────────────────────┤
│ Company: TMV Ltd | FY: 2025-26 | F5:Pmt F8:Sales ESC:Back        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Work Distribution

### Agent 1: Keyboard Navigation System
**Task #23** - Design keyboard-driven UI architecture

**Building:**
- Global keyboard event handler (F1-F12, Alt combos)
- Routing system (F5→payment, F8→sales, etc.)
- Status bar with shortcut hints
- Escape stack for navigation
- Alpine.js integration

**Files:**
- `src/tally_mac_clone/static/js/keyboard.js`
- Updates to `static/index.html`

**Key Mappings:**
- F5: Payment | F6: Receipt | F7: Journal | F8: Sales | F9: Purchase
- Alt+G: Gateway | Alt+K: Masters | Alt+R: Reports | Alt+X: Import
- Esc: Back | Ctrl+A: Save | F12: Settings

---

### Agent 2: Voucher Entry Forms
**Tasks #29, #30** - All 16 voucher types + proper Tally layout

**Building:**
- Payment Voucher (F5)
- Receipt Voucher (F6)
- Journal Voucher (F7)
- Sales Voucher (F8)
- Purchase Voucher (F9)
- + 11 other voucher types

**Each form has:**
- Date field (F2 to change)
- Auto-generated voucher number
- Party account autocomplete
- Ledger entries table (add/remove rows)
- Narration field
- Real-time Dr/Cr validation (must balance to 0)
- Save (Ctrl+A) / Cancel (Esc)
- GST auto-calculation

**Files:**
- Voucher components in `static/index.html` or separate templates
- Alpine.js reactive forms

---

### Agent 3: Reports + Export
**Tasks #27, #25** - Financial reports with Excel/PDF/XML export

**Building Backend:**
- GET `/api/reports/trial-balance`
- GET `/api/reports/day-book`
- GET `/api/reports/balance-sheet`
- GET `/api/reports/profit-loss`
- GET `/api/reports/cash-flow`
- GET `/api/reports/sales-register`
- GET `/api/reports/purchase-register`
- GET `/api/reports/bills-receivable`
- GET `/api/reports/bills-payable`
- GET `/api/reports/{name}/export?format=excel|pdf|xml`

**Building Frontend:**
- Reports menu navigation
- Drill-down functionality (group → ledgers → Day Book)
- Date range filters
- Export button (Alt+E) on each report
- Print functionality

**Libraries:**
- pandas for Excel export
- reportlab/weasyprint for PDF

---

### Agent 4: Masters Management UI
**Task #26** - Ledgers, Groups, Stock Items, Cost Centers

**Building Screens:**

1. **Ledgers**
   - List: searchable table (name, group, balance)
   - Create/Edit form: name, group, opening balance, GST config
   - Delete with confirmation

2. **Groups**
   - Tree view showing hierarchy
   - Create/Edit: name, parent, ISDEEMEDPOSITIVE flag

3. **Stock Items**
   - List: name, unit, rate, stock quantity
   - Create/Edit form

4. **Cost Centers**
   - List with search
   - Create/Edit form

5. **Currencies**
   - List with exchange rates
   - Create/Edit

**Features:**
- Alt+K to access Masters menu
- Keyboard nav: Tab, Enter to save, Esc to cancel
- Uses existing Phase 2 backend APIs

---

### Agent 5: Import/ETL System
**Task #20** - Excel/XML/Bank statement imports

**Building:**

1. **Excel Import:**
   - GET `/api/import/template/{type}` - download templates
   - POST `/api/import/excel` - upload & parse
   - Validation report (errors/success)
   - Bulk insert to database

2. **Bank Statement Import:**
   - POST `/api/import/bank-statement`
   - Parse CSV/Excel (date, desc, debit, credit)
   - Auto-match to existing vouchers
   - Suggest ledger mappings
   - Create reconciliation entries

3. **XML Import:**
   - POST `/api/import/xml` - Tally XML format
   - Parse ENVELOPE/BODY/TALLYMESSAGE
   - Support voucher bulk creation

**Frontend:**
- Import menu (Alt+X)
- File upload component
- Validation results table
- Preview before commit
- Progress indicator

---

### Agent 6: Data Tables UI
**Task #28** - Searchable, sortable tables for all masters

**Building Tables:**

1. **Ledger Table**
   - Columns: Name, Group, Type, Opening Balance, Current Balance
   - Search, filter by group, sort
   - Click row → edit
   - Keyboard nav (↑↓, Enter)

2. **Voucher List Table**
   - Columns: Date, Type, Number, Party, Amount, Narration
   - Filter: date range, voucher type, party
   - Sort by date/amount
   - Click → view/edit

3. **Stock Items Table**
   - Columns: Name, Group, Unit, Rate, Stock Qty, Value
   - Low stock alerts

4. **Outstanding Bills Table**
   - Columns: Party, Bill Date, Due Date, Amount, Pending, Overdue Days
   - Aging buckets (0-30, 31-60, 61-90, 90+)
   - Click → allocate payment

**Generic Component:**
- Reusable Alpine.js table component
- Props: data, columns, searchable, sortable
- Export to Excel button

---

### Agent 7: Company Management
**Task #22** - Company info, switcher, FY management

**Building:**

1. **Company Info Screen (F3):**
   - Name, address, city, state, country
   - GSTIN, PAN, CIN
   - Financial year start/end
   - Base currency
   - Books beginning date
   - Feature toggles (inventory, multi-currency)

2. **Company Switcher (F3):**
   - List all companies
   - Click to switch active
   - Create new company
   - Delete with confirmation

3. **Settings Screen (F12):**
   - Enable/disable features
   - GST settings
   - Voucher numbering
   - Security & users

**Backend:**
- GET `/api/companies` - list all
- POST `/api/companies` - create
- PATCH `/api/companies/{id}` - update (exists from Phase 2)
- DELETE `/api/companies/{id}` - delete
- POST `/api/companies/{id}/set-active` - switch

**Status Bar:**
- Show active company name
- Show financial year
- Show current user

---

### Agent 8: Gateway Menu System
**Task #31** - Main navigation menu

**Building:**

```
Gateway (Alt+G)
├── Masters (Alt+K)
│   ├── Ledgers
│   ├── Groups
│   ├── Stock Items
│   ├── Units
│   ├── Cost Centers
│   └── Currencies
├── Transactions/Vouchers
│   ├── Payment (F5)
│   ├── Receipt (F6)
│   ├── Journal (F7)
│   ├── Sales (F8)
│   ├── Purchase (F9)
│   └── Contra (F4)
├── Reports (Alt+R)
│   ├── Day Book
│   ├── Trial Balance
│   ├── Balance Sheet
│   ├── Profit & Loss
│   └── All Registers
├── Import/Export (Alt+X)
│   ├── Import Excel
│   ├── Export Data
│   └── Bank Statement
└── Utilities (Alt+U)
    ├── Backup/Restore
    └── Settings (F12)
```

**Implementation:**
- Top menu bar (always visible)
- Dropdown menus on click/Alt key
- Keyboard navigation (↑↓, Enter)
- Routing via Alpine.js $store
- Breadcrumb navigation
- Integrates with keyboard.js from Agent 1

---

## Dependencies & Coordination

### Agent Dependencies:
- **Agent 8 (Gateway)** depends on **Agent 1 (Keyboard)** - both work on routing
- **Agent 2 (Vouchers)** uses **Agent 1 (Keyboard)** shortcuts
- **Agent 4 (Masters)** uses **Agent 6 (Tables)** for list views
- **Agent 3 (Reports)** uses **Agent 6 (Tables)** for data display

### File Coordination:
- **static/index.html** - modified by Agents 1, 2, 4, 6, 7, 8 (potential conflicts)
  - Solution: Each agent works on separate Alpine components
  - Final integration: merge all components into single HTML

- **app.py** - modified by Agents 3, 5, 7
  - Solution: Each adds distinct endpoints, minimal overlap
  - Agent 3: `/api/reports/*`
  - Agent 5: `/api/import/*`
  - Agent 7: `/api/companies/*` (already exists)

### Integration Order:
1. Agent 1 (Keyboard) + Agent 8 (Gateway) → routing foundation
2. Agent 2 (Vouchers) + Agent 4 (Masters) → core screens
3. Agent 6 (Tables) → data display components
4. Agent 3 (Reports) + Agent 5 (Import) → backend endpoints
5. Agent 7 (Company) → settings & management
6. Final integration → merge all components, test end-to-end

---

## Success Criteria

**UI Complete When:**
- ✅ Chat on left (30%), Tally workspace on right (70%)
- ✅ F-keys work (F5-F12 trigger vouchers/actions)
- ✅ Alt combos work (Alt+G/K/R/X for menus)
- ✅ Gateway menu navigable with keyboard
- ✅ All 16 voucher types have entry forms
- ✅ Ledger autocomplete works
- ✅ Dr/Cr validation real-time
- ✅ Reports display with drill-down
- ✅ Export to Excel/PDF/XML works
- ✅ Masters CRUD screens functional
- ✅ Import Excel/XML/bank statements works
- ✅ Data tables searchable, sortable
- ✅ Company switcher works
- ✅ Status bar shows shortcuts
- ✅ Esc navigation works (go back)

**Backend Complete When:**
- ✅ All report endpoints return data
- ✅ Export endpoints generate files
- ✅ Import endpoints parse & validate
- ✅ Company management API works
- ✅ Existing Phase 2 APIs integrated

---

## Current Status

**Agents Running:** 8 in parallel  
**Tasks In Progress:** 9/12  
**Estimated Completion:** Agents will report back when done  
**Next Step:** Wait for agent completion, integrate, test

---

**Orchestration Strategy:**
1. Launch all agents in parallel (✅ Done)
2. Let agents work independently on isolated modules
3. Monitor for completion notifications
4. Review each agent's output
5. Integrate all components
6. Resolve conflicts (if any)
7. End-to-end testing
8. Git commit with comprehensive message

**Risk Mitigation:**
- File conflicts: Agents work on separate sections/components
- API endpoint overlap: Distinct route prefixes per agent
- Integration issues: Final review & merge step before commit
- Testing: Manual testing of all workflows after integration
