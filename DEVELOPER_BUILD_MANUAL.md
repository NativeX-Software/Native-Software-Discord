# Native Software Discord Hub — Developer Build Manual

This manual walks a developer through delivering the full Native Software Discord
collaboration hub, from local environment preparation to final handover. It
covers provisioning the guild structure, deploying the operational slash bot,
standing up the AI router bot, wiring webhooks, and validating the installation
against the acceptance criteria in the project brief.

---

## 1. Solution Overview

The implementation is organised into three deliverable bundles. Each bundle can
be zipped and delivered independently, but they are designed to work together.

| Folder | Purpose |
| --- | --- |
| `discord_team_hub_blueprint/` | Guild reconciliation script, structural spec, and baseline state artifacts for roles, channels, and webhooks. |
| `discord_slash_bot_plus/` | Operational automation bot that implements `/standup`, `/standup_sched`, `/wbs`, `/deploy approve`, `/retro open`, and `/oncall`. |
| `discord_ai_router_bot/` | AI routing bot that exposes `/ai` and forwards prompts to OpenAI, Anthropic, Gemini, or Grok using role-specific system prompts. |

Supporting documents live beside each package (`README`, `.env.example`, state
files). This manual shows how to stitch them together for a production-ready
hub.

---

## 2. Prerequisites & Access Checklist

1. **Discord Assets**
   - Create (or identify) the target Discord guild.
   - Register three Discord applications:
     1. Provisioning bot (used once, temporary Administrator permission).
     2. Ops slash bot.
     3. AI router bot.
   - Invite the provisioning bot with `bot` and `applications.commands` scopes;
     temporarily grant **Administrator** for reconciliation.
   - Invite the operational bots with the minimal permissions they require
     (Send Messages, Embed Links, Attach Files, Use Slash Commands, Manage
     Threads if desired).

2. **API Credentials & Secrets**
   - Discord bot tokens for all three applications.
   - Provider keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
     `GROK_API_KEY`, and (optionally) `GROK_BASE_URL` when using a self-hosted
     Grok-compatible endpoint.

3. **Runtime Environment**
   - Python 3.10 or newer.
   - Git, zip, and curl (for webhook tests).
   - Outbound internet access to Discord and the AI provider APIs.
   - Systemd unit or Docker runtime for production deployment.

4. **Local Filesystem Layout**
   - Clone this repository.
   - Ensure the bot state directories (`discord_slash_bot_plus/data/` and the
     root of `discord_team_hub_blueprint/`) remain writable; the bots persist
     JSON files there.

---

## 3. Environment Preparation

### 3.1 Python Virtual Environments

Create isolated environments for each bundle (recommended to keep dependencies
clean):

```bash
cd /path/to/Native-Software-Discord
python -m venv .venv-blueprint
source .venv-blueprint/bin/activate
pip install -U -r discord_team_hub_blueprint/requirements.txt
# when finished provisioning
deactivate
```

Repeat for the ops bot and AI router bot, or adapt to your preferred environment
manager. Use separate `.env` files per service to avoid leaking secrets.

### 3.2 Populating `.env` Files

Each bot folder contains an `.env.example`. Copy it and populate the required
variables:

```bash
cp discord_slash_bot_plus/.env.example discord_slash_bot_plus/.env
cp discord_ai_router_bot/.env.example discord_ai_router_bot/.env
```

Update the copies with the appropriate Discord tokens, guild ID, and provider
API keys. Never commit the filled `.env` files.

---

## 4. Provision the Discord Server

1. **Install Dependencies**
   ```bash
   source .venv-blueprint/bin/activate
   pip install -U "discord.py>=2.3.2"
   ```

2. **Set Environment Variables**
   ```bash
   export DISCORD_BOT_TOKEN="<provisioning bot token>"
   export DISCORD_GUILD_ID="<guild id>"
   ```

3. **Execute the Provisioning Script**
   ```bash
   cd discord_team_hub_blueprint
   python create_discord_server.py
   ```

   The script reads `server_spec.json`, creates or updates roles, categories,
   channels, permission overwrites, and webhooks, then writes the resulting IDs
   to `server_state.json`.

4. **Review Generated State**
   - `server_state.json` — capture role/channel/webhook IDs for downstream bots.
   - `schedules.json` & `oncall.json` — initial placeholders for operational
     state (will be populated later by the ops bot).

