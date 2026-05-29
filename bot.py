import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from embed_utils import chunk_message
from embeds import MESSAGE_TEMPLATES
from publisher import load_channel_config, publish_template

load_dotenv()


def _clean_env(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip('"').strip("'")


TOKEN = _clean_env(os.getenv("DISCORD_TOKEN"))
AUTO_PUBLISH = _clean_env(os.getenv("AUTO_PUBLISH_ON_START", "true")).lower() in (
    "1",
    "true",
    "yes",
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def publish_all_channels() -> None:
    """Publie le bon template dans chaque salon configuré."""
    mapping = load_channel_config()
    if not mapping:
        print("Aucun salon dans channel_config.json")
        return

    for channel_id, template_name in mapping.items():
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            print(f"Salon {channel_id} introuvable (template: {template_name})")
            continue
        try:
            await publish_template(channel, template_name, bot.user)
            print(f"Publié '{template_name}' dans #{channel.name}")
        except Exception as exc:
            print(f"Erreur salon {channel_id}: {exc}")


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print("------")

    if AUTO_PUBLISH:
        await publish_all_channels()


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send("Pong !")


@bot.command(name="refresh")
async def refresh(ctx: commands.Context, template_name: str | None = None):
    """
    Met à jour ce salon : supprime les anciens messages du bot et renvoie l'embed.
    Usage : !refresh  ou  !refresh account_setup
    """
    mapping = load_channel_config()
    name = template_name or mapping.get(str(ctx.channel.id))

    if not name:
        await ctx.send(
            "Aucun template pour ce salon. Ajoute l'ID dans `channel_config.json` "
            "ou précise : `!refresh account_setup`"
        )
        return

    if name not in MESSAGE_TEMPLATES:
        await ctx.send(f"Template `{name}` introuvable dans embeds.py")
        return

    await publish_template(ctx.channel, name, bot.user)
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass


@bot.command(name="refreshall")
@commands.has_permissions(administrator=True)
async def refresh_all(ctx: commands.Context):
    """Met à jour tous les salons définis dans channel_config.json (admin)."""
    await publish_all_channels()
    await ctx.send("Tous les salons configurés ont été mis à jour.", delete_after=5)


@bot.command(name="say")
async def say(ctx: commands.Context, *, message: str):
    """Texte simple, découpé automatiquement si > 2000 caractères."""
    for part in chunk_message(message):
        await ctx.send(part)


@bot.command(name="templates")
async def list_templates(ctx: commands.Context):
    """Liste les templates disponibles."""
    names = "\n".join(f"• `{name}`" for name in MESSAGE_TEMPLATES)
    mapping = load_channel_config()
    channels = "\n".join(
        f"• <#{cid}> → `{tpl}`" for cid, tpl in mapping.items()
    ) or "_(aucun salon configuré)_"

    embed = discord.Embed(
        title="Templates & salons",
        color=0x3498DB,
    )
    embed.add_field(name="Templates", value=names, inline=False)
    embed.add_field(name="Salons configurés", value=channels, inline=False)
    await ctx.send(embed=embed)


def _validate_token(token: str) -> None:
    if token.isdigit():
        raise SystemExit(
            "DISCORD_TOKEN ressemble à un ID d'application. "
            "Va sur discord.com/developers → Bot → Reset Token."
        )
    if len(token) == 64 and all(c in "0123456789abcdef" for c in token.lower()):
        raise SystemExit(
            "DISCORD_TOKEN ressemble à la clé publique. "
            "Utilise le token sous Bot → Reset Token."
        )
    if token.count(".") != 2:
        raise SystemExit(
            "DISCORD_TOKEN invalide (format : xxx.yyy.zzz). "
            "Recopie le token sans guillemets ni espaces."
        )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant.")

    _validate_token(TOKEN)
    bot.run(TOKEN)
