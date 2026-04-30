# AI Command Parser Examples

## Quick Start

1. Set API key:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

2. Run demo:
```bash
python examples/ai_demo.py --mode preset
```

3. Interactive mode:
```bash
python examples/ai_demo.py --mode interactive
```

## Test Suite

```bash
python tests/test_ai_parser.py
```

## Example Commands

### Voucher Creation
- "Create sales voucher for Acme Corp, $5000"
- "Record purchase from XYZ Ltd $3000"
- "Pay rent $1500"
- "Received $2000 from John Doe"

### With GST
- "Sales invoice for ABC Inc $10000 with 18% GST"

### Ledger Queries
- "Show ledger for Cash"
- "Display Acme Corp account"

### Reports
- "Generate trial balance"
- "Show P&L"
- "Balance sheet"

### Help
- "What is trial balance?"
- "How to record bank transfer?"
