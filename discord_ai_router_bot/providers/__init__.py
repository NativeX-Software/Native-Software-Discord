"""Provider registry for the AI router bot."""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from .base import PromptRequest, Provider, ProviderError, ProviderResponse
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .grok_provider import GrokProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        key = provider.name.lower()
        self._providers[key] = provider

    def get(self, name: str) -> Optional[Provider]:
        return self._providers.get(name.lower())

    def names(self) -> Iterable[str]:
        return self._providers.keys()

    def __contains__(self, item: str) -> bool:
        return item.lower() in self._providers


__all__ = [
    "PromptRequest",
    "Provider",
    "ProviderError",
    "ProviderResponse",
    "ProviderRegistry",
    "AnthropicProvider",
    "GeminiProvider",
    "GrokProvider",
    "OpenAIProvider",
]
