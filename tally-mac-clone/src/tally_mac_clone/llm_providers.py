"""
LLM provider abstraction for Azure-based models.
Supports Claude, Grok, and OpenAI via Azure.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    """Base interface for LLM providers."""

    @abstractmethod
    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        """
        Create completion with system prompt and messages.

        Args:
            system_prompt: System instruction
            messages: List of {"role": "user"|"assistant", "content": "..."}
            max_tokens: Max response tokens

        Returns:
            Response text
        """
        pass


class AzureClaudeProvider(LLMProvider):
    """Claude Sonnet 4.5 via Azure OpenAI Service."""

    def __init__(self):
        from openai import AzureOpenAI

        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version="2024-10-01-preview",
            azure_endpoint=os.getenv("AZURE_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "claude-sonnet-4-5")

    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        # Azure OpenAI format: system message first
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content.strip()


class AzureGrokProvider(LLMProvider):
    """Grok via Azure."""

    def __init__(self):
        from openai import AzureOpenAI

        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version="2024-10-01-preview",
            azure_endpoint=os.getenv("AZURE_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "grok")

    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content.strip()


class AzureOpenAIProvider(LLMProvider):
    """OpenAI GPT-4 via Azure."""

    def __init__(self):
        from openai import AzureOpenAI

        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_API_KEY"),
            api_version="2024-10-01-preview",
            azure_endpoint=os.getenv("AZURE_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4")

    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=formatted_messages,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content.strip()


class AzureFoundryProvider(LLMProvider):
    """Claude via Azure Foundry (uses Anthropic SDK with Foundry env vars)."""

    def __init__(self):
        from anthropic import Anthropic

        # Azure Foundry: standard Anthropic client with Foundry API key
        # The Foundry routing is handled by env vars:
        # CLAUDE_CODE_USE_FOUNDRY=1
        # ANTHROPIC_FOUNDRY_RESOURCE=atmen-mg7nh9ke-eastus2
        # ANTHROPIC_FOUNDRY_API_KEY=...

        api_key = os.getenv("ANTHROPIC_FOUNDRY_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

        # If using Foundry, set base URL to Azure endpoint
        if os.getenv("CLAUDE_CODE_USE_FOUNDRY") == "1":
            resource = os.getenv("ANTHROPIC_FOUNDRY_RESOURCE", "atmen-mg7nh9ke-eastus2")
            base_url = f"https://{resource}.openai.azure.com/openai/deployments/claude-sonnet-4-5"
            self.client = Anthropic(
                api_key=api_key,
                base_url=base_url
            )
        else:
            self.client = Anthropic(api_key=api_key)

        self.model = os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-5")

    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text.strip()


class DirectClaudeProvider(LLMProvider):
    """Direct Claude via Anthropic API (fallback)."""

    def __init__(self):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def create_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text.strip()


def get_provider() -> LLMProvider:
    """
    Get LLM provider based on environment configuration.

    Reads LLM_PROVIDER env var:
    - "azure-foundry": Claude Sonnet 4.5 via Azure Foundry (Anthropic SDK)
    - "azure-claude" or "claude": Claude Sonnet 4.5 via Azure OpenAI
    - "azure-grok" or "grok": Grok via Azure
    - "azure-openai" or "openai" or "gpt4": GPT-4 via Azure
    - "direct-claude": Direct Anthropic API (legacy)

    Returns:
        Configured LLMProvider instance
    """
    provider_name = os.getenv("LLM_PROVIDER", "azure-foundry").lower()

    if provider_name == "azure-foundry":
        return AzureFoundryProvider()
    elif provider_name in ["azure-claude", "claude"]:
        return AzureClaudeProvider()
    elif provider_name in ["azure-grok", "grok"]:
        return AzureGrokProvider()
    elif provider_name in ["azure-openai", "openai", "gpt4"]:
        return AzureOpenAIProvider()
    elif provider_name == "direct-claude":
        return DirectClaudeProvider()
    else:
        # Default to Azure Foundry
        return AzureFoundryProvider()
