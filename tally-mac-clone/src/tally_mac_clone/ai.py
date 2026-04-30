"""
AI-powered accounting command parser using multiple LLM providers.

Parses natural language commands into structured Tally accounting operations.
Supports Azure-based Claude, Grok, OpenAI via provider abstraction.
"""

import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .llm_providers import get_provider

# Load environment variables
load_dotenv()

# Initialize LLM provider (Azure-based by default)
llm_provider = get_provider()

# System prompt for Tally accounting context
TALLY_SYSTEM_PROMPT = """You are an AI assistant specialized in Tally accounting software. You parse natural language commands into structured operations.

# Tally Data Model

## Voucher Types
- Sales: Revenue transactions (Dr: Party/Cash, Cr: Sales)
- Purchase: Expense transactions (Dr: Purchase, Cr: Party/Cash)
- Payment: Cash/Bank outflow (Dr: Expense/Party, Cr: Cash/Bank)
- Receipt: Cash/Bank inflow (Dr: Cash/Bank, Cr: Income/Party)
- Journal: General entries (Dr: Account, Cr: Account)
- Contra: Cash/Bank transfers (Dr: Cash/Bank, Cr: Cash/Bank)

## Ledger Accounts
- Assets: Cash, Bank, Debtors, Stock
- Liabilities: Creditors, Loans
- Income: Sales, Interest Income
- Expenses: Purchase, Rent, Salaries
- Capital: Owner's equity

## Reports
- Trial Balance: All ledger balances (Dr/Cr totals must match)
- Profit & Loss: Income - Expenses
- Balance Sheet: Assets = Liabilities + Capital
- Ledger: Transaction history for specific account

# Command Parsing

Parse user commands into JSON with this structure:

{
  "action": "<action_type>",
  "entity": "<entity_type>",
  "data": {<extracted_data>},
  "response": "<natural_language_response>"
}

## Action Types
- create_voucher: Create accounting entry
- show_ledger: Display account transactions
- show_trial_balance: Display trial balance
- show_profit_loss: Display P&L statement
- show_balance_sheet: Display balance sheet
- chat: General conversation/help

## Entity Types
- voucher: For create_voucher
- ledger: For show_ledger
- report: For reports (trial_balance, profit_loss, balance_sheet)
- conversation: For chat

# Examples

USER: "Create sales voucher for Acme Corp, $5000"
ASSISTANT: {
  "action": "create_voucher",
  "entity": "voucher",
  "data": {
    "voucher_type": "sales",
    "party": "Acme Corp",
    "amount": 5000,
    "currency": "USD",
    "date": null,
    "narration": "Sales to Acme Corp",
    "entries": [
      {"account": "Acme Corp", "debit": 5000, "credit": 0},
      {"account": "Sales", "debit": 0, "credit": 5000}
    ]
  },
  "response": "Creating sales voucher for Acme Corp worth $5000. Debiting Acme Corp (debtor) and crediting Sales account."
}

USER: "Show ledger for Cash account"
ASSISTANT: {
  "action": "show_ledger",
  "entity": "ledger",
  "data": {
    "account": "Cash",
    "from_date": null,
    "to_date": null
  },
  "response": "Displaying Cash ledger with all transactions."
}

USER: "Generate trial balance"
ASSISTANT: {
  "action": "show_trial_balance",
  "entity": "report",
  "data": {
    "as_of_date": null
  },
  "response": "Generating trial balance report with all ledger balances."
}

USER: "Record payment of $2000 to supplier ABC Ltd"
ASSISTANT: {
  "action": "create_voucher",
  "entity": "voucher",
  "data": {
    "voucher_type": "payment",
    "party": "ABC Ltd",
    "amount": 2000,
    "currency": "USD",
    "date": null,
    "narration": "Payment to ABC Ltd",
    "entries": [
      {"account": "ABC Ltd", "debit": 2000, "credit": 0},
      {"account": "Cash", "debit": 0, "credit": 2000}
    ]
  },
  "response": "Recording payment of $2000 to ABC Ltd. Debiting ABC Ltd (reducing liability) and crediting Cash."
}

USER: "What is trial balance?"
ASSISTANT: {
  "action": "chat",
  "entity": "conversation",
  "data": {},
  "response": "Trial Balance is a statement that lists all ledger accounts with their debit and credit balances. It ensures that total debits equal total credits, verifying the arithmetic accuracy of your books. It's typically generated at the end of an accounting period before preparing financial statements."
}

# Accounting Rules

1. **Double Entry**: Every transaction has equal debits and credits
2. **Dr/Cr Conventions**:
   - Assets/Expenses increase on Debit side
   - Liabilities/Income increase on Credit side
3. **GST**: If mentioned, add tax components to entries
4. **Date**: Use current date if not specified
5. **Currency**: Default to USD if not specified

# Instructions

1. Analyze the user's command carefully
2. Identify the accounting operation they want to perform
3. Extract all relevant data (amounts, parties, accounts, dates)
4. Return valid JSON matching the schema above
5. Provide helpful natural language response
6. For ambiguous commands, make reasonable assumptions and mention them in response
7. For invalid/unclear commands, return action "chat" with helpful guidance

Always return ONLY valid JSON, no additional text.
"""