5. **Post-Provisioning Actions**
   - Remove Administrator permission from the provisioning bot or delete it.
   - Share relevant IDs and webhook URLs with the team securely.
   - Configure external systems (GitHub, GitLab, Jenkins, Grafana, Prometheus,
     Datadog, Sentry) to point to the recorded webhook URLs.

### 4.1 Webhook Configuration Cheat Sheet

| Source | Discord Channel | Required Events | Notes |
| --- | --- | --- | --- |
| GitHub | `#ci-cd-pipeline` | `push`, `pull_request`, `workflow_run` | Set a secret and verify `X-Hub-Signature-256`. |
| GitLab | `#ci-cd-pipeline` | Pipeline, Merge Request | Use project integrations; filter to main branches. |
| Jenkins / Azure DevOps | `#ci-cd-pipeline` | Build/Release completion | Configure service hooks / post-build actions. |
| Grafana / Prometheus / Datadog / Sentry | `#alerts` | Critical alerts | Ensure `@On-Call` role ping is enabled and noise filtered. |

---

## 5. Deploy the Ops Slash Bot

1. **Install Dependencies**
   ```bash
   python -m venv .venv-ops
   source .venv-ops/bin/activate
   pip install -U -r discord_slash_bot_plus/requirements.txt
   ```

2. **Environment Variables**
   Fill `discord_slash_bot_plus/.env` with:
   - `DISCORD_BOT_TOKEN`
   - (Optional) `DISCORD_GUILD_ID` to speed up guild resolution.

3. **Data Directory**
   Ensure `discord_slash_bot_plus/data/` is writable. The bot persists:
   - `schedules.json` — recurring standup reminders.
   - `oncall.json` — rotation roster.
   - `wbs_templates/` — baseline templates for `/wbs`.

4. **Run Locally**
   ```bash
   cd discord_slash_bot_plus
   source ../.venv-ops/bin/activate
   python bot.py
   ```

5. **Slash Command Registration**
   The bot automatically syncs application commands on startup. If you update
   command definitions, restart the bot (Discord may take up to an hour to fully
   propagate changes in production guilds).

6. **Command Mapping**

   | Command | Purpose | Notes |
   | --- | --- | --- |
   | `/standup` | Launches a modal for asynchronous standups. | Data stored per channel; results posted to the invoking channel. |
   | `/standup_sched` | Schedule recurring standups. | Supports daily times; persisted in `schedules.json`. |
   | `/wbs` | Render WBS templates or ad-hoc JSON. | Sample template provided; add more files under `data/wbs_templates/`. |
   | `/deploy approve` | Gated deployment approval flow. | Enforces quorum and roles (`Program Manager`, `DevOps`, etc.). |
   | `/retro open` | Creates retro threads (Keep/Drop/Start/Kudos). | Threads named after the session title. |
   | `/oncall` | Manage rotation (setup/add/remove/list/rotate). | Assigns/removes the `On-Call` role automatically. |

7. **Production Deployment**
   - For **systemd**, adapt the sample below:
     ```ini
     [Unit]
     Description=NativeX Ops Bot
     After=network-online.target

     [Service]
     WorkingDirectory=/opt/nativex/discord_slash_bot_plus
     Environment="PYTHONUNBUFFERED=1"
     EnvironmentFile=/opt/nativex/discord_slash_bot_plus/.env
     ExecStart=/opt/nativex/venvs/ops/bin/python bot.py
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```
   - For **Docker**, create an image with the requirements installed and mount a
     volume to persist the `data/` directory.

8. **Observability**
   - Logs are emitted to stdout; ship them to your log stack (CloudWatch, ELK,
     etc.).
   - Configure alerts for command failures or missed schedule ticks if desired.

---

## 6. Deploy the AI Router Bot

1. **Install Dependencies**
   ```bash
   python -m venv .venv-ai
   source .venv-ai/bin/activate
   pip install -U -r discord_ai_router_bot/requirements.txt
   ```

2. **Environment Variables**
   Populate `discord_ai_router_bot/.env` with:
   - `DISCORD_BOT_TOKEN`
   - Any provider keys you intend to enable (`OPENAI_API_KEY`, etc.).
   - Optional: `ENABLE_MESSAGE_CONTENT=1` if you have Discord approval for the
     privileged intent (required for channel summarisation features).

3. **Run Locally**
   ```bash
   cd discord_ai_router_bot
   source ../.venv-ai/bin/activate
   python ai_router.py
   ```

