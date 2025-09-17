# Native Software Ops Slash Bot

This bot provides the operational automation flows referenced in the project
brief: standups, scheduling, work breakdown structure rendering, deployment
approvals, retrospectives, and on-call rotations.

## Features

- `/standup` launches a modal that posts the response as an embed to the active
  channel.
- `/standup_sched` offers `schedule`, `list`, and `clear` subcommands. The data is
  persisted in `data/schedules.json`.
- `/wbs` renders a work breakdown structure from inline JSON or a template file.
- `/deploy` opens an approval card with interactive Approve/Reject buttons and
  quorum enforcement.
- `/oncall` manages named rotations (setup, add, remove, list, rotate) stored in
  `data/oncall.json` and synchronises the Discord role assignment.
- `/retro open` seeds threaded retrospective lanes (Keep/Drop/Start/Kudos).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # populate values
python bot.py
```

Environment variables (via `.env` or shell):

- `DISCORD_BOT_TOKEN` – bot token with the `applications.commands` scope.
- `DISCORD_GUILD_ID` (optional) – limits command sync to a single guild for rapid
  iteration.
- `LOG_LEVEL` – optional logging verbosity (defaults to INFO).

## Persistent Data

State files live in `data/` and are JSON-formatted for easy inspection:

- `schedules.json`
- `oncall.json`
- `wbs_templates/` – include additional templates for `/wbs`.

The bot automatically creates the directories/files on first run.

## Permissions

Grant the following Discord permissions to the bot:

- `Send Messages`
- `Embed Links`
- `Attach Files`
- `Read Message History`
- `Use Application Commands`
- `Manage Roles` (required for `/oncall rotate` to update the rotation role)
- `Manage Threads` (optional but recommended for retrospectives)

## Deployment Notes

- For systemd, set `WorkingDirectory` to the project folder and `EnvironmentFile`
  to the `.env` path. Ensure the service user can read/write the `data/`
  directory.
- For Docker, mount the project directory and pass environment variables via a
  secret store. Persist the `data/` directory as a volume to retain schedules and
  on-call rotations.

## Testing Checklist

- Trigger `/standup` and verify the embed posts to the correct channel.
- Configure `/standup_sched schedule 09:30 timezone:UTC` and confirm
  `data/schedules.json` is updated.
- Execute `/wbs template:sample_wbs_template` and review the embed output.
- Run `/deploy version:v1.2.3 quorum:2` and confirm approvals are recorded in the
  embed footer and buttons disable after quorum is met or a reject is issued.
- Configure `/oncall setup role:@On-Call`, add members, list the rotation, and
  rotate to confirm the role assignment changes.
- Open a retrospective via `/retro open` and ensure four threads are created.
