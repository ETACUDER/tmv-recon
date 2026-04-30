# RecordX.Finance

**AI-Powered Accounting with Conversational Interface**

Chat with your accounting system. Create vouchers, view ledgers, generate reports - all through natural language.

Built with Tally-compatible data models. Supports Azure-based LLMs (Claude, Grok, OpenAI).

## Quick Start

```bash
# 1. Setup
cd tally-mac-clone
python -m venv .venv
source .venv/bin/activate

# 2. Install
pip install -e .

# 3. Configure (choose your LLM)
cp .env.example .env
# Edit .env with Azure credentials

# 4. Run
python -m uvicorn tally_mac_clone.app:app --reload

# 5. Open browser
open http://localhost:8000
```

## Features

- 💬 **Chat Interface** - Natural language accounting
- 📊 **Tally-Compatible** - Standard accounting data model
- 🔄 **Multi-LLM** - Switch between Claude/Grok/GPT
- 📈 **Reports** - Trial balance, ledgers, vouchers
- 🎨 **Split Panel UI** - Chat left, workspace right

## Architecture

- Backend: FastAPI + SQLAlchemy
- Frontend: Tailwind + Alpine.js
- AI: Azure Claude/Grok/OpenAI
- Database: SQLite
