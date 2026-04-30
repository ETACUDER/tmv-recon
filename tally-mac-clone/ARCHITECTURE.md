# LLM Provider Architecture

## System Flow

```
User Command
    ↓
ai.parse_accounting_command()
    ↓
llm_provider.create_completion()
    ↓
┌─────────────────────────────────────┐
│      Provider Selection Layer       │
│  (based on LLM_PROVIDER env var)    │
└─────────────────────────────────────┘
    ↓
┌──────────┬──────────┬──────────┬──────────┐
│  Azure   │  Azure   │  Azure   │  Direct  │
│  Claude  │   Grok   │  OpenAI  │  Claude  │
└──────────┴──────────┴──────────┴──────────┘
    ↓           ↓           ↓           ↓
┌────────────────────────────────────────────┐
│         Azure OpenAI Service               │
│   (or Anthropic API for direct-claude)     │
└────────────────────────────────────────────┘
    ↓
LLM Response (JSON)
    ↓
Parse & Validate
    ↓
Structured Output
```

## Class Hierarchy

```
LLMProvider (ABC)
│
├── AzureClaudeProvider
│   └── Uses: Azure OpenAI SDK
│       Model: Claude Sonnet 4.5
│
├── AzureGrokProvider
│   └── Uses: Azure OpenAI SDK
│       Model: Grok
│
├── AzureOpenAIProvider
│   └── Uses: Azure OpenAI SDK
│       Model: GPT-4
│
└── DirectClaudeProvider
    └── Uses: Anthropic SDK
        Model: Claude Sonnet 4.6
```

## Message Flow

### Input
```python
system_prompt = "You are Tally accounting expert..."
messages = [
    {"role": "user", "content": "Create sales voucher for Acme, $5000"}
]
```

### Provider Processing

**Azure Providers** (Claude, Grok, OpenAI)
```python
formatted = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]
→ Azure OpenAI API
```

**Direct Claude**
```python
# System separate from messages
system = system_prompt
messages = [{"role": "user", "content": user_message}]
→ Anthropic API
```

### Output
```json
{
  "action": "create_voucher",
  "entity": "voucher",
  "data": {
    "voucher_type": "sales",
    "party": "Acme Corp",
    "amount": 5000,
    "entries": [...]
  },
  "response": "Creating sales voucher..."
}
```

## Configuration Mapping

```
Environment Variable          Provider Instance
─────────────────────────── → ─────────────────────────
LLM_PROVIDER=azure-claude   → AzureClaudeProvider()
LLM_PROVIDER=azure-grok     → AzureGrokProvider()
LLM_PROVIDER=azure-openai   → AzureOpenAIProvider()
LLM_PROVIDER=direct-claude  → DirectClaudeProvider()
(default/empty)             → AzureClaudeProvider()
```

## Shared Components

### System Prompt
**TALLY_SYSTEM_PROMPT** - Same across all providers
- Tally domain knowledge
- Voucher types
- Ledger accounts
- Accounting rules
- JSON output schema

### Error Handling
```python
try:
    response = llm_provider.create_completion(...)
    parsed = json.loads(response)
except json.JSONDecodeError:
    # Wrap non-JSON in chat response
except Exception as e:
    # Return error response
```

### Context Support
```python
conversation_history = [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}  # current
]
```

## Deployment Architecture

```
Application Layer
├── FastAPI routes
├── Business logic
└── ai.py (parse_accounting_command)
    ↓
Provider Layer
├── llm_providers.py
│   ├── get_provider()
│   └── Provider classes
    ↓
Configuration Layer
├── .env
│   ├── LLM_PROVIDER
│   ├── AZURE_ENDPOINT
│   ├── AZURE_API_KEY
│   └── AZURE_DEPLOYMENT_NAME
    ↓
External Services
├── Azure OpenAI (Claude, Grok, GPT-4)
└── Anthropic API (direct-claude only)
```

## Provider Comparison

| Aspect | Azure Providers | Direct Claude |
|--------|----------------|---------------|
| SDK | `openai` | `anthropic` |
| Auth | Azure API Key | Anthropic API Key |
| Endpoint | Azure OpenAI | api.anthropic.com |
| System Prompt | In messages array | Separate parameter |
| Format | OpenAI chat format | Anthropic format |
| Models | Claude/Grok/GPT-4 | Claude only |

## Extensibility

Add new provider:

1. Create provider class
```python
class AzureNewModelProvider(LLMProvider):
    def create_completion(self, system_prompt, messages, max_tokens):
        # Implementation
        pass
```

2. Update `get_provider()`
```python
elif provider_name == "new-model":
    return AzureNewModelProvider()
```

3. Update docs
- LLM_PROVIDERS.md
- .env.example
- PROVIDER_QUICK_REF.md

No changes to `ai.py` needed - abstraction handles it.

## Testing Strategy

```
Unit Tests
├── Test each provider independently
├── Mock Azure/Anthropic APIs
└── Verify output format

Integration Tests
├── Test provider switching
├── Test conversation history
└── Test error scenarios

End-to-End Tests
├── Real API calls (dev env)
├── All test commands
└── Performance metrics
```

## Performance Considerations

**Provider Selection Overhead**
- Minimal - done once at startup
- `get_provider()` called during import

**Runtime Overhead**
- None - direct API calls
- Same as original implementation

**Scalability**
- Stateless providers
- Thread-safe
- Can instantiate per-request if needed

## Security

**API Keys**
- Never committed to git
- Loaded from .env only
- Azure Key Vault recommended for prod

**Provider Isolation**
- Each provider independent
- Failures contained
- No shared state

## Monitoring

Log provider selection:
```python
provider = get_provider()
logger.info(f"Using provider: {provider.__class__.__name__}")
```

Track per-provider metrics:
- Response times
- Error rates
- Token usage
- Cost
