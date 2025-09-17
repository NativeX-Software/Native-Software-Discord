# Native Software Discord Hub — Developer Build Manual

<<<<<<< ours
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
=======
Review the ready-made bundles and use them alongside this manual:

- **Server provisioning pack** (`discord_team_hub_blueprint/`) → delivers
  roles, channels, webhooks, and the reconciliation script. Package as
  `discord_team_hub_blueprint.zip`.
- **Ops slash bot** (`discord_slash_bot_plus/`) → implements standups, WBS,
  deployment approvals, on-call rotations, retros, and scheduling. Package as
  `discord_slash_bot_plus.zip`.
- **AI router bot** (`discord_ai_router_bot/`) → routes `/ai` prompts to OpenAI,
  Anthropic, Gemini, or Grok. Package as `discord_ai_router_bot.zip`.

This guide mirrors the customer acceptance checklist, details Docker Compose
automation for both bots (with Watchtower), and provides a soup-to-nuts runbook
for provisioning, validation, and handover.

---

## 0) Scope & Success Criteria

**Goal**: Deliver a Discord-based, AI-augmented collaboration hub that replaces
core Slack/Teams/Jira/Confluence functions for software, DevOps, PMO, and design
teams.

**Must haves**

- Guild structure featuring Programs → Projects, Agile, Waterfall, DevOps &
  CI/CD, Design, Governance, and Voice/Stage categories.
- Roles & permissions with controlled announcement and approval flows.
- CI/CD and monitoring webhooks that land in the right channels with alerting
  for on-call rotations.
- Ops Bot commands: `/standup`, `/standup_sched`, `/wbs`, `/deploy approve`,
  `/retro open`, `/oncall`.
- AI Router Bot command: `/ai ask` with OpenAI, Anthropic, Gemini, and Grok
  providers and role prompts.
- Partner workspace that allows contractors to collaborate securely without
  exposing governance/on-call channels.
- Handover with full ownership, rotated secrets, and archived state.

**Acceptance**

- All slash commands operate in a test guild.
- CI/CD and monitoring events land in their designated channels and mention the
  correct roles.
- Deployment approvals enforce quorum/roles; on-call rotations update Discord
  roles.
- `/ai` routes to the selected provider with the correct persona prompts.
- Handover checklist completed and owner promoted.

---

## 1) High-Level Architecture

```
Discord Guild
├─ Categories: General, Programs, Project-* (Alpha/Beta/..), Partner-Projects,
│              Agile, Waterfall, DevOps & CI/CD, Design & Docs, Governance,
│              Voice/Stage
├─ Webhooks:  GitHub/GitLab/Jenkins/Azure DevOps → #ci-cd-pipeline
│             Grafana/Prometheus/Datadog/Sentry → #alerts
├─ Roles:     Owner, Program Manager, Project Manager, Scrum Master, DevOps,
│             Developers, Designers, QA, Contractors, On-Call, Stakeholders,
│             Bots
├─ Bots:
│   1) Ops Slash Bot  (`discord_slash_bot_plus`)
│      - /standup, /standup_sched, /wbs, /deploy approve, /retro open, /oncall
│   2) AI Router Bot  (`discord_ai_router_bot`)
│      - /ai ask → routes to OpenAI/Anthropic/Gemini/Grok with role prompts
└─ State: schedules.json, oncall.json, server_state.json (webhook URLs)
```

---

## 2) Prereqs & Access

1. **Discord assets**
   - Create the target guild.
   - Register three Discord applications: provisioning bot, ops bot, AI router.
   - Invite the provisioning bot with `bot` and `applications.commands` scopes;
     temporarily grant **Administrator**.
   - Invite production bots with minimal permissions: Send Messages, Embed Links,
     Attach Files, Read Message History (optional), Manage Threads (optional),
     Manage Roles (needed for `/oncall`).

2. **Secrets & configuration**
   - Discord bot tokens for all three apps.
   - Provider keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
     `GROK_API_KEY`, and optional `GROK_BASE_URL` (self-hosted endpoint).
   - Store secrets in `.env` files kept outside source control and rotate on
     handover.

3. **Runtime requirements**
   - Python 3.10+ for local execution.
   - Git, zip, curl for repo management and webhook tests.
   - Docker Engine + Docker Compose (v2) if you plan to use the provided stack.
   - Outbound internet to Discord and AI providers.

