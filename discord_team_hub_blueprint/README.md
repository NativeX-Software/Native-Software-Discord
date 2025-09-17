# Discord Team Hub Blueprint

This package provisions the Native Software collaboration hub described in the
project brief. It creates the roles, categories, channels, permission
structures, and foundational webhooks required for the DevOps- and AI-augmented
workflow.

## Contents

- `server_spec.json` – canonical description of the guild layout, roles (native
  and external/contractor), and webhooks.
- `create_discord_server.py` – provisioning script that reconciles a guild to
  match the specification.
- `server_state.json` – generated on first run with identifiers and webhook
  URLs.
- `schedules.json`, `oncall.json` – empty state containers created for the bots
  that depend on them.

## Prerequisites

- Python 3.10+
- `discord.py>=2.3.2`
- Discord application/bot with the **Administrator** permission during
  provisioning.
- Environment variables
  - `DISCORD_BOT_TOKEN`
  - `DISCORD_GUILD_ID`

Install dependencies:

```bash
python -m pip install -U "discord.py>=2.3.2"
```

## Provisioning Workflow

1. Invite the provisioning bot to the target guild with the `applications.commands`
   and `bot` scopes. Temporarily grant the Administrator permission.
2. Export credentials and execute the script:

   ```bash
   export DISCORD_BOT_TOKEN="<token>"
   export DISCORD_GUILD_ID="<guild id>"
   python create_discord_server.py
   ```

3. Inspect the generated `server_state.json` for role IDs, channel IDs, and
   webhook URLs. Share these values with the ops and AI bot deployments.
4. Remove the Administrator permission (or remove the provisioning bot entirely)
   once the server matches the blueprint.

## Customisation

- Update `server_spec.json` to add new projects. Duplicate the `Project-Alpha`
  category and adjust the channel names/topics.
- Add new webhook definitions in the `webhooks` array. The script will ensure
  they are created and record their URLs.
- Permission overwrites use role names; ensure any new roles exist in the `roles`
  section before referencing them in a channel.
- To support external collaborators, assign them the **Contractors** role and
  use the pre-built **Partner-Projects** category (lobby, briefing, artifacts,
  standups) for secure collaboration. Duplicate this category per vendor or
  programme when you need isolated workspaces.

## Testing Checklist

- Confirm that read-only channels such as `#announcements`, `#ci-cd-pipeline`,
  and `#release-approval` enforce permissions for non-privileged roles.
- Post a test payload to each webhook using the recorded URL to ensure external
  systems can reach Discord.
- Validate that private channels (for example `#on-call`) are hidden from
  `@everyone` and visible to the appropriate roles only.

## Handover Artifacts

After provisioning, archive the following files:

- `server_spec.json`
- `server_state.json`
- `schedules.json`
- `oncall.json`

These files form the baseline required for bot configuration and operational
handover.
