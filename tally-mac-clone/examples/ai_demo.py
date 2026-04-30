#!/usr/bin/env python3
"""
Interactive demo of AI command parsing.

Usage: python examples/ai_demo.py
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tally_mac_clone.ai import parse_accounting_command, get_context_aware_response


def print_result(result):
    """Pretty print parsing result."""
    print("\n" + "─" * 60)
    print(f"Action: {result['action']}")
    print(f"Entity: {result['entity']}")

    if result.get('data'):
        print("\nExtracted Data:")
        print(json.dumps(result['data'], indent=2))

    print(f"\nAI Response:")
    print(f"  {result['response']}")
    print("─" * 60)


def interactive_demo():
    """Run interactive command demo."""
    print("=" * 60)
    print("TALLY AI COMMAND PARSER - Interactive Demo")
    print("=" * 60)
    print("\nType accounting commands in natural language.")
    print("Type 'quit' or 'exit' to stop.\n")

    context = {}

    while True:
        try:
            command = input("\n> ").strip()

            if command.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if not command:
                continue

            # Parse with context
            result = get_context_aware_response(command, context)

            # Print result
            print_result(result)

            # Update context for next command
            if result['action'] == 'create_voucher':
                context['last_voucher'] = result['data']
                if 'party' in result['data']:
                    context['active_party'] = result['data']['party']

            elif result['action'] == 'show_ledger':
                context['last_ledger'] = result['data']
                if 'account' in result['data']:
                    context['active_account'] = result['data']['account']

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


def preset_demo():
    """Run preset command examples."""
    print("=" * 60)
    print("TALLY AI COMMAND PARSER - Preset Examples")
    print("=" * 60)

    examples = [
        # Voucher creation
        "Create sales voucher for Acme Corp, $5000",
        "Record purchase of office supplies from XYZ Ltd for $1500",
        "Pay salary to John Doe $3000",
        "Received payment $2500 from customer ABC Inc",

        # With GST
        "Create sales invoice for TechCorp $10000 with 18% GST",

        # Ledger queries
        "Show ledger for Cash account",
        "Display Acme Corp ledger",

        # Reports
        "Generate trial balance",
        "Show profit and loss",

        # Help
        "What is the difference between payment and contra voucher?",

        # Context-aware (after first command)
        "Add another $500 to Acme Corp",
    ]

    context = {}

    for i, command in enumerate(examples, 1):
        print(f"\n[{i}/{len(examples)}] Command: {command}")

        result = get_context_aware_response(command, context)
        print_result(result)

        # Update context
        if result['action'] == 'create_voucher':
            context['last_voucher'] = result['data']
            if 'party' in result['data']:
                context['active_party'] = result['data']['party']

        input("\nPress Enter for next example...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Command Parser Demo")
    parser.add_argument(
        '--mode',
        choices=['interactive', 'preset'],
        default='preset',
        help="Demo mode: interactive or preset examples"
    )

    args = parser.parse_args()

    try:
        if args.mode == 'interactive':
            interactive_demo()
        else:
            preset_demo()

    except KeyboardInterrupt:
        print("\n\nDemo stopped.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure ANTHROPIC_API_KEY is set in .env file")
        sys.exit(1)
