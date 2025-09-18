# Team Structure Cheat Sheet

This project builds a Discord home base where a full software team can plan, build, ship, and support products together. Think of it as a virtual office with clearly labelled rooms and job badges so everyone knows where to go and what to do.

---

## 1. Who’s on the team?

| Role | What they’re responsible for | Typical Permissions |
| --- | --- | --- |
| **Owner** | Final decisions, security, and inviting new tooling. | Full admin control. |
| **Program Manager** | Keeps the whole program aligned, runs portfolio reviews. | Manage channels, roles, events, and messages. |
| **Project Manager** | Owns day-to-day delivery for one project or squad. | Manage channels/events, guide approvals. |
| **Scrum Master** | Facilitates agile rituals, removes blockers. | Manage events/messages. |
| **DevOps** | Handles infrastructure, deployments, monitoring, on-call rotations. | Manage webhooks, channels, voice moderation. |
| **Developers** | Build features, review code, ship updates. | Post, attach files, use slash commands. |
| **Designers** | UX/UI work, Figma reviews, prototypes. | Post, attach files, use slash commands. |
| **QA** | Testing plans, bug triage, release gates. | Post, attach files, use slash commands. |
| **Stakeholders** | Execs or business sponsors who need read-only visibility. | Read important channels, limited posting. |
| **On-Call** | Current responders for incidents and alerts. | Mentioned by alerts, can post in on-call spaces. |
| **Bots** | Automation helpers (Ops bot & AI bot). | Post updates, manage threads, sometimes manage roles. |
| **Contractors** | Vendors or partners doing scoped work. | Limited access to Partner-Projects area only. |

---

## 2. The “virtual office” layout

Each Discord category is a hallway of related rooms. Here’s the high-level map:

- **General** – Lobby channels like `#announcements`, `#town-square`, and FAQs for the whole org.
- **Programs** – Status dashboards and portfolio overviews managed by program leadership.
- **Project-* (Alpha, Beta, etc.)** – One hallway per project with planning, build, test, and retro channels.
- **Partner-Projects** – Mirrored project spaces for contractors; same structure but locked down so sensitive data stays inside.
- **Agile** – Sprint boards, standup threads, retro summaries; Scrum Masters live here.
- **Waterfall** – For teams running phased delivery (requirements, design, QA, UAT, release approval).
- **DevOps & CI/CD** – Webhook landing spots (`#ci-cd-pipeline`, `#alerts`, `#deploy-approvals`) plus on-call coordination.
- **Design & Docs** – Figma updates, shared artifacts, how-to guides.
- **Governance** – Risk register, audit log, compliance notes.
- **Voice & Stage** – Incident war rooms, daily standup voice rooms, town-hall stage events.

Every channel has permissions pre-wired so only the right roles can talk, approve, or see sensitive info.

---

## 3. Daily rhythm (what happens where)

1. **Plan the work**
   - Program managers post goals in `Programs` and `General`.
   - Project managers break tasks into WBS templates using `/wbs` in their project hallway.
   - Scrum Masters set up standups with `/standup_sched` in project channels.

2. **Build and review**
   - Developers discuss features in project build channels, share progress in `#ci-cd-pipeline` via webhooks.
   - Designers drop mockups in `Design & Docs` and partner with PMs for feedback.
   - QA tracks test runs and raises release risks.

3. **Ship and monitor**
   - Deployments are approved in `DevOps & CI/CD` with `/deploy approve`.
   - Alerts land in `#alerts`; the on-call role rotates with `/oncall rotate`.
   - Incident voice calls start in the `war-room` channel.

4. **Learn and improve**
   - `/retro open` creates Keep/Drop/Start/Kudos threads after each sprint or release.
   - Governance rooms capture decisions, risks, and compliance notes for posterity.

---

## 4. Automation buddies

- **Ops Slash Bot (`discord_slash_bot_plus`)**
  - `/standup` modal for daily updates.
  - `/standup_sched`, `/retro open`, `/deploy approve`, `/oncall`—all run from the Discord UI.
  - Keeps shared JSON data (`schedules.json`, `oncall.json`) so rituals survive restarts.

- **AI Router Bot (`discord_ai_router_bot`)**
  - `/ai` command forwards prompts to OpenAI, Anthropic, Gemini, or Grok.
  - Role-specific prompts (code, PM, exec, design, partner) keep answers on-brand.
  - Supports private replies, shared threads, and provider-by-provider testing.

These bots make the Discord space feel like a productivity app instead of a chatroom.

---

## 5. Contractors and partner squads

- Contractors get the **Contractors** role and only see `Partner-Projects`.
- Each partner hallway mirrors the internal project layout but does **not** expose governance, on-call, or internal approvals.
- Internal leads copy important summaries back into internal channels to keep leadership in the loop.
- When a partner engagement ends, archive the partner hallway and remove the role (the blueprint includes a checklist).

---

## 6. Reference files in this repo

If you need deeper detail:

- `discord_team_hub_blueprint/server_spec.json` – the master list of roles, categories, channels, and permission rules.
- `0-DEVELOPER_MANUAL.md` – full build-and-handover manual.
- `discord_slash_bot_plus/README_PLUS.md` – everything about the Ops bot commands.
- `discord_ai_router_bot/README_AI_ROUTER.md` – how the AI routing works.
- `2-README.md` – step-by-step onboarding guide for new builders.

Use this cheat sheet to keep the big picture in mind, then dive into the deeper docs when you’re ready to run the full build.
