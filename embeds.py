"""Templates de messages — ajoute/modifie les entrées ici."""

EMBED_COLOR = 0x9B59B6

# Chaque clé = un type de message réutilisable dans channel_config.json
MESSAGE_TEMPLATES: dict[str, dict] = {
    "account_setup": {
        "title": "💸 EROMIFY CLIPPING — ACCOUNT SETUP",
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
            "Start generating now with @eromify_ai\n\n"
            "**Bio link:**\n"
            "https://eromify.com/\n\n"
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
