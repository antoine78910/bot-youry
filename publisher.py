import json
from pathlib import Path

import discord

from channel_utils import delete_bot_messages
from embed_utils import build_embeds_from_template
from embeds import MESSAGE_TEMPLATES, get_template

CONFIG_PATH = Path(__file__).parent / "channel_config.json"

def load_channel_config() -> dict[str, str]:
    """Retourne {channel_id: template_name}."""
    if not CONFIG_PATH.exists():
        return {}

    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    return {str(k): v for k, v in data.get("channels", {}).items()}


def _load_special_publishers() -> dict:
    from registration import REGISTRATION_TEMPLATE, publish_registration_welcome

    return {REGISTRATION_TEMPLATE: publish_registration_welcome}


async def publish_channel(
    channel: discord.TextChannel,
    template_name: str,
    bot_user: discord.ClientUser,
    *,
    clear_old: bool = True,
) -> None:
    """Supprime les anciens messages du bot puis publie le contenu du salon."""
    special = _load_special_publishers()
    if template_name in special:
        await special[template_name](channel, bot_user, clear_old=clear_old)
        return

    template = get_template(template_name)
    if not template:
        raise ValueError(f"Template inconnu : {template_name}")

    if clear_old:
        await delete_bot_messages(channel, bot_user)

    embeds = build_embeds_from_template(template)
    for i in range(0, len(embeds), 10):
        await channel.send(embeds=embeds[i : i + 10])


async def publish_template(
    channel: discord.TextChannel,
    template_name: str,
    bot_user: discord.ClientUser,
    *,
    clear_old: bool = True,
) -> None:
    """Alias pour compatibilité."""
    await publish_channel(channel, template_name, bot_user, clear_old=clear_old)
