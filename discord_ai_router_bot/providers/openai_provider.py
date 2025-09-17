"""OpenAI provider implementation."""
from __future__ import annotations

import aiohttp

from .base import PromptRequest, Provider, ProviderError, ProviderResponse


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com").rstrip("/")

    async def complete(self, request: PromptRequest) -> ProviderResponse:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                data = await response.json()
                if response.status >= 400:
                    message = data.get("error", {}).get("message", response.reason)
                    raise ProviderError(f"OpenAI error {response.status}: {message}")
        choice = data["choices"][0]["message"]
        text = choice.get("content", "")
        usage = data.get("usage", {})
        return ProviderResponse(text=text, raw=data, usage=usage)
