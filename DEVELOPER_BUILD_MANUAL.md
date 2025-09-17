# Native Software Discord Hub — Developer Build Manual

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
   ```bash
   export DISCORD_BOT_TOKEN="<provisioning bot token>"
   export DISCORD_GUILD_ID="<guild id>"
   ```

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
