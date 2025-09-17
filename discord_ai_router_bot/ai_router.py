"""AI router bot entrypoint."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from providers import (
    AnthropicProvider,
    GeminiProvider,
    GrokProvider,
    OpenAIProvider,
    PromptRequest,
    ProviderError,
    ProviderRegistry,
)

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_PATH = BASE_DIR / "prompts.json"
DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_WINDOW = 60

load_dotenv()
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
logger = logging.getLogger("ai-router")


class SimpleRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._events: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            events = [stamp for stamp in self._events.get(key, []) if now - stamp < self.window]
            if len(events) >= self.limit:
                self._events[key] = events
                return False
            events.append(now)
            self._events[key] = events
            return True


def load_prompts() -> Dict[str, str]:
    if not PROMPTS_PATH.exists():
        raise FileNotFoundError(f"Prompts file missing at {PROMPTS_PATH}")
    with PROMPTS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class BotConfig:
    token: str
    guild_id: Optional[int]
    default_provider: Optional[str]
    default_model: str
    rate_limit: int
    rate_window: int
    enable_message_content: bool

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            raise RuntimeError("DISCORD_BOT_TOKEN is required")
        guild_id = os.getenv("DISCORD_GUILD_ID")
        default_provider = os.getenv("DEFAULT_PROVIDER")
        default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        rate_limit = int(os.getenv("AI_RATE_LIMIT", DEFAULT_RATE_LIMIT))
        rate_window = int(os.getenv("AI_RATE_WINDOW", DEFAULT_RATE_WINDOW))
        enable_message_content = os.getenv("ENABLE_MESSAGE_CONTENT", "0") == "1"
        return cls(
            token=token,
            guild_id=int(guild_id) if guild_id else None,
            default_provider=default_provider.lower() if default_provider else None,
            default_model=default_model,
            rate_limit=rate_limit,
            rate_window=rate_window,
            enable_message_content=enable_message_content,
        )


def build_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        registry.register(OpenAIProvider(openai_key, os.getenv("OPENAI_BASE_URL")))
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        registry.register(AnthropicProvider(anthropic_key, os.getenv("ANTHROPIC_VERSION", "2023-06-01")))
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        registry.register(GeminiProvider(gemini_key, os.getenv("GEMINI_BASE_URL")))
    grok_key = os.getenv("GROK_API_KEY")
    grok_url = os.getenv("GROK_BASE_URL")
    if grok_key and grok_url:
        registry.register(GrokProvider(grok_key, grok_url))
    return registry


class AIRouterBot(commands.Bot):
    def __init__(self, config: BotConfig, registry: ProviderRegistry, prompts: Dict[str, str]) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        if config.enable_message_content:
            intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        self.registry = registry
        self.prompts = prompts
        self.rate_limiter = SimpleRateLimiter(config.rate_limit, config.rate_window)

    async def setup_hook(self) -> None:  # type: ignore[override]
        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


prompts = load_prompts()
registry = build_registry()
if not any(True for _ in registry.names()):
    raise RuntimeError("No AI providers configured. Set provider API keys in the environment.")
config = BotConfig.from_env()
bot = AIRouterBot(config, registry, prompts)


def resolve_provider(name: Optional[str]) -> Optional[str]:
    if name:
        return name.lower()
    return bot.config.default_provider or next(iter(bot.registry.names()))


def resolve_role(role: Optional[str]) -> str:
    if role and role.lower() in bot.prompts:
        return role.lower()
    return "default"


@app_commands.describe(
    provider="AI provider to target (openai, anthropic, gemini, grok)",
    model="Model identifier for the selected provider",
    role="Persona prompt to apply",
    prompt="User prompt",
    temp="Temperature (0.0 - 1.0)",
    max_tokens="Maximum response tokens",
    thread="Create a follow-up thread with the response",
    public="Set true to send a channel-visible message",
)
@bot.tree.command(name="ai", description="Route prompts to configured AI providers.")
async def ai(
    interaction: discord.Interaction,
    prompt: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    role: Optional[str] = None,
    temp: app_commands.Range[float, 0.0, 1.0] = 0.2,
    max_tokens: app_commands.Range[int, 32, 4000] = 800,
    thread: bool = False,
    public: bool = False,
) -> None:
    provider_name = resolve_provider(provider)
    if not provider_name or provider_name not in bot.registry:
        available = ", ".join(sorted(bot.registry.names()))
        await interaction.response.send_message(
            f"Unknown provider. Available providers: {available}",
            ephemeral=True,
        )
        return
    role_key = resolve_role(role)
    channel_key = str(interaction.channel_id)
    if not await bot.rate_limiter.check(channel_key):
        await interaction.response.send_message(
            "Channel rate limit exceeded. Try again shortly.",
            ephemeral=True,
        )
        return

    provider_impl = bot.registry.get(provider_name)
    assert provider_impl is not None

    model_name = model or bot.config.default_model
    system_prompt = bot.prompts.get(role_key, bot.prompts.get("default"))
    metadata: Dict[str, Any] = {
        "user_id": interaction.user.id if interaction.user else None,
        "channel_id": interaction.channel_id,
        "role": role_key,
        "provider": provider_name,
    }

    thread_warning = False
    if thread and not public:
        thread = False
        thread_warning = True

    await interaction.response.defer(thinking=True, ephemeral=not public)
    request = PromptRequest(
        prompt=prompt,
        model=model_name,
        temperature=temp,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        metadata=metadata,
    )
    try:
        response = await provider_impl.complete(request)
    except ProviderError as exc:
        logger.exception("Provider error from %s", provider_name)
        await interaction.followup.send(f"Provider error: {exc}", ephemeral=True)
        return
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected provider failure")
        await interaction.followup.send("Unexpected error while contacting the provider.", ephemeral=True)
        return

    text = response.text.strip() or "(empty response)"
    embed = discord.Embed(
        title=f"{provider_name.title()} • {model_name}",
        colour=discord.Colour.dark_teal(),
    )
    embed.add_field(name="Role", value=role_key, inline=True)
    usage = response.usage
    if usage:
        usage_summary = ", ".join(f"{key}: {value}" for key, value in usage.items())
        embed.add_field(name="Usage", value=usage_summary, inline=False)
    if len(text) > 3900:
        truncated = text[:1900] + "…"
        embed.description = truncated
        buffer = io.StringIO(text)
        file = discord.File(buffer, filename="ai-response.txt")
        await interaction.followup.send(embed=embed, file=file, ephemeral=not public)
    else:
        embed.description = text
        await interaction.followup.send(embed=embed, ephemeral=not public)

    if thread and public:
        try:
            origin = await interaction.original_response()
            thread_name = f"AI • {interaction.user.display_name if interaction.user else 'Conversation'}"
            await origin.create_thread(name=thread_name, auto_archive_duration=1440, reason="AI follow-up")
        except Exception as exc:  # pragma: no cover - thread creation best effort
            logger.warning("Failed to create follow-up thread: %s", exc)
    elif thread_warning:
        await interaction.followup.send(
            "Thread creation is only supported for public responses.",
            ephemeral=True,
        )


@ai.autocomplete("provider")
async def provider_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    suggestions = []
    for name in bot.registry.names():
        if current.lower() in name.lower():
            suggestions.append(app_commands.Choice(name=name, value=name))
    return suggestions[:25]


@ai.autocomplete("role")
async def role_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    suggestions = []
    for name in bot.prompts.keys():
        if current.lower() in name.lower():
            suggestions.append(app_commands.Choice(name=name, value=name))
    return suggestions[:25]


async def main() -> None:
    await bot.start(bot.config.token)


if __name__ == "__main__":
    asyncio.run(main())
