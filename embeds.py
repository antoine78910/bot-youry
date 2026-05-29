"""Templates de messages — ajoute/modifie les entrées ici."""

import json
from pathlib import Path

EMBED_COLOR = 0x9B59B6
CONFIG_PATH = Path(__file__).parent / "channel_config.json"

# Labels affichés si l'ID du salon n'est pas dans channel_config.json
CHANNEL_LABELS = {
    "account_setup": "#👤-account-setup",
    "apply": "#🚀-apply",
    "warmup": "#🔥-warmup",
    "content_bot": "#🎬-content-bot",
    "payout_submission": "#💳-payout-submission",
}


def _load_channel_links() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): str(v) for k, v in data.get("channel_links", {}).items() if v}


def channel_mention(link_key: str) -> str:
    """Mention cliquable <#id> ou label #salon si ID manquant."""
    cid = _load_channel_links().get(link_key, "").strip()
    if cid.isdigit():
        return f"<#{cid}>"
    return CHANNEL_LABELS.get(link_key, f"#{link_key}")


def start_here_description() -> str:
    acc = channel_mention("account_setup")
    apply = channel_mention("apply")
    warmup = channel_mention("warmup")
    content = channel_mention("content_bot")

    return (
        "Welcome to **Youry** 👋\n"
        "You're just a few steps away from getting paid to post content.\n\n"
        "💰 **What You'll Earn**\n"
        "• $300 per 1M views\n\n"
        "🎯 **Your First 4 Actions**\n\n"
        f"Create a brand new Instagram account following {acc}\n\n"
        f"Register your account and enter payout details at {apply}\n\n"
        f"Warm up your account for 3 days {warmup}\n\n"
        f"Start posting using {content}"
    )


def payouts_description() -> str:
    payout_ch = channel_mention("payout_submission")

    return (
        "$300 per 1M views\n"
        "Minimum views for payout: 100k views\n"
        "Minimum T1 audience for payout: 20%\n\n"
        "Payouts are made by Bank Transfer, Paypal, or Cryptocurrency.\n"
        "Payouts are made bi-weekly.\n\n"
        f"Request payout? Go to {payout_ch}"
    )


MESSAGE_TEMPLATES: dict[str, dict] = {
    "start_here": {
        "title": "💸 YOURY CLIPPING — START HERE",
        "description": "",  # rempli dynamiquement via get_template()
        "color": EMBED_COLOR,
    },
    "payouts": {
        "title": "💸 YOURY CLIPPING — PAYOUTS",
        "description": "",
        "color": EMBED_COLOR,
    },
    "account_setup": {
        "title": "💸 YOURY CLIPPING — ACCOUNT SETUP",
        "description": (
            "Create a brand new Instagram account.\n\n"
            "**Username:** ai + American male name\n"
            "Examples: aibynick, aimoneynick, nickaiworkflow, nickusesai, "
            "nickteachesai, nickcreatesai, brysondoesai, aibrysonnnnn\n\n"
            "**Name:** Your American male name. Example: Nick\n\n"
            "**Profile Picture:**\n"
            "https://drive.google.com/REMPLACE_PAR_TON_LIEN\n\n"
            "**Bio:**\n"
            "Miami | Make money with AI influencers 💻\n"
            "Start generating now with @youry_ai\n\n"
            "**Bio link:**\n"
            "https://youry.com/\n\n"
            "*Only add the link once you have earned over 30k views on your account.*"
        ),
        "color": EMBED_COLOR,
    },
    "welcome": {
        "title": "👋 Bienvenue",
        "description": (
            "Bienvenue sur le serveur.\n\n"
            "Lis les règles et présente-toi dans le salon dédié."
        ),
        "color": EMBED_COLOR,
    },
    "rules": {
        "title": "📋 Règles",
        "fields": [
            {"name": "1. Respect", "value": "Sois respectueux envers tout le monde."},
            {"name": "2. Pas de spam", "value": "Pas de pub ni de spam."},
            {"name": "3. Contenu", "value": "Pas de contenu illégal ou NSFW."},
        ],
        "color": EMBED_COLOR,
    },
    "bot_online": {
        "title": "✅ Youry est en ligne",
        "description": "Messages à jour. Utilise `!refresh` pour mettre à jour ce salon.",
        "color": EMBED_COLOR,
    },
}


def get_template(name: str) -> dict | None:
    """Retourne une copie du template (start_here = mentions à jour)."""
    template = MESSAGE_TEMPLATES.get(name)
    if not template:
        return None
    result = dict(template)
    if name == "start_here":
        result["description"] = start_here_description()
    elif name == "payouts":
        result["description"] = payouts_description()
    return result