4. **Command Usage**
   `/ai provider:<openai|anthropic|gemini|grok> model:<text> role:<default|code|pm|ops|exec|design|research> prompt:<text> temp:<float> max_tokens:<int> thread:<true|false> public:<true|false>`

   - Role-specific system prompts live in `prompts.json`. Extend or edit the file
     to customise tone and policy.
   - Providers are modular; implement `providers/base.py::LLMProvider.complete`
     for new backends and register them in `providers/__init__.py`.
   - Responses are ephemeral by default unless `public:true` is specified.

5. **Cost and Access Controls**
   - Restrict the bot to `#ai-*` channels using Discord channel permissions.
   - Adjust rate limiting logic in `ai_router.py` if you need per-user or
     per-channel quotas.
   - Consider adding auditing hooks to log prompts/responses for compliance.

6. **Deployment**
   Mirror the systemd/Docker approach from the ops bot, pointing to the AI bot's
   working directory, virtual environment, and `.env` file.

---

## 7. End-to-End Testing Plan

Use a staging guild to perform the following checks before production handover:

1. **Structure Verification**
   - Confirm categories match the blueprint (`Programs`, `Project-Alpha`, etc.).
   - Validate channel permissions for read-only and private channels.

2. **Webhook Smoke Tests**
   - Send sample payloads (GitHub push, Alertmanager alert) to ensure messages
     arrive in the correct channels and mention the right roles.

3. **Ops Bot Commands**
   - `/standup` → modal collects responses; summary posts to channel.
   - `/standup_sched` → schedule a reminder at 09:30; verify reminder triggers.
   - `/wbs` → render `sample_wbs_template.json` in a planning channel.
   - `/deploy approve` → require quorum of two; test approve & reject flows.
   - `/oncall setup` → configure role; `/oncall rotate` updates members.
   - `/retro open` → threads for Keep/Drop/Start/Kudos auto-created.

4. **AI Router Bot**
   - Invoke `/ai` with each provider; ensure routing and responses succeed.
   - Test thread creation (`thread:true`) and public replies (`public:true`).

5. **State Persistence**
   - Restart both bots; confirm schedules, on-call roster, and prompts persist.

6. **Security & Compliance**
   - Review Discord audit logs for provisioning changes.
   - Confirm secrets remain outside version control.

---

## 8. Operational Runbook Highlights

- **Restarting Services**: `systemctl restart nativex-ops-bot` or equivalent;
  same for the AI bot.
- **Rotating On-Call**: `/oncall rotate` (ensures the `On-Call` role updates and
  the roster file is saved).
- **Handling Noisy Alerts**: Adjust webhook filters in source systems or apply
  temporary channel posting restrictions.
- **Incident Response**: Use the `#alerts` incident thread and the war-room voice
  channel; summarise with `/ai ask role:ops`.

---

## 9. Packaging & Handover

1. Run final tests (`python -m compileall discord_team_hub_blueprint discord_slash_bot_plus discord_ai_router_bot`).
2. Zip each deliverable directory:
   ```bash
   zip -r discord_team_hub_blueprint.zip discord_team_hub_blueprint
   zip -r discord_slash_bot_plus.zip discord_slash_bot_plus
   zip -r discord_ai_router_bot.zip discord_ai_router_bot
   ```
3. Deliver archives alongside redacted copies of `.env` files, `server_spec.json`,
   `server_state.json`, `schedules.json`, `oncall.json`, and deployment notes.
4. Rotate all tokens and webhook secrets after transfer; promote the customer to
   guild Owner and remove temporary admin access.

---

## 10. Troubleshooting Tips

| Issue | Resolution |
| --- | --- |
| Slash commands not visible | Ensure the bot has the `applications.commands` scope and restart after syncing; allow up to one hour for propagation. |
| Permission errors on read-only channels | Re-run the provisioning script or manually adjust channel overwrites to align with `server_spec.json`. |
| Webhooks posting to wrong channel | Verify the webhook URL in `server_state.json`; recreate via provisioning script if needed. |
| AI requests failing | Check provider API keys and network egress; inspect logs for HTTP error codes. |
| On-call role not updating | Ensure the role name in Discord matches the `oncall` configuration and that the bot has Manage Roles permission above the `On-Call` role. |

---

By following this manual, a developer can reproduce the complete Discord-based
collaboration hub, satisfy the acceptance criteria, and hand over a maintainable
system to operations.
