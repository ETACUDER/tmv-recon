"""
Test suite for AI command parser.

Run with: python -m pytest tests/test_ai_parser.py -v
Or directly: python tests/test_ai_parser.py
"""

import sys
import os
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tally_mac_clone.ai import parse_accounting_command, get_context_aware_response


def test_sales_voucher_parsing():
    """Test parsing of sales voucher command."""
    result = parse_accounting_command("Create sales voucher for Acme Corp, $5000")

    assert result["action"] == "create_voucher"
    assert result["entity"] == "voucher"
    assert "amount" in result["data"]
    assert "party" in result["data"]
    print("\n✓ Sales voucher parsing test passed")
    return result


def test_ledger_query():
    """Test parsing of ledger query command."""
    result = parse_accounting_command("Show ledger for Cash account")

    assert result["action"] == "show_ledger"
    assert result["entity"] == "ledger"
    assert "account" in result["data"]
    print("✓ Ledger query test passed")
    return result


def test_trial_balance():
    """Test parsing of trial balance command."""
    result = parse_accounting_command("Generate trial balance")

    assert result["action"] == "show_trial_balance"
    assert result["entity"] == "report"
    print("✓ Trial balance test passed")
    return result


def test_payment_voucher():
    """Test parsing of payment voucher command."""
    result = parse_accounting_command("Record payment of $2000 to supplier ABC Ltd")

    assert result["action"] == "create_voucher"
    assert result["entity"] == "voucher"
    assert result["data"]["voucher_type"] == "payment"
    print("✓ Payment voucher test passed")
    return result


def test_context_awareness():
    """Test context-aware parsing."""
    context = {
        "last_voucher": {
            "type": "sales",
            "party": "Acme Corp",
            "amount": 5000
        },
        "active_party": "Acme Corp"
    }

    result = get_context_aware_response("Add another $1000 to the same party", context)

    # Should understand "same party" refers to Acme Corp
    assert "data" in result
    print("✓ Context awareness test passed")
    return result


def test_help_query():
    """Test handling of help/info queries."""
    result = parse_accounting_command("What is a trial balance?")

    assert result["action"] == "chat"
    assert "response" in result
    assert len(result["response"]) > 0
    print("✓ Help query test passed")
    return result


def demo_all_commands():
    """Run demonstration of all command types."""
    print("\n" + "=" * 70)
    print("TALLY AI COMMAND PARSER - DEMONSTRATION")
    print("=" * 70)

    test_cases = [
        ("Sales Voucher", "Create sales voucher for Acme Corp, $5000"),
        ("Purchase Voucher", "Record purchase of inventory from XYZ Ltd for $3000"),
        ("Payment Voucher", "Pay rent $1500"),
        ("Receipt Voucher", "Received $4000 from customer John Doe"),
        ("Ledger Query", "Show me Cash ledger"),
        ("Trial Balance", "Display trial balance"),
        ("P&L Report", "Show profit and loss statement"),
        ("GST Transaction", "Create sales invoice for ABC Inc $10000 with 18% GST"),
        ("Journal Entry", "Record depreciation expense $500"),
        ("Help Query", "How do I record a bank transfer?"),
        ("Multi-line Voucher", "Create sales voucher: Party is TechCorp, amount $7500, product is software license, payment terms 30 days"),
    ]

    for title, command in test_cases:
        print(f"\n{'─' * 70}")
        print(f"Test: {title}")
        print(f"{'─' * 70}")
        print(f"Command: {command}\n")

        result = parse_accounting_command(command)

        print("Parsed Result:")
        print(f"  Action: {result.get('action')}")
        print(f"  Entity: {result.get('entity')}")
        print(f"  Data: {json.dumps(result.get('data', {}), indent=4)}")
        print(f"\nResponse: {result.get('response')}\n")


if __name__ == "__main__":
    print("Running AI Parser Tests...\n")

    # Run unit tests
    try:
        test_sales_voucher_parsing()
        test_ledger_query()
        test_trial_balance()
        test_payment_voucher()
        test_context_awareness()
        test_help_query()

        print("\n" + "=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)

        # Run demo
        print("\nRunning full demonstration...\n")
        demo_all_commands()

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Note: Ensure ANTHROPIC_API_KEY is set in .env file")
        sys.exit(1)
