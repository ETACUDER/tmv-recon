# Provider Quick Reference

## Switch Models in 3 Steps

### 1. Edit `.env`
```bash
LLM_PROVIDER=azure-claude  # or azure-grok, azure-openai
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5  # or grok, gpt-4
```

### 2. Verify Config
```bash
cat .env | grep -E "LLM_PROVIDER|AZURE"
```

### 3. Restart App
```bash
# Restart your FastAPI server or Python process
```

## Provider Values

| Provider | LLM_PROVIDER Value | Deployment Name |
|----------|-------------------|-----------------|
| Claude Sonnet 4.5 | `azure-claude` | `claude-sonnet-4-5` |
| Grok | `azure-grok` | `grok` |
| GPT-4 | `azure-openai` | `gpt-4` |
| Direct Claude | `direct-claude` | N/A |

## Required Env Vars

### Azure Providers (claude, grok, openai)
```env
LLM_PROVIDER=azure-claude
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-azure-key
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

### Direct Anthropic (legacy)
```env
LLM_PROVIDER=direct-claude
ANTHROPIC_API_KEY=sk-ant-...
```

## Test Provider
```bash
python test_providers.py
```

## Common Issues

**Error: "Deployment not found"**
- Check `AZURE_DEPLOYMENT_NAME` matches Azure deployment
- Verify deployment exists in Azure Portal

**Error: "Invalid API key"**
- Check `AZURE_API_KEY` is correct
- Verify key has access to deployment

**Error: "Import openai failed"**
- Run: `pip install openai>=1.0.0`

## Code Usage

```python
from tally_mac_clone.ai import parse_accounting_command

# Provider loaded automatically from env
result = parse_accounting_command("Create sales voucher for Corp X, $1000")
```

No code changes needed to switch providers.
