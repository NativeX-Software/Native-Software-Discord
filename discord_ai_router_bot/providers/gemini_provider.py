"""Google Gemini provider."""
from __future__ import annotations

import aiohttp

from .base import PromptRequest, Provider, ProviderError, ProviderResponse


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")

    async def complete(self, request: PromptRequest) -> ProviderResponse:
        url = f"{self.base_url}/v1beta/models/{request.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": request.prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                if response.status >= 400:
                    message = data.get("error", {}).get("message", response.reason)
                    raise ProviderError(f"Gemini error {response.status}: {message}")
        candidates = data.get("candidates", [])
        if not candidates:
            raise ProviderError("Gemini response did not include candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        usage = data.get("usageMetadata", {})
        return ProviderResponse(text=text, raw=data, usage=usage)
