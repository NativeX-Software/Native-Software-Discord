"""Anthropic Claude provider."""
from __future__ import annotations

import aiohttp

from .base import PromptRequest, Provider, ProviderError, ProviderResponse


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str, version: str = "2023-06-01") -> None:
        self.api_key = api_key
        self.version = version
        self.base_url = "https://api.anthropic.com"

    async def complete(self, request: PromptRequest) -> ProviderResponse:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
            "content-type": "application/json",
        }
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                data = await response.json()
                if response.status >= 400:
                    message = data.get("error", {}).get("message", response.reason)
                    raise ProviderError(f"Anthropic error {response.status}: {message}")
        content = data.get("content", [])
        text = "".join(part.get("text", "") for part in content)
        usage = data.get("usage", {})
        return ProviderResponse(text=text, raw=data, usage=usage)
