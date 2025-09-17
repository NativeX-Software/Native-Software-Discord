"""Provider abstraction for the AI router bot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass
class PromptRequest:
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    system_prompt: Optional[str]
    metadata: Mapping[str, Any]


@dataclass
class ProviderResponse:
    text: str
    raw: Dict[str, Any]
    usage: Dict[str, Any]


class ProviderError(RuntimeError):
    """Raised when a provider request fails."""


class Provider:
    name: str

    async def complete(self, request: PromptRequest) -> ProviderResponse:  # pragma: no cover - interface
        raise NotImplementedError
