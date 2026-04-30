# Tally Mac Clone - Architecture

## Overview
AI-powered accounting system with chat interface. Replicates Tally's data model and accounting conventions on macOS.

## Tech Stack
- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite + SQLAlchemy ORM
- **Frontend**: Tailwind CSS + Alpine.js (no build process)
- **AI**: Claude Sonnet 4.6 (Anthropic API)

## Architecture Pattern
**Command-Action-Preview (CAP)**
- User types natural language in chat (left panel)
- AI parses command and extracts structured data
- Preview shown in workspace (right panel)
- User confirms → Data persists to database

## Data Model (Tally-Compatible)

### Core Entities
```
Company
├── Vouchers
│   └── LedgerEntries (must balance to zero)
└── Ledgers
    └── Groups
```

### Sign Convention (Tally Standard)
- **Debit**: is_debit=True
- **Credit**: is_debit=False
- Per-voucher entries sum to zero

### Voucher Types
- Sales, Purchase, Receipt, Payment, Journal, Contra

## System Components

### 1. Data Layer (`models.py`)
SQLAlchemy models matching Tally structure:
- Company, Group, Ledger, VoucherType, Voucher, LedgerEntry

### 2. Database Layer (`database.py`)
- SQLAlchemy session management
- CRUD operations for all entities
- Transaction handling
- Trial balance calculation

### 3. AI Layer (`ai.py`)
- Claude API integration
- Command parsing: natural language → structured JSON
- Context management (remember recent entities)
- Accounting domain knowledge

### 4. API Layer (`app.py`)
FastAPI routes:
- `POST /api/chat` - AI conversation
- `GET/POST /api/vouchers` - Voucher CRUD
- `GET/POST /api/ledgers` - Ledger CRUD
- `GET /api/trial-balance` - Trial balance report
- `GET /` - Serve frontend

### 5. Frontend (`static/index.html`)
Split-panel UI:
- **Left (30%)**: Chat interface
- **Right (70%)**: Workspace (dashboard, forms, reports)
- Alpine.js state management
- Tailwind styling

## User Workflows

### Create Sales Voucher
1. User: "Create sales voucher for Acme Corp, $5000"
2. AI extracts: party=Acme, amount=5000, type=Sales
3. Workspace shows pre-filled voucher form
4. User reviews, clicks Save
5. POST /api/vouchers → Database

### View Trial Balance
1. User: "Show trial balance"
2. AI: action=show_trial_balance
3. GET /api/trial-balance
4. Workspace displays table (Ledger | Debit | Credit)

### Add Ledger
1. User: "Add new ledger 'Marketing Expenses' under Indirect Expenses"
2. AI extracts: name=Marketing Expenses, group=Indirect Expenses
3. Workspace shows ledger form
4. POST /api/ledgers

## Key Design Decisions

### Why FastAPI?
- Consistent with existing tmv-recon stack
- Fast async support for AI streaming
- Auto-generated OpenAPI docs

### Why Alpine.js?
- No build process (fast iteration)
- Lightweight (~15KB)
- Sufficient for accounting UI interactivity

### Why SQLite?
- Single-user accounting (like Tally)
- Zero configuration
- File-based backups

### Why Claude?
- Excellent structured output
- Understands accounting domain
- API already available in project

## File Structure
```
tally-mac-clone/
├── src/tally_mac_clone/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   ├── database.py        # DB session, CRUD
│   ├── ai.py              # Claude integration
│   ├── app.py             # FastAPI routes
│   └── static/
│       └── index.html     # Frontend UI
├── docs/
│   └── architecture.md    # This file
├── tests/
├── pyproject.toml
├── .env.example
└── README.md
```

## Development Phases

### Phase 1: Foundation (Current)
- [x] Project setup
- [x] Data models
- [x] AI integration
- [x] Frontend UI
- [ ] Database layer
- [ ] FastAPI backend
- [ ] End-to-end test

### Phase 2: Core Features
- Voucher CRUD (all types)
- Ledger management
- Trial balance
- Basic validation (entries balance)

### Phase 3: Advanced
- Reports (P&L, Balance Sheet, Day Book)
- Multi-company support
- GST calculations
- Bank reconciliation

### Phase 4: Polish
- Export to Tally XML
- Data migration from tmv-recon
- Keyboard shortcuts
- Mobile responsive

## Security Notes
- Single-user desktop app (no auth needed)
- SQLite file can be encrypted at OS level
- API keys in .env (not committed)

## Performance Targets
- Chat response: <2s
- Trial balance (1000 entries): <100ms
- Voucher creation: <50ms

## Future Considerations
- Multi-user: Add auth, PostgreSQL
- Cloud: Deploy as web app
- Tally sync: Bidirectional XML import/export
- Offline: PWA with service worker