4. **Filesystem layout**
   - Clone this repo.
   - Keep `discord_slash_bot_plus/data/` writable for `schedules.json` and
     `oncall.json`.
   - Ensure `discord_team_hub_blueprint/server_state.json` and related files are
     retained after provisioning; bots reference IDs/webhooks stored there.
5. **Contractor segmentation plan**
   - Pre-create the **Contractors** role in your production org so Discord SSO
     tools can auto-assign it.
   - Decide which internal roles shadow vendor leads (e.g. assign a Project
     Manager or Scrum Master for every external squad) to maintain accountability.

---

## 3) Provision the Server (Structure + Roles + Webhooks)

1. **Unpack the bundle**
   ```bash
   unzip discord_team_hub_blueprint.zip
   cd discord_team_hub_blueprint
   ```

2. **Install dependencies**
   ```bash
   python -m pip install -U "discord.py>=2.3.2"
   ```

3. **Export credentials**
>>>>>>> theirs
   ```bash
   export DISCORD_BOT_TOKEN="<provisioning bot token>"
   export DISCORD_GUILD_ID="<guild id>"
   ```

<<<<<<< ours
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
=======
4. **Run the provisioning script**
   ```bash
   python create_discord_server.py
   ```

   The script reconciles roles, categories, channels, and webhooks against
   `server_spec.json` and records resulting IDs and webhook URLs in
   `server_state.json`.

5. **Post-provisioning**
   - Remove Administrator from the provisioning bot or delete it entirely.
   - Share webhook URLs securely with the DevOps team for external integrations.
   - Configure external systems:
     - **GitHub** → Settings → Webhooks: paste URL, subscribe to `push`,
       `pull_request`, `workflow_run`, set a secret, verify `X-Hub-Signature-256`.
     - **GitLab** → Integrations → Webhooks: pipeline + merge request events.
     - **Jenkins/Azure DevOps** → service hooks/post-build actions to
       `#ci-cd-pipeline`.
     - **Grafana/Prometheus/Datadog/Sentry** → route critical alerts to `#alerts`
       and ping `@On-Call`; send informative noise to a secondary channel if
       desired.
   - Validate read-only and private channel permissions against `server_spec.json`.

6. **Reference state files**
   - `server_state.json` → canonical IDs + webhook URLs.
   - `schedules.json` & `oncall.json` → initial placeholders consumed by bots.

---

## 4) Deploy the Ops Slash Bot (Standups, WBS, Approvals, On-Call, Retros)

1. **Local virtualenv (optional)**
   ```bash
   cd discord_slash_bot_plus
   python -m venv .venv
   source .venv/bin/activate
   pip install -U -r requirements.txt
   cp .env.example .env  # fill DISCORD_BOT_TOKEN (+ optional DISCORD_GUILD_ID)
   python bot.py
   ```

2. **Command summary**

   | Command | Purpose | Notes |
   | --- | --- | --- |
   | `/standup` | Modal-driven async standup | Posts embed to invoking channel. |
   | `/standup_sched` | Schedule, list, clear reminders | Persisted in `data/schedules.json`. |
   | `/wbs` | Render WBS from JSON/template | Templates stored in `data/wbs_templates/`. |
   | `/deploy approve` | Quorum-based deployment approvals | Buttons enforce `Program Manager` / `DevOps` roles. |
   | `/retro open` | Creates threads for Keep/Drop/Start/Kudos | Threads named after session title. |
   | `/oncall` | Manage rotation roster | Updates `data/oncall.json` and the Discord role. |

3. **Permissions checklist**
   - Send Messages, Embed Links, Attach Files, Use Application Commands.
   - Read Message History (recommended), Manage Threads (for retros),
     Manage Roles (required for `/oncall`).

4. **Observability**
   - Logs emitted to stdout; ship to CloudWatch/ELK or equivalent.
   - Consider adding alerting for missed schedules or command errors.

5. **Container deployment**
   - See “Combined Docker Compose Stack” below for Watchtower-managed runtime.
   - When running standalone Docker, mount `.env` and `data/` to persist state.

---

## 5) Deploy the AI Router Bot (Multi‑LLM/Agent Layer)

1. **Local virtualenv (optional)**
   ```bash
   cd discord_ai_router_bot
   python -m venv .venv
   source .venv/bin/activate
   pip install -U -r requirements.txt
   cp .env.example .env  # populate DISCORD_BOT_TOKEN + provider keys
   python ai_router.py
   ```

