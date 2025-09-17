"""Provision a Discord guild using the Native Software blueprint.

The script reads ``server_spec.json`` and reconciles the target guild so that
roles, categories, channels, and webhooks match the specification. The created
artifacts and identifiers are persisted in ``server_state.json`` so the
configuration can be referenced by downstream automation (for example the ops
and AI bots).

Usage
-----
```
python create_discord_server.py
```
The script uses the following environment variables:
``DISCORD_BOT_TOKEN`` – token for a provisioning bot with administrator access.
``DISCORD_GUILD_ID`` – numeric guild identifier to configure.

The provisioning bot can be disabled after the server has been created.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import discord

ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "server_spec.json"
STATE_PATH = ROOT / "server_state.json"


@dataclass
class RoleSpec:
    """Data class describing a role defined in the specification."""

    name: str
    colour: str
    hoist: bool
    mentionable: bool
    permissions: Mapping[str, bool]

    def to_kwargs(self) -> Dict[str, Any]:
        colour_value = int(self.colour.lstrip("#"), 16)
        return {
            "name": self.name,
            "colour": discord.Colour(colour_value),
            "hoist": self.hoist,
            "mentionable": self.mentionable,
            "permissions": discord.Permissions(**self.permissions),
        }


@dataclass
class ChannelSpec:
    name: str
    type: str
    topic: Optional[str] = None
    slowmode_delay: Optional[int] = None
    bitrate: Optional[int] = None
    user_limit: Optional[int] = None
    overwrites: Optional[Mapping[str, Mapping[str, Iterable[str]]]] = None


@dataclass
class CategorySpec:
    name: str
    channels: List[ChannelSpec]


def load_spec() -> Dict[str, Any]:
    with SPEC_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_role_specs(data: Iterable[Mapping[str, Any]]) -> List[RoleSpec]:
    return [RoleSpec(**item) for item in data]


def build_category_specs(data: Iterable[Mapping[str, Any]]) -> List[CategorySpec]:
    categories: List[CategorySpec] = []
    for item in data:
        channels = [ChannelSpec(**channel) for channel in item.get("channels", [])]
        categories.append(CategorySpec(name=item["name"], channels=channels))
    return categories


def permission_overwrite_from_spec(
    overwrite_spec: Mapping[str, Mapping[str, Iterable[str]]],
    guild: discord.Guild,
    roles: Mapping[str, discord.Role],
) -> Dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    overwrites: Dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}
    for target_name, perms in overwrite_spec.items():
        target: discord.abc.Snowflake
        if target_name == "@everyone":
            target = guild.default_role
        else:
            role = roles.get(target_name)
            if role is None:
                raise ValueError(f"Role '{target_name}' referenced in overwrites does not exist yet.")
            target = role
        allow = perms.get("allow", [])
        deny = perms.get("deny", [])
        overwrite_kwargs: Dict[str, Optional[bool]] = {}
        for flag in allow:
            overwrite_kwargs[flag] = True
        for flag in deny:
            overwrite_kwargs[flag] = False
        overwrites[target] = discord.PermissionOverwrite(**overwrite_kwargs)
    return overwrites


async def ensure_role(guild: discord.Guild, spec: RoleSpec) -> discord.Role:
    existing = discord.utils.find(lambda r: r.name == spec.name, guild.roles)
    kwargs = spec.to_kwargs()
    if existing is None:
        return await guild.create_role(**kwargs, reason="Provisioning blueprint role")
    await existing.edit(**kwargs, reason="Reconciling blueprint role")
    return existing


async def ensure_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    existing = discord.utils.get(guild.categories, name=name)
    if existing is None:
        return await guild.create_category(name=name, reason="Provisioning blueprint category")
    return existing


async def ensure_text_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    spec: ChannelSpec,
    overwrites: Optional[Dict[discord.abc.Snowflake, discord.PermissionOverwrite]],
) -> discord.TextChannel:
    existing = discord.utils.get(category.text_channels, name=spec.name)
    if existing is None:
        channel = await category.create_text_channel(
            spec.name,
            topic=spec.topic,
            slowmode_delay=spec.slowmode_delay,
            overwrites=overwrites,
            reason="Provisioning blueprint text channel",
        )
        return channel
    await existing.edit(
        topic=spec.topic,
        slowmode_delay=spec.slowmode_delay,
        overwrites=overwrites,
        reason="Reconciling blueprint text channel",
    )
    return existing


async def ensure_voice_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    spec: ChannelSpec,
    overwrites: Optional[Dict[discord.abc.Snowflake, discord.PermissionOverwrite]],
) -> discord.VoiceChannel:
    existing = discord.utils.get(category.voice_channels, name=spec.name)
    bitrate = spec.bitrate or guild.bitrate_limit
    if existing is None:
        channel = await category.create_voice_channel(
            spec.name,
            bitrate=bitrate,
            user_limit=spec.user_limit or 0,
            overwrites=overwrites,
            reason="Provisioning blueprint voice channel",
        )
        return channel
    await existing.edit(
        bitrate=bitrate,
        user_limit=spec.user_limit or 0,
        overwrites=overwrites,
        reason="Reconciling blueprint voice channel",
    )
    return existing


async def ensure_stage_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    spec: ChannelSpec,
    overwrites: Optional[Dict[discord.abc.Snowflake, discord.PermissionOverwrite]],
) -> discord.StageChannel:
    existing = discord.utils.get(category.channels, name=spec.name, type=discord.ChannelType.stage_voice)
    if existing is None:
        channel = await guild.create_stage_channel(
            spec.name,
            topic=spec.topic,
            category=category,
            overwrites=overwrites,
            reason="Provisioning blueprint stage channel",
        )
        return channel
    await existing.edit(
        topic=spec.topic,
        category=category,
        overwrites=overwrites,
        reason="Reconciling blueprint stage channel",
    )
    return existing


async def ensure_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    spec: ChannelSpec,
    roles: Mapping[str, discord.Role],
) -> discord.abc.GuildChannel:
    overwrite_spec = spec.overwrites or {}
    overwrites = permission_overwrite_from_spec(overwrite_spec, guild, roles) if overwrite_spec else None
    channel_type = spec.type.lower()
    if channel_type == "text":
        return await ensure_text_channel(guild, category, spec, overwrites)
    if channel_type == "voice":
        return await ensure_voice_channel(guild, category, spec, overwrites)
    if channel_type == "stage":
        return await ensure_stage_channel(guild, category, spec, overwrites)
    raise ValueError(f"Unsupported channel type: {spec.type}")


async def ensure_webhook(
    channel: discord.TextChannel,
    name: str,
) -> discord.Webhook:
    existing = discord.utils.get(await channel.webhooks(), name=name)
    if existing is None:
        return await channel.create_webhook(name=name, reason="Provisioning blueprint webhook")
    return existing


async def provision() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    guild_id_str = os.environ.get("DISCORD_GUILD_ID")
    if not token or not guild_id_str:
        raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID must be set")

    spec = load_spec()
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:  # type: ignore[override]
        guild_id = int(guild_id_str)
        guild = client.get_guild(guild_id)
        if guild is None:
            raise RuntimeError(f"Bot is not a member of guild {guild_id}")

        role_specs = build_role_specs(spec.get("roles", []))
        role_objects: Dict[str, discord.Role] = {}
        for role_spec in role_specs:
            role = await ensure_role(guild, role_spec)
            role_objects[role.name] = role

        category_specs = build_category_specs(spec.get("categories", []))
        channel_state: Dict[str, Dict[str, int]] = {}
        for category_spec in category_specs:
            category = await ensure_category(guild, category_spec.name)
            category_channels: Dict[str, int] = {}
            for channel_spec in category_spec.channels:
                channel = await ensure_channel(guild, category, channel_spec, role_objects)
                category_channels[channel.name] = channel.id
            channel_state[category.name] = category_channels

        webhook_state: Dict[str, Dict[str, str]] = {}
        for webhook_spec in spec.get("webhooks", []):
            channel_name = webhook_spec["channel"]
            webhook_name = webhook_spec["name"]
            # Locate the text channel by traversing categories.
            target_channel: Optional[discord.TextChannel] = None
            for category in guild.categories:
                channel = discord.utils.get(category.text_channels, name=channel_name)
                if channel is not None:
                    target_channel = channel
                    break
            if target_channel is None:
                raise RuntimeError(f"Cannot create webhook '{webhook_name}' because channel '{channel_name}' was not found")
            webhook = await ensure_webhook(target_channel, webhook_name)
            webhook_state.setdefault(target_channel.name, {})[webhook_name] = webhook.url

        state_payload = {
            "guild_id": guild.id,
            "roles": {name: role.id for name, role in role_objects.items()},
            "categories": {category.name: category.id for category in guild.categories},
            "channels": channel_state,
            "webhooks": webhook_state,
        }
        STATE_PATH.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")

        for state_file in spec.get("state_files", []):
            if state_file == STATE_PATH.name:
                continue
            path = ROOT / state_file
            if not path.exists():
                path.write_text("{}\n", encoding="utf-8")

        await client.close()

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(provision())
