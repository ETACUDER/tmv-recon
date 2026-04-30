# RecordX.Finance - Quick Start

## 🚀 Start the App

```bash
cd /Volumes/CRESCENT/dev/project-sonnet/tmv-recon/tally-mac-clone
./start.sh
```

Then open: **http://localhost:8001**

## 📝 What You'll See

**Left Panel (30%)**: Chat interface  
**Right Panel (70%)**: Accounting workspace

## 💬 Try These Commands

In the chat interface:

```
"Create sales voucher for Acme Corp, $5000"
"Show me the trial balance"
"Add a new ledger called Marketing under Indirect Expenses"
"What vouchers did we create today?"
```

## 🔧 Configuration

### Switch LLM Provider

Edit `.env`:

```bash
# Current: Direct Claude
LLM_PROVIDER=direct-claude
ANTHROPIC_API_KEY=sk-ant-...

# Azure Claude
LLM_PROVIDER=azure-claude
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-key
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5

# Azure Grok
LLM_PROVIDER=azure-grok
AZURE_DEPLOYMENT_NAME=grok

# Azure GPT-4
LLM_PROVIDER=azure-openai
AZURE_DEPLOYMENT_NAME=gpt-4
```

## 📊 Default Data

The system comes pre-loaded with:
- **1 Company**: Default Company (FY 2026-04-01)
- **11 Groups**: Debtors, Creditors, Banks, Sales, Purchases, etc.
- **6 Voucher Types**: Sales, Purchase, Receipt, Payment, Journal, Contra

## 🧪 API Testing

```bash
# Get stats
curl http://localhost:8001/api/stats

# Create ledger
curl -X POST http://localhost:8001/api/ledgers \
  -H "Content-Type: application/json" \
  -d '{"name": "Customer ABC", "group_name": "Sundry Debtors"}'

# Trial balance
curl http://localhost:8001/api/trial-balance?company_id=1

# Chat with AI
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create payment voucher for rent $2000"}'
```

## 📚 Documentation

- `DELIVERABLE.md` - Complete system overview
- `architecture.md` - Technical architecture
- `LLM_PROVIDERS.md` - Multi-LLM setup guide
- `README.md` - Project readme

## 🐛 Troubleshooting

**Port already in use?**
```bash
# Change port in start.sh or run manually:
python -m uvicorn tally_mac_clone.app:app --port 8002
```

**Database issues?**
```bash
# Reset database
rm tally.db recordx.db
./start.sh  # Will recreate with seed data
```

**LLM not responding?**
```bash
# Check .env has valid API keys
# Test with: python tests/test_ai_parser.py
```

## 🎯 Key Files

- `src/tally_mac_clone/app.py` - FastAPI backend
- `src/tally_mac_clone/ai.py` - AI parsing
- `src/tally_mac_clone/models.py` - Data models
- `src/tally_mac_clone/static/index.html` - Frontend UI
- `.env` - Configuration

## 🔐 Security Notes

- API keys in `.env` (not committed to git)
- Single-user desktop app (no auth needed)
- Database file can be encrypted at OS level

## 📈 Next Steps

1. Connect frontend chat to `/api/chat` endpoint
2. Wire up workspace panels to backend APIs
3. Add voucher validation (Dr/Cr must balance)
4. Implement all report types
5. Add export to Tally XML

---

**Need help?** Check `DELIVERABLE.md` for full documentation.
