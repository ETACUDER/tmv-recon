# AI Chat Integration - Capabilities

## Overview

Claude-powered natural language interface for Tally accounting operations. Parses commands into structured JSON for backend processing.

## Core Features

### 1. Voucher Creation
Parse natural language into structured voucher entries with automatic Dr/Cr calculation.

**Supported Voucher Types:**
- Sales (revenue)
- Purchase (expenses)
- Payment (outflow)
- Receipt (inflow)
- Journal (general)
- Contra (transfers)

**Examples:**
```
"Create sales voucher for Acme Corp, $5000"
→ {action: "create_voucher", data: {type: "sales", party: "Acme Corp", amount: 5000}}

"Record payment of $2000 to supplier ABC Ltd"
→ {action: "create_voucher", data: {type: "payment", party: "ABC Ltd", amount: 2000}}

"Received $4000 from customer John Doe"
→ {action: "create_voucher", data: {type: "receipt", party: "John Doe", amount: 4000}}
```

### 2. Ledger Queries
Display transaction history for specific accounts.

**Examples:**
```
"Show ledger for Cash account"
→ {action: "show_ledger", data: {account: "Cash"}}

"Display transactions for Acme Corp from Jan to March"
→ {action: "show_ledger", data: {account: "Acme Corp", from_date: "2026-01-01", to_date: "2026-03-31"}}
```

### 3. Report Generation
Generate accounting reports.

**Examples:**
```
"Generate trial balance"
→ {action: "show_trial_balance", entity: "report"}

"Show profit and loss statement"
→ {action: "show_profit_loss", entity: "report"}

"Display balance sheet"
→ {action: "show_balance_sheet", entity: "report"}
```

### 4. GST/Tax Handling
Automatically calculates tax components when mentioned.

**Examples:**
```
"Create sales invoice for ABC Inc $10000 with 18% GST"
→ Generates entries for base amount, CGST, SGST/IGST ledgers

"Purchase from XYZ with $5000 base + 10% tax"
→ Splits into purchase and input tax entries
```

### 5. Context Awareness
Remembers recent operations for follow-up commands.

**Examples:**
```
Context: Last voucher was sales to Acme Corp for $5000

User: "Add another $1000 to the same party"
→ AI understands "same party" = Acme Corp

User: "Show their ledger"
→ AI understands "their" = Acme Corp
```

### 6. Help & Explanations
Answers accounting questions and provides guidance.

**Examples:**
```
"What is trial balance?"
→ {action: "chat", response: "Detailed explanation..."}

"How do I record a bank transfer?"
→ {action: "chat", response: "Use contra voucher..."}

"Difference between receipt and payment?"
→ {action: "chat", response: "Receipt is inflow..."}
```

## Response Structure

All commands return JSON:
```json
{
  "action": "create_voucher | show_ledger | show_trial_balance | chat | error",
  "entity": "voucher | ledger | report | conversation",
  "data": {
    // Extracted structured data
    "voucher_type": "sales",
    "party": "Acme Corp",
    "amount": 5000,
    "currency": "USD",
    "entries": [
      {"account": "Acme Corp", "debit": 5000, "credit": 0},
      {"account": "Sales", "debit": 0, "credit": 5000}
    ]
  },
  "response": "Natural language response for user"
}
```

## Accounting Intelligence

### Double-Entry Bookkeeping
AI automatically generates balanced Dr/Cr entries:
- Sales: Dr Party/Cash, Cr Sales
- Purchase: Dr Purchase, Cr Party/Cash
- Payment: Dr Party/Expense, Cr Cash/Bank
- Receipt: Dr Cash/Bank, Cr Party/Income

### Account Classification
Understands account types:
- **Assets**: Cash, Bank, Debtors, Stock (Dr increase)
- **Liabilities**: Creditors, Loans (Cr increase)
- **Income**: Sales, Interest (Cr increase)
- **Expenses**: Purchase, Rent, Salaries (Dr increase)
- **Capital**: Owner equity (Cr increase)

### Smart Defaults
- Date: Current date if not specified
- Currency: USD default
- Narration: Auto-generated from command
- Account creation: Suggests new accounts when needed

## Usage

### Basic Command Parsing
```python
from tally_mac_clone.ai import parse_accounting_command

result = parse_accounting_command("Create sales voucher for Acme Corp, $5000")
print(result["action"])  # "create_voucher"
print(result["data"])    # {voucher_type: "sales", party: "Acme Corp", ...}
```

### Context-Aware Parsing
```python
from tally_mac_clone.ai import get_context_aware_response

context = {
    "last_voucher": {"type": "sales", "party": "Acme Corp", "amount": 5000},
    "active_party": "Acme Corp"
}

result = get_context_aware_response("Add another $1000", context)
# AI understands to create another voucher for Acme Corp
```

## API Configuration

Requires environment variable:
```bash
ANTHROPIC_API_KEY=your-key-here
```

Model: `claude-sonnet-4-5` (latest Sonnet)

## Testing

Run test suite:
```bash
python tests/test_ai_parser.py
```

Or with pytest:
```bash
pytest tests/test_ai_parser.py -v
```

## Error Handling

- Invalid commands → Returns chat action with helpful guidance
- API errors → Returns error action with message
- Ambiguous commands → Makes reasonable assumptions, mentions in response
- Missing data → Uses smart defaults (current date, USD, etc.)

## Next Steps

Integration with FastAPI routes (not yet implemented):
- POST /api/chat - Send command, receive parsed response
- WebSocket /ws/chat - Real-time chat interface
- GET /api/chat/context - Retrieve recent context
- POST /api/chat/execute - Parse + execute command in one call