def parse_accounting_command(user_message: str, conversation_history: Optional[list] = None) -> Dict[str, Any]:
    """
    Parse natural language accounting command using Claude.

    Args:
        user_message: User's natural language command
        conversation_history: Optional list of previous messages for context

    Returns:
        Structured dict with action, entity, data, and response
    """
    messages = []

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        # Call LLM via provider abstraction
        response_text = llm_provider.create_completion(
            system_prompt=TALLY_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=2048
        )

        # Parse JSON response
        try:
            parsed = json.loads(response_text)
            return parsed
        except json.JSONDecodeError:
            # If LLM didn't return valid JSON, wrap it
            return {
                "action": "chat",
                "entity": "conversation",
                "data": {},
                "response": response_text
            }

    except Exception as e:
        # Handle API errors gracefully
        return {
            "action": "error",
            "entity": "system",
            "data": {"error": str(e)},
            "response": f"Error processing command: {str(e)}"
        }


def get_context_aware_response(user_message: str, recent_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse command with awareness of recent accounting context.

    Args:
        user_message: User's command
        recent_context: Dict with recent vouchers, ledgers, or operations

    Returns:
        Structured response dict
    """
    conversation_history = []

    # Build context from recent operations
    if recent_context:
        context_summary = "Recent context:\n"

        if "last_voucher" in recent_context:
            voucher = recent_context["last_voucher"]
            context_summary += f"- Last voucher: {voucher.get('type')} for {voucher.get('party')} amount {voucher.get('amount')}\n"

        if "last_ledger" in recent_context:
            ledger = recent_context["last_ledger"]
            context_summary += f"- Last viewed ledger: {ledger.get('account')}\n"

        if "active_party" in recent_context:
            context_summary += f"- Active party: {recent_context['active_party']}\n"

        # Add context as system-like message
        conversation_history.append({
            "role": "user",
            "content": f"Context: {context_summary}"
        })
        conversation_history.append({
            "role": "assistant",
            "content": "I understand the context. Ready for your next command."
        })

    return parse_accounting_command(user_message, conversation_history)


# Example usage and testing
if __name__ == "__main__":
    # Test commands
    test_commands = [
        "Create sales voucher for Acme Corp, $5000",
        "Show ledger for Cash account",
        "Generate trial balance",
        "Record payment of $2000 to supplier ABC Ltd",
        "What is the difference between receipt and payment voucher?",
        "Create purchase voucher for office supplies from XYZ Ltd for $1500 with 10% GST"
    ]

    print("Testing Tally AI Command Parser\n")
    print("=" * 60)

    for command in test_commands:
        print(f"\nUser: {command}")
        result = parse_accounting_command(command)
        print(f"\nParsed Response:")
        print(json.dumps(result, indent=2))
        print("\n" + "-" * 60)
