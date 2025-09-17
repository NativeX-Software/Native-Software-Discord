# Native Software Discord Automation Packs

This repository contains the three deliverables requested in the project brief:

1. **`discord_team_hub_blueprint/`** – server provisioning bundle with
   `server_spec.json` and the automation script that creates roles, channels, and
   webhooks.
2. **`discord_slash_bot_plus/`** – operational slash bot covering standups,
   scheduling, WBS rendering, deployment approvals, retrospectives, and on-call
   rotations.
3. **`discord_ai_router_bot/`** – AI router bot exposing `/ai` and routing prompts
   to OpenAI, Anthropic, Gemini, or Grok with role-based system prompts.

The blueprint now includes a **Contractors** role and a dedicated
**Partner-Projects** category so the Native Software Discord team can onboard
external contributors while keeping governance, incident response, and finance
channels internal.

Each folder includes a dedicated README with setup instructions, environment
variables, and testing checklists. A consolidated build manual lives at
`DEVELOPER_BUILD_MANUAL.md` and mirrors the delivery checklist provided in the
project brief.

To package for distribution, zip each directory individually:

```bash
zip -r discord_team_hub_blueprint.zip discord_team_hub_blueprint
zip -r discord_slash_bot_plus.zip discord_slash_bot_plus
zip -r discord_ai_router_bot.zip discord_ai_router_bot
```

The resulting archives can be handed to operations along with the state files
produced during provisioning (`server_state.json`, `schedules.json`,
`oncall.json`) and any environment variable secrets (redacted). Include
`docker-compose.yml` and `DEVELOPER_BUILD_MANUAL.md` so operations can reuse the
container stack and walkthrough without cloning the repository.

## Containerized Deployment

A ready-to-run `docker-compose.yml` is included at the repository root. It
builds images for both bots, mounts their `.env` files, persists operational
state (`schedules.json`, `oncall.json`), and runs [Watchtower](https://github.com/containrrr/watchtower)
to monitor for image updates.

```bash
docker compose build
docker compose up -d
```

Populate the `.env` files in each bot directory before starting the stack. The
Watchtower container is label-scoped and will only manage the bots defined in
this compose file.
>>>>>>> theirs
