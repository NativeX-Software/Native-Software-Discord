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

Each folder includes a dedicated README with setup instructions, environment
variables, and testing checklists.

To package for distribution, zip each directory individually:

```bash
zip -r discord_team_hub_blueprint.zip discord_team_hub_blueprint
zip -r discord_slash_bot_plus.zip discord_slash_bot_plus
zip -r discord_ai_router_bot.zip discord_ai_router_bot
```

The resulting archives can be handed to operations along with the state files
produced during provisioning (`server_state.json`, `schedules.json`,
`oncall.json`) and any environment variable secrets (redacted).
