import discord

# Couleur de la barre à gauche (bleu comme sur ton exemple)
EMBED_COLOR = 0x3498DB


def account_setup_embed() -> discord.Embed:
    """Message structuré type EROMIFY — modifie le texte ici."""
    return discord.Embed(
        title="💸 EROMIFY CLIPPING — ACCOUNT SETUP",
        description=(
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
        color=EMBED_COLOR,
    )


def bot_online_embed() -> discord.Embed:
    return discord.Embed(
        title="✅ Youry est en ligne",
        description="Le bot est prêt. Utilise `!setup` pour envoyer le guide de configuration.",
        color=EMBED_COLOR,
    )
