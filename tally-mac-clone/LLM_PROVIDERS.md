# LLM Provider Configuration

Multi-provider LLM abstraction for Tally accounting command parser. All models run via Azure OpenAI Service.

## Supported Providers

### 1. Azure Claude (Default)
Claude Sonnet 4.5 via Azure OpenAI Service

```env
LLM_PROVIDER=azure-claude
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-azure-key
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

### 2. Azure Grok
Grok via Azure

```env
LLM_PROVIDER=azure-grok
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-azure-key
AZURE_DEPLOYMENT_NAME=grok
```

### 3. Azure OpenAI
GPT-4 via Azure

```env
LLM_PROVIDER=azure-openai
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_API_KEY=your-azure-key
AZURE_DEPLOYMENT_NAME=gpt-4
```

### 4. Direct Claude (Legacy)
Direct Anthropic API (fallback)

```env
LLM_PROVIDER=direct-claude
ANTHROPIC_API_KEY=your-anthropic-key
```

## Quick Switch

Change provider by updating `.env`:

```bash
# Switch to Grok
LLM_PROVIDER=azure-grok

# Switch to GPT-4
LLM_PROVIDER=azure-openai

# Switch to Claude
LLM_PROVIDER=azure-claude
```

Restart application after changing provider.

## Architecture

### Provider Abstraction
All providers implement `LLMProvider` interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        pass
```

### Unified Parsing
Same system prompt and structured output across all providers:
- Tally accounting domain knowledge
- JSON structured output
- Double-entry bookkeeping rules
- Voucher type classification

### Error Handling
Consistent error handling across providers:
- API errors wrapped in error response
- JSON parse failures fallback to chat
- Same error format regardless of provider

## Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Configure Azure credentials:
```env
AZURE_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_API_KEY=abc123...
```

3. Set deployment name matching your Azure deployment:
```env
AZURE_DEPLOYMENT_NAME=claude-sonnet-4-5
```

4. Choose provider:
```env
LLM_PROVIDER=azure-claude
```

## Azure Deployment Names

Match deployment name in Azure:
- `claude-sonnet-4-5` for Claude
- `grok` for Grok
- `gpt-4` or `gpt-4-turbo` for OpenAI

## Testing

Test provider switch:

```python
from tally_mac_clone.ai import parse_accounting_command

result = parse_accounting_command("Create sales voucher for Acme Corp, $5000")
print(result)
```

Provider loaded automatically from `LLM_PROVIDER` env var.

## Performance Notes

- **Claude**: Best for complex accounting logic, structured output
- **Grok**: Fast, good for simple transactions
- **GPT-4**: Balanced performance, wide knowledge

All models use same prompt engineering for consistency.