2. **Slash command**

   `/ai provider:<openai|anthropic|gemini|grok> model:<text> role:<default|code|pm|ops|exec|design|research|partner> prompt:<text> temp:0.2 max_tokens:800 thread:true public:false`

   - Role prompts defined in `prompts.json` (now including `partner` for vendor
     coordination); extend for additional personas.
   - Providers live under `providers/`; implement `complete()` in a new class and
     register it in `providers/__init__.py` to add more backends.
   - Default rate limit is 5 requests per 60 seconds per channel (adjust in
     `ai_router.py`).

3. **Permissions & intents**
   - Send Messages, Embed Links, Attach Files, Use Application Commands.
   - Optional privileged intent `MESSAGE_CONTENT` (set `ENABLE_MESSAGE_CONTENT=1`
     and request Discord approval) for channel summaries.

4. **Security & cost controls**
   - Restrict to `#ai-*` channels via Discord permissions.
   - Optionally add per-user budgets or audit logging hooks in `ai_router.py`.
   - Store provider API keys in a vault/secret manager; rotate regularly.

5. **Container deployment**
   - Covered in the combined Docker Compose stack; for standalone Docker mount
     `.env` and any custom prompt files.

### Combined Docker Compose Stack (Ops Bot + AI Router + Watchtower)

The repository root includes `docker-compose.yml` plus Dockerfiles for each bot.
This stack builds both services, bind-mounts their `.env` files, persists
`schedules.json`/`oncall.json`, and runs Watchtower to monitor for image updates.

```bash
docker compose build
docker compose up -d
```

Key notes:

- Edit `.env` in each bot directory **before** running the compose commands; the
  files are mounted read-only inside the containers.
- `discord_slash_bot_plus/data/schedules.json` and `data/oncall.json` are bind
  mounted so schedule/on-call changes survive restarts.
- `discord_ai_router_bot/prompts.json` is mounted read-only to allow live
  persona tuning without rebuilding.
- Watchtower is label-scoped (`WATCHTOWER_LABEL_ENABLE=true`) and only manages
  services labeled with `com.centurylinklabs.watchtower.enable=true`.
- Run `docker compose pull` (if using registry-hosted images) or `docker compose
  build --pull` to refresh images that Watchtower will later roll out.

---

## 6) Methodology & Workflow Mapping

**Agile**

- `/standup` for async updates; `/standup_sched` for reminders.
- Kanban sources (Trello/Jira/Linear) post to `#kanban-updates` via webhook.
- `/retro open` to create lanes; `/ai role:pm` to synthesise takeaways.

**Waterfall**

- Phase channels: `#req-signoff`, `#design-phase`, `#qa-phase`, `#uat-phase`,
  `#release-approval` remain read-only except to leadership/bots.
- Use `/ai role:pm` to analyse risks/dependencies prior to approvals.

**SDLC & DevOps**

- CI webhooks → `#ci-cd-pipeline`; deployments tracked via `/deploy approve`.
- Monitoring alerts → `#alerts`; `/oncall rotate` manages rosters; escalate to
  war-room voice channel when necessary.
- `/ai role:ops` for diagnostic suggestions from alert payloads.

**Leadership**

- `/ai role:exec` for weekly summaries, ROI notes, hiring implications.

**External contractors & partners**

- Assign the **Contractors** role as soon as invites are accepted so sensitive
  channels remain hidden by default.
- Duplicate the **Partner-Projects** category from `server_spec.json` per
  vendor/programme (lobby, briefing, artifacts, standups) to keep workstreams
  isolated.
- Configure `/standup_sched`, `/standup`, and `/wbs` inside partner areas only;
  keep `/deploy approve` and retrospectives for internal roles and copy the
  results back into partner threads.
- Share curated runbooks/templates in `#partner-artifacts`, track requests in
  `#partner-briefing`, and avoid exposing governance/on-call channels directly.
- Audit membership monthly, revoke access immediately after contract completion,
  and archive partner threads alongside the latest `server_state.json` snapshot.

---

## 7) Integration Details (Concise but Exact)

**GitHub Webhook**
- Events: `push`, `pull_request`, `workflow_run`.
- Set and store a secret; verify `X-Hub-Signature-256` in inbound payloads.
- Format messages as concise embeds (commit/PR title, author, status, links).

**GitLab / Jenkins / Azure DevOps**
- Use project-level tokens or service hooks; filter to main branches.
- Surface actionable summaries with links to detailed logs.

**Grafana / Prometheus Alertmanager / Datadog / Sentry**
- Route critical alerts to `#alerts` and ping `@On-Call`.
- Auto-create incident threads on first alert; auto-close after quiet period.

