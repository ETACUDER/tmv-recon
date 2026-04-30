#!/bin/bash
# RecordX.Finance startup script

set -e

echo "🚀 Starting RecordX.Finance..."

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -e . -q
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Azure credentials"
    exit 1
fi

# Start the app
echo "✅ Starting server on http://localhost:8000"
python -m uvicorn tally_mac_clone.app:app --reload --host 0.0.0.0 --port 8000
