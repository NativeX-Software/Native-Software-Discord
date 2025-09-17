"""Ops automation bot for Native Software Discord."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCHEDULES_PATH = DATA_DIR / "schedules.json"
ONCALL_PATH = DATA_DIR / "oncall.json"
WBS_TEMPLATE_DIR = DATA_DIR / "wbs_templates"

REQUIRED_APPROVER_ROLES = {"Program Manager", "Project Manager", "DevOps"}
DEFAULT_RETRO_LENSES = ("Keep", "Drop", "Start", "Kudos")

load_dotenv()
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))


def load_env(key: str, *, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Environment variable {key} is required")
    return value


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WBS_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for path in (SCHEDULES_PATH, ONCALL_PATH):
        if not path.exists():
            path.write_text(json.dumps({}, indent=2), encoding="utf-8")


class PersistentJSON:
    """Async helper that serialises JSON payloads to disk."""

    def __init__(self, path: Path, default: Any) -> None:
        self._path = path
        self._default = default
        self._lock = asyncio.Lock()
        if not self._path.exists():
            self._path.write_text(json.dumps(self._default, indent=2), encoding="utf-8")

    async def load(self) -> Any:
        async with self._lock:
            return json.loads(await asyncio.to_thread(self._path.read_text, encoding="utf-8"))

    async def save(self, data: Any) -> None:
        async with self._lock:
            payload = json.dumps(data, indent=2, sort_keys=True)
            await asyncio.to_thread(self._path.write_text, payload, encoding="utf-8")


@dataclass
class BotConfig:
    token: str
    guild_id: Optional[int]

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = load_env("DISCORD_BOT_TOKEN", required=True)
        guild_id_raw = load_env("DISCORD_GUILD_ID")
        return cls(token=token or "", guild_id=int(guild_id_raw) if guild_id_raw else None)


class StandupModal(discord.ui.Modal, title="Standup Update"):
    yesterday: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Yesterday",
        placeholder="What did you complete yesterday?",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    today: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Today",
        placeholder="What is your focus today?",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    blockers: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="Blockers",
        placeholder="Call out any blockers or risks",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )

    def __init__(self, author: discord.Member, target_channel: discord.TextChannel) -> None:
        super().__init__()
        self.author = author
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        embed = discord.Embed(
            title="Standup",
            description=f"Standup update from {self.author.mention}",
            colour=discord.Colour.blurple(),
            timestamp=datetime.utcnow(),
        )
        embed.add_field(name="Yesterday", value=self.yesterday.value or "—", inline=False)
        embed.add_field(name="Today", value=self.today.value or "—", inline=False)
        embed.add_field(name="Blockers", value=self.blockers.value or "None", inline=False)
        await self.target_channel.send(embed=embed)
        await interaction.response.send_message("Standup submitted.", ephemeral=True)


class DeployApprovalView(discord.ui.View):
    def __init__(self, quorum: int, approver_roles: set[str]) -> None:
        super().__init__(timeout=3600)
        self.quorum = quorum
        self.approver_roles = approver_roles
        self.approved: Dict[int, datetime] = {}
        self.rejected: Dict[int, datetime] = {}

    async def _check_permissions(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        member_role_names = {role.name for role in interaction.user.roles}
        return bool(member_role_names & self.approver_roles)

    async def _handle_vote(
        self,
        interaction: discord.Interaction,
        bucket: Dict[int, datetime],
        other_bucket: Dict[int, datetime],
        *,
        is_approval: bool,
        completion_message: str,
    ) -> None:
        if not await self._check_permissions(interaction):
            await interaction.response.send_message(
                "You do not have permission to vote on this deployment.",
                ephemeral=True,
            )
            return
        assert isinstance(interaction.user, discord.Member)
        other_bucket.pop(interaction.user.id, None)
        already = bucket.get(interaction.user.id)
        if already is None:
            bucket[interaction.user.id] = datetime.utcnow()
        approvals = len(self.approved)
        rejections = len(self.rejected)
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
        if embed is not None:
            footer = f"Approvals: {approvals} | Rejections: {rejections} | Quorum: {self.quorum}"
            embed.set_footer(text=footer)

        approval_complete = approvals >= self.quorum if is_approval else False
        rejection_complete = rejections >= max(1, self.quorum // 2 + 1) if not is_approval else False

        if approval_complete or rejection_complete:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(completion_message, ephemeral=False)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:  # type: ignore[override]
        await self._handle_vote(
            interaction,
            self.approved,
            self.rejected,
            is_approval=True,
            completion_message="Deployment approval quorum reached.",
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:  # type: ignore[override]
        await self._handle_vote(
            interaction,
            self.rejected,
            self.approved,
            is_approval=False,
            completion_message="Deployment rejected.",
        )

    async def on_timeout(self) -> None:  # type: ignore[override]
        for child in self.children:
            child.disabled = True


class OpsBot(commands.Bot):
    def __init__(self, config: BotConfig) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        ensure_data_files()
        self.schedules = PersistentJSON(SCHEDULES_PATH, {"schedules": []})
        self.oncall = PersistentJSON(ONCALL_PATH, {"rotations": {}})

    async def setup_hook(self) -> None:  # type: ignore[override]
        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = OpsBot(BotConfig.from_env())


@bot.tree.command(name="standup", description="Submit a standup update using an interactive modal.")
async def standup(interaction: discord.Interaction) -> None:
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Standups must be triggered inside a guild.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Standups are limited to text channels.", ephemeral=True)
        return
    modal = StandupModal(interaction.user, interaction.channel)
    await interaction.response.send_modal(modal)


standup_sched_group = app_commands.Group(name="standup_sched", description="Manage standup schedules")


@standup_sched_group.command(name="schedule")
@app_commands.describe(time="24-hour time, e.g. 09:30", timezone="Timezone label", channel="Channel to post reminders in")
async def standup_schedule(
    interaction: discord.Interaction,
    time: str,
    timezone: str = "UTC",
    channel: Optional[discord.TextChannel] = None,
) -> None:
    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("Please choose a text channel for standup reminders.", ephemeral=True)
        return
    data = await bot.schedules.load()
    schedules: List[Dict[str, Any]] = data.setdefault("schedules", [])
    schedules = [entry for entry in schedules if entry.get("channel_id") != target_channel.id]
    schedules.append(
        {
            "channel_id": target_channel.id,
            "time": time,
            "timezone": timezone,
        }
    )
    data["schedules"] = schedules
    await bot.schedules.save(data)
    await interaction.response.send_message(
        f"Standup scheduled for {target_channel.mention} at {time} {timezone}.",
        ephemeral=True,
    )


@standup_sched_group.command(name="list")
async def standup_list(interaction: discord.Interaction) -> None:
    data = await bot.schedules.load()
    schedules: List[Dict[str, Any]] = data.get("schedules", [])
    if not schedules:
        await interaction.response.send_message("No standup schedules defined.", ephemeral=True)
        return
    lines = []
    for entry in schedules:
        channel = interaction.guild.get_channel(entry.get("channel_id")) if interaction.guild else None
        channel_name = channel.mention if isinstance(channel, discord.TextChannel) else "Unknown channel"
        lines.append(f"• {channel_name}: {entry.get('time')} {entry.get('timezone', 'UTC')}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@standup_sched_group.command(name="clear")
@app_commands.describe(channel="Channel to clear. Defaults to the current channel.")
async def standup_clear(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None) -> None:
    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("Please choose a text channel to clear.", ephemeral=True)
        return
    data = await bot.schedules.load()
    schedules: List[Dict[str, Any]] = data.get("schedules", [])
    new_schedules = [entry for entry in schedules if entry.get("channel_id") != target_channel.id]
    data["schedules"] = new_schedules
    await bot.schedules.save(data)
    await interaction.response.send_message(
        f"Standup schedule cleared for {target_channel.mention}.",
        ephemeral=True,
    )


bot.tree.add_command(standup_sched_group)


@bot.tree.command(name="wbs", description="Render a work breakdown structure from JSON data.")
@app_commands.describe(input_json="Inline JSON payload", template="Name of a template file in data/wbs_templates")
async def wbs(
    interaction: discord.Interaction,
    input_json: Optional[str] = None,
    template: Optional[str] = None,
) -> None:
    try:
        if input_json:
            payload = json.loads(input_json)
        else:
            if not template:
                template = "sample_wbs_template"
            template_path = WBS_TEMPLATE_DIR / f"{template}.json"
            if not template_path.exists():
                await interaction.response.send_message("Template not found.", ephemeral=True)
                return
            payload = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        await interaction.response.send_message(f"Invalid JSON: {exc}", ephemeral=True)
        return

    project_name = payload.get("project", "Project")
    embed = discord.Embed(
        title=f"WBS – {project_name}",
        colour=discord.Colour.teal(),
        timestamp=datetime.utcnow(),
    )
    for phase in payload.get("phases", []):
        tasks = phase.get("tasks", [])
        lines = []
        for task in tasks:
            owner = task.get("owner", "Unassigned")
            due = task.get("due", "TBD")
            name = task.get("name", "Task")
            lines.append(f"• **{name}** — {owner} _(due {due})_")
        value = "\n".join(lines) if lines else "No tasks defined."
        embed.add_field(name=phase.get("name", "Phase"), value=value, inline=False)
    await interaction.response.send_message(embed=embed)


deploy_group = app_commands.Group(name="deploy", description="Deployment workflows")


@deploy_group.command(name="approve")
@app_commands.describe(version="Version or build identifier", quorum="Number of approvals required")
async def deploy_approve(interaction: discord.Interaction, version: str, quorum: app_commands.Range[int, 1, 10] = 2) -> None:
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Deployment approvals must run in a guild.", ephemeral=True)
        return
    member_role_names = {role.name for role in interaction.user.roles}
    if not (member_role_names & REQUIRED_APPROVER_ROLES):
        await interaction.response.send_message("Only program, project, or DevOps leads can open deployment approvals.", ephemeral=True)
        return
    embed = discord.Embed(
        title="Deployment Approval",
        description=f"Requesting approval for version **{version}**",
        colour=discord.Colour.orange(),
        timestamp=datetime.utcnow(),
    )
    embed.add_field(name="Requested by", value=interaction.user.mention)
    embed.add_field(name="Quorum", value=str(quorum))
    view = DeployApprovalView(quorum, REQUIRED_APPROVER_ROLES)
    await interaction.response.send_message(embed=embed, view=view)

bot.tree.add_command(deploy_group)


oncall_group = app_commands.Group(name="oncall", description="Manage on-call rotations")


def _ensure_rotation_structure(data: Dict[str, Any], role: discord.Role) -> Dict[str, Any]:
    rotations = data.setdefault("rotations", {})
    rotation = rotations.setdefault(
        role.name,
        {"role_id": role.id, "members": [], "active_member": None},
    )
    if rotation.get("role_id") != role.id:
        rotation["role_id"] = role.id
    return rotation


@oncall_group.command(name="setup")
async def oncall_setup(interaction: discord.Interaction, role: discord.Role) -> None:
    data = await bot.oncall.load()
    _ensure_rotation_structure(data, role)
    await bot.oncall.save(data)
    await interaction.response.send_message(
        f"On-call rotation initialised for **{role.name}**.",
        ephemeral=True,
    )


@oncall_group.command(name="add")
async def oncall_add(interaction: discord.Interaction, role: discord.Role, member: discord.Member) -> None:
    data = await bot.oncall.load()
    rotation = _ensure_rotation_structure(data, role)
    if member.id not in rotation["members"]:
        rotation["members"].append(member.id)
    await bot.oncall.save(data)
    await interaction.response.send_message(
        f"{member.mention} added to the {role.name} rotation.",
        ephemeral=True,
    )


@oncall_group.command(name="remove")
async def oncall_remove(interaction: discord.Interaction, role: discord.Role, member: discord.Member) -> None:
    data = await bot.oncall.load()
    rotation = _ensure_rotation_structure(data, role)
    if member.id in rotation["members"]:
        rotation["members"].remove(member.id)
    if rotation.get("active_member") == member.id:
        rotation["active_member"] = None
    await bot.oncall.save(data)
    await interaction.response.send_message(
        f"{member.mention} removed from the {role.name} rotation.",
        ephemeral=True,
    )


@oncall_group.command(name="list")
async def oncall_list(interaction: discord.Interaction, role: discord.Role) -> None:
    data = await bot.oncall.load()
    rotation = _ensure_rotation_structure(data, role)
    member_ids = rotation.get("members", [])
    if not member_ids:
        await interaction.response.send_message("No members enrolled in this rotation.", ephemeral=True)
        return
    lines = []
    for index, member_id in enumerate(member_ids):
        member = interaction.guild.get_member(member_id) if interaction.guild else None
        indicator = "→" if rotation.get("active_member") == member_id else " "
        if member:
            lines.append(f"{indicator} {index + 1}. {member.mention}")
        else:
            lines.append(f"{indicator} {index + 1}. (member left server)")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@oncall_group.command(name="rotate")
async def oncall_rotate(interaction: discord.Interaction, role: discord.Role) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command must be used in a guild.", ephemeral=True)
        return
    data = await bot.oncall.load()
    rotation = _ensure_rotation_structure(data, role)
    member_ids = rotation.get("members", [])
    members = [interaction.guild.get_member(member_id) for member_id in member_ids]
    members = [member for member in members if member is not None]
    if not members:
        await interaction.response.send_message("No members available to rotate.", ephemeral=True)
        return
    members.append(members.pop(0))
    rotation["members"] = [member.id for member in members]
    next_on_call = members[0]
    rotation["active_member"] = next_on_call.id

    for member in members:
        has_role = role in member.roles
        if member is next_on_call and not has_role:
            await member.add_roles(role, reason="On-call rotation")
        elif member is not next_on_call and has_role:
            await member.remove_roles(role, reason="On-call rotation")

    await bot.oncall.save(data)
    await interaction.response.send_message(
        f"Rotation updated. {next_on_call.mention} is now on call.",
        ephemeral=False,
    )


bot.tree.add_command(oncall_group)


retro_group = app_commands.Group(name="retro", description="Retrospective utilities")


@retro_group.command(name="open")
@app_commands.describe(title="Retro title", channel="Channel to host the retro threads", duration="Auto archive duration in minutes")
async def retro_open(
    interaction: discord.Interaction,
    title: str,
    channel: Optional[discord.TextChannel] = None,
    duration: app_commands.Range[int, 60, 10080] = 1440,
) -> None:
    target_channel = channel or interaction.channel
    if not isinstance(target_channel, discord.TextChannel):
        await interaction.response.send_message("Retros must be started in a text channel.", ephemeral=True)
        return
    message = await target_channel.send(
        embed=discord.Embed(
            title=f"Retro: {title}",
            description="Threads created for each lane. Share feedback asynchronously before the live session.",
            colour=discord.Colour.purple(),
            timestamp=datetime.utcnow(),
        )
    )
    for lens in DEFAULT_RETRO_LENSES:
        thread_name = f"{title} – {lens}"
        await target_channel.create_thread(
            name=thread_name,
            message=message,
            auto_archive_duration=duration,
            reason="Retro lane setup",
        )
    await interaction.response.send_message("Retrospective created.", ephemeral=True)


bot.tree.add_command(retro_group)


async def main() -> None:
    await bot.start(bot.config.token)


if __name__ == "__main__":
    asyncio.run(main())