**Figma / Design tooling**
- Figma bot posts updates to `#design-collab`.
- Store canonical design links in `#project-artifacts`; approvals logged in
  `#release-approval`.

---

## 8) Security, Privacy, Compliance

- Keep secrets in `.env`; never commit them; rotate on handover.
- Enforce channel overwrites per `server_spec.json`, especially read-only and
  private areas (approvals, on-call).
- Scrub bot outputs for credentials/PII before forwarding to AI providers; add a
  regex scrubber if needed.
- Enable Discord Audit Log and ship bot logs to your observability stack.
- Implement per-provider quotas or per-user budgets to control AI spend.

---

## 9) Testing Plan (Minimum)

1. **Provisioning validation**
   - Run the blueprint; verify categories/channels/permissions.
   - Confirm webhook URLs in `server_state.json` are populated.

2. **Webhook smoke tests**
   - Send sample GitHub `workflow_run` payload → `#ci-cd-pipeline`.
   - Send mock Alertmanager payload → `#alerts`; ensure `@On-Call` pings.

3. **Ops bot commands**
   - `/standup` modal posts embed.
   - `/standup_sched schedule 09:30` updates `data/schedules.json` and fires.
   - `/wbs template:sample_wbs_template` renders correctly.
   - `/deploy approve version:v1.2.3 quorum:2` enforces approvals/rejects.
   - `/oncall setup` → add → list → rotate updates role + `data/oncall.json`.
   - `/retro open` spawns Keep/Drop/Start/Kudos threads.

4. **AI router bot**
   - `/ai` against each enabled provider; confirm responses + thread options.
   - Test `public:true` vs. default ephemeral responses.

5. **Persistence & restart**
   - Restart services (`docker compose restart` or systemd) and verify schedules,
     on-call roster, and provider defaults persist.

6. **Security review**
   - Audit Discord logs for provisioning/bot actions.
   - Ensure `.env` files remain local and secrets vault entries are updated.

---

## 10) Ops Runbook (Cheat Sheet)

- Restart bots: `systemctl restart nativex-ops-bot` / `nativex-ai-router` or
  `docker compose restart ops_bot ai_router_bot`.
- Rotate on-call: `/oncall rotate`.
- Mute noisy alerts: adjust source routing or temporary channel restrictions.
- Incident response: use war-room voice + `#alerts` incident thread;
  summarise via `/ai role:ops`.
- Watchtower: review logs with `docker compose logs -f watchtower`; disable by
  stopping the service if manual control is required.

---

## 11) Handover Checklist (Final)

- Promote customer contact to Server Owner; remove developer Admin access.
- Rotate Discord bot tokens, provider API keys, and webhook secrets; regenerate
  as needed.
- Destroy/recreate legacy webhooks after rotation.
- Export & archive: `server_spec.json`, `server_state.json`, `schedules.json`,
  `oncall.json`, `prompts.json`.
- Validate permissions on private/read-only channels.
- Document hosting footprint (hosts, service units, Docker stack location,
  `.env` storage) for ops.

---

## 12) Deliverables (What the Developer Must Hand Back)

- Running Discord server matching `server_spec.json` (duplicate project
  categories as requested).
- Configured webhooks with CI/CD + monitoring payloads landing in correct
  channels.
- Ops bot deployed with all commands working; persistent state files present.
- AI router bot deployed with at least two providers tested end-to-end.
- Documentation package:
  - Final `server_spec.json`, `server_state.json`.
  - Ops bot `.env` (redacted), `requirements.txt`, `README_PLUS.md`.
  - AI router `.env` (redacted), `requirements.txt`, `README_AI_ROUTER.md`,
    `prompts.json`.
  - Systemd/Docker deployment notes (commands + unit files/compose usage).
- Handover completed: owner rights granted, keys rotated, audit log reviewed.

---

## Appendix A — Channel & Role Map (Quick Reference)

- `#announcements` → Owner/Program Manager post; everyone read.
- `#ci-cd-pipeline` → Bots + DevOps post; everyone read.
- `#release-approval` → Program/PM/DevOps post; reactions count as approvals.
- `#on-call` → Visible only to On-Call/DevOps/Program Manager.
- `#runbooks` / `#how-to` → Pin SOPs and onboarding material.
- `Partner-Projects` → Use lobby/briefing/artifacts/standups channels to isolate
  contractor collaboration per vendor.
- Project categories replicate the Alpha pattern (Planning/WBS/Design/Dev/Test/Retro).
>>>>>>> theirs
