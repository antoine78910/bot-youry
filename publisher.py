import json
from pathlib import Path

import discord

from embed_utils import build_embeds_from_template
from embeds import MESSAGE_TEMPLATES

CONFIG_PATH = Path(__file__).parent / "channel_config.json"


def load_channel_config() -> dict[str, str]:
    """Retourne {channel_id: template_name}."""
    if not CONFIG_PATH.exists():
        return {}

    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    return {str(k): v for k, v in data.get("channels", {}).items()}


async def delete_bot_messages(channel: discord.TextChannel, bot_user: discord.ClientUser) -> int:
    """Supprime les anciens messages du bot dans ce salon (max 14 jours pour bulk)."""
    deleted = 0
    async for message in channel.history(limit=100):
        if message.author.id != bot_user.id:
            continue
        try:
            await message.delete()
            deleted += 1
        except discord.HTTPException:
            pass
    return deleted


async def publish_template(
    channel: discord.TextChannel,
    template_name: str,
    bot_user: discord.ClientUser,
    *,
    clear_old: bool = True,
) -> None:
    """Supprime les anciens messages du bot puis envoie le template."""
    template = MESSAGE_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template inconnu : {template_name}")

    if clear_old:
        await delete_bot_messages(channel, bot_user)

    embeds = build_embeds_from_template(template)
    for i in range(0, len(embeds), 10):
        await channel.send(embeds=embeds[i : i + 10])
