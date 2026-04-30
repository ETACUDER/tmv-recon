"""
Test script for LLM provider switching.

Usage:
    python test_providers.py

Ensure .env is configured with:
    LLM_PROVIDER=azure-claude (or azure-grok, azure-openai, direct-claude)
    AZURE_ENDPOINT=https://...
    AZURE_API_KEY=...
    AZURE_DEPLOYMENT_NAME=...
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

def test_provider():
    """Test current LLM provider configuration."""
    from src.tally_mac_clone.ai import parse_accounting_command

    provider_name = os.getenv("LLM_PROVIDER", "azure-claude")
    print(f"Testing provider: {provider_name}")
    print("=" * 60)

    test_commands = [
        "Create sales voucher for Acme Corp, $5000",
        "Show ledger for Cash account",
        "Generate trial balance",
    ]

    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        try:
            result = parse_accounting_command(cmd)
            print(f"Action: {result.get('action')}")
            print(f"Entity: {result.get('entity')}")
            print(f"Response: {result.get('response')[:100]}...")
            print("✓ Success")
        except Exception as e:
            print(f"✗ Error: {e}")
        print("-" * 60)

if __name__ == "__main__":
    test_provider()
