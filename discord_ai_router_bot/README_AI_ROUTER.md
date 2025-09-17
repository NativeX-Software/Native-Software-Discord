# Native Software AI Router Bot

This bot exposes a unified `/ai` slash command that routes prompts to OpenAI,
Anthropic, Google Gemini, or Grok. It applies role-specific system prompts, can
create follow-up threads, and supports ephemeral responses for sensitive
queries.

## Features

- Provider abstraction with pluggable backends (`openai`, `anthropic`, `gemini`,
  `grok`).
- Role prompts defined in `prompts.json` for personas such as engineering,
  product, ops, exec, design, and research.
- `/ai` command options:
  - `provider` – provider to call (default configurable via `.env`).
  - `model` – provider-specific model name.
  - `role` – persona used to shape the system prompt.
  - `prompt` – user text.
  - `temp` – temperature (0.0–1.0).
  - `max_tokens` – completion budget.
  - `thread` – create a follow-up thread with the response.
  - `public` – reply ephemerally by default to reduce channel noise.
- Channel-scoped rate limiter (5 requests per 60 seconds by default).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in tokens
python ai_router.py
```

Required environment variables:

- `DISCORD_BOT_TOKEN`
- Provider keys for the services you intend to enable (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROK_API_KEY`, `GROK_BASE_URL`).
- `DEFAULT_PROVIDER` and `DEFAULT_MODEL` (optional overrides).
- `ENABLE_MESSAGE_CONTENT=1` if you plan to summarise existing channel messages
  (requires enabling the privileged intent in the Discord developer portal).

## Deployment Tips

- Run under systemd or Docker with outbound internet access to provider APIs.
- Scope the bot to specific `#ai-*` channels using Discord permissions.
- Adjust rate limits or add billing guards in `ai_router.py` to align with your
  spend policies.
- Rotate all API keys during handover and store them in your secret manager.
- A Dockerfile is provided. The top-level `docker-compose.yml` runs this bot
  alongside the ops bot and Watchtower:

  ```bash
  docker compose build ai_router_bot
  docker compose up -d ai_router_bot
  ```

  Ensure `discord_ai_router_bot/.env` contains the provider keys before bringing
  the container online. The compose stack mounts `.env` read-only and
  `prompts.json` so persona updates can be made without rebuilding.

## Testing Checklist

- Invoke `/ai` for each enabled provider and confirm responses.
- Toggle the `public` flag to ensure ephemeral vs. public replies behave as
  expected.
- Enable `thread:true` to verify that threads are created only when the response
  is public.
- Inspect logs for provider latency and potential errors.
