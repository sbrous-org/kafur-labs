from abc import ABC, abstractmethod
from typing import Dict, Any
import json


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Invoke the LLM with a prompt.

        Args:
            system_prompt: System context/instructions
            user_message: User query
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature. Use near-0 for deterministic
                classification/routing, higher (0.6-0.8) for natural-language synthesis.

        Returns:
            String response from the LLM
        """
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider (supports multiple models via single API)."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = model

    def invoke(self, system_prompt: str, user_message: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content


def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create LLM provider based on config.

    Args:
        config: Dict with 'provider' key and provider-specific settings

    Returns:
        LLMProvider instance

    Example:
        config = {
            "provider": "openrouter",
            "api_key": "sk-or-v1-...",
            "model": "openai/gpt-4o"
        }
        provider = create_llm_provider(config)
    """
    provider_type = config.get("provider", "claude").lower()
    api_key = config.get("api_key")

    if not api_key:
        raise ValueError(f"API key required for {provider_type} provider")

    if provider_type == "claude":
        model = config.get("model", "claude-3-5-haiku-20241022")
        return ClaudeProvider(api_key=api_key, model=model)

    elif provider_type == "openai":
        model = config.get("model", "gpt-3.5-turbo")
        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_type == "openrouter":
        model = config.get("model", "openai/gpt-4o")
        return OpenRouterProvider(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_type}")
