# Migration Guide: Azure LLM Providers

## Overview
Refactored `ai.py` to support multiple LLM providers via Azure OpenAI Service.

## Changes Made

### 1. New Files
- `src/tally_mac_clone/llm_providers.py` - Provider abstraction layer
- `LLM_PROVIDERS.md` - Provider documentation
- `MIGRATION_GUIDE.md` - This file

### 2. Modified Files
- `src/tally_mac_clone/ai.py` - Uses provider abstraction
- `.env.example` - Azure configuration examples
- `pyproject.toml` - Added `openai` dependency

### 3. Dependencies
```bash
pip install openai>=1.0.0
```

## Breaking Changes

### Environment Variables
Old:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

New (Azure default):
```env
LLM_PROVIDER=azure-claude
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-azure-key
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

Legacy support (direct Anthropic):
```env
LLM_PROVIDER=direct-claude
ANTHROPIC_API_KEY=sk-ant-...
```

## Migration Steps

### Option 1: Switch to Azure (Recommended)

1. Get Azure credentials from Azure Portal
2. Update `.env`:
```env
LLM_PROVIDER=azure-claude
AZURE_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_API_KEY=your-azure-api-key
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

3. Install dependencies:
```bash
pip install -r requirements.txt  # or pip install openai>=1.0.0
```

4. Restart application

### Option 2: Keep Direct Anthropic (Temporary)

1. Add to `.env`:
```env
LLM_PROVIDER=direct-claude
# Keep existing ANTHROPIC_API_KEY
```

2. No code changes needed
3. Plan migration to Azure

## Code Changes

### Before
```python
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=TALLY_SYSTEM_PROMPT,
    messages=messages
)
```

### After
```python
from .llm_providers import get_provider
llm_provider = get_provider()

response_text = llm_provider.create_completion(
    system_prompt=TALLY_SYSTEM_PROMPT,
    messages=messages,
    max_tokens=2048
)
```

## Testing

Verify provider working:

```python
python -c "
from tally_mac_clone.ai import parse_accounting_command
result = parse_accounting_command('Create sales voucher for Test Corp, $100')
print(result)
"
```

## Switching Providers

Edit `.env` and change `LLM_PROVIDER`:

```bash
# Use Grok
LLM_PROVIDER=azure-grok
AZURE_DEPLOYMENT_NAME=grok

# Use GPT-4
LLM_PROVIDER=azure-openai
AZURE_DEPLOYMENT_NAME=gpt-4

# Use Claude
LLM_PROVIDER=azure-claude
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

Restart after changes.

## Rollback

Revert to direct Anthropic:

```env
LLM_PROVIDER=direct-claude
ANTHROPIC_API_KEY=sk-ant-...
```

No other changes needed - backward compatible.

## Provider Features

All providers support:
- Same system prompt (Tally domain knowledge)
- Same JSON output format
- Same error handling
- Same conversation history

Differences:
- Model capabilities vary
- Response speed varies
- Cost varies

See `LLM_PROVIDERS.md` for details.
