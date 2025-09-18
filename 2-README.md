# Discord Hub Starter Guide (New Builders)

This repository sets up a complete Discord workspace for a software delivery team. It includes:

- **A server blueprint** that creates channels, roles, and webhooks.
- **An Ops bot** that runs standups, retros, on-call rotations, and deployment approvals.
- **An AI bot** that responds to `/ai` questions using OpenAI, Anthropic, Gemini, or Grok.

Use the steps below for a quick start. When you need more depth, reference `0-DEVELOPER_MANUAL.md`.

---

## 1. Prerequisites

- A Discord server where you can invite bots.
- Three Discord bot applications in the [Discord Developer Portal](https://discord.com/developers/applications): provisioning, Ops bot, and AI bot.
- API keys for the AI providers you plan to use (OpenAI, Anthropic, Gemini, Grok).
- Python 3.10+ installed. Docker is optional if you prefer containers.

---

## 2. Repository layout

```
/discord_team_hub_blueprint   -> scripts and JSON to provision the Discord server
/discord_slash_bot_plus       -> Ops bot implementation
/discord_ai_router_bot        -> AI router bot implementation
0-DEVELOPER_MANUAL.md         -> full build and handover manual
docker-compose.yml            -> optional Docker setup for both bots
```

Each folder has its own README with additional context.

---

## 3. One-time Python environment setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
```

Keep the virtual environment active while running scripts. Use `deactivate` when finished.

---

## 4. Provision the Discord server

1. Switch to the blueprint folder and install dependencies:
   ```bash
   cd discord_team_hub_blueprint
   pip install -r requirements.txt
   ```
2. Export the provisioning bot token and the target guild ID (replace placeholders):
   ```bash
   export DISCORD_BOT_TOKEN="your-provisioning-bot-token"
   export DISCORD_GUILD_ID="123456789012345678"
   ```
   Windows PowerShell:
   ```powershell
   $env:DISCORD_BOT_TOKEN = "your-token"
   $env:DISCORD_GUILD_ID = "your-guild-id"
   ```
3. Run the provisioning script:
   ```bash
   python create_discord_server.py
   ```

The script creates roles, channels, and webhooks defined in `server_spec.json`. Review `server_state.json` afterward—it stores the IDs needed by the bots. Remove the provisioning bot’s administrator access once setup is complete.

---

## 5. Start the Ops bot

1. Install requirements and create an environment file:
   ```bash
   cd ../discord_slash_bot_plus
   pip install -r requirements.txt
   cp .env.example .env
   ```
2. Edit `.env` with the bot token (and optionally the guild ID).
3. Ensure the `data/` directory remains writable; it stores schedules and on-call details.
4. Launch the bot:
   ```bash
   python bot.py
   ```

### Recommended checks
- `/standup` posts an embed in the current channel.
- `/standup_sched schedule time:09:30 timezone:UTC` updates `data/schedules.json`.
- `/oncall setup role:@On-Call` and `/oncall rotate` adjust the rotation and role assignment.
- `/retro open title:"Sprint 5"` creates the four retrospective threads.

---

## 6. Start the AI router bot

1. Install requirements and configure the environment file:
   ```bash
   cd ../discord_ai_router_bot
   pip install -r requirements.txt
   cp .env.example .env
   ```
2. Populate `.env` with the bot token and any provider API keys.
3. Run the bot:
   ```bash
   python ai_router.py
   ```
4. Test in Discord:
   ```
   /ai provider:openai role:code prompt:"How do I sort a list?"
   ```
   Add `public:true` to share the reply with the channel; omit it for a private response.

---

## 7. Running everything with Docker (optional)

From the repository root:

```bash
docker compose build
docker compose up -d
```

Confirm that `.env` files are filled in before starting. The compose file mounts those files read-only and persists the Ops bot state directory. Use `docker compose logs -f` to monitor output.

---

## 8. Preparing a handover package

1. Run a quick validation:
   ```bash
   python -m compileall discord_team_hub_blueprint discord_slash_bot_plus discord_ai_router_bot
   ```
2. Create archives:
   ```bash
   zip -r discord_team_hub_blueprint.zip discord_team_hub_blueprint
   zip -r discord_slash_bot_plus.zip discord_slash_bot_plus
   zip -r discord_ai_router_bot.zip discord_ai_router_bot
   ```
3. Provide the archives plus:
   - `server_spec.json`
   - `server_state.json`
   - `discord_slash_bot_plus/data/oncall.json`
   - `discord_slash_bot_plus/data/schedules.json`
   - `discord_ai_router_bot/prompts.json`
   - Sanitized copies of `.env` files (remove secrets)
4. Rotate all Discord and API tokens after delivery.

---

## 9. Quick troubleshooting

- **Slash commands missing**: Reinvite the bot with the `applications.commands` scope and wait a few minutes for Discord to sync.
- **Bots cannot post**: Confirm channel permissions and ensure the bot role is higher than the roles it must manage.
- **Noisy webhooks**: Adjust filters in GitHub, Jenkins, Grafana, etc., or temporarily disable the webhook URL.
- **AI responses failing**: Verify provider API keys and network access to the provider endpoints.

---

You now have the short version of the setup. Refer to `0-DEVELOPER_MANUAL.md` whenever you need the complete runbook and acceptance checklist.
