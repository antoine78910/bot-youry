import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from embeds import account_setup_embed, bot_online_embed

load_dotenv()


def _clean_env(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().strip('"').strip("'")


TOKEN = _clean_env(os.getenv("DISCORD_TOKEN"))
CHANNEL_ID = _clean_env(os.getenv("DISCORD_CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print("------")

    if CHANNEL_ID:
        channel = bot.get_channel(int(CHANNEL_ID))
        if channel:
            await channel.send(embed=bot_online_embed())
        else:
            print(f"Canal introuvable pour DISCORD_CHANNEL_ID={CHANNEL_ID}")


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send("Pong !")


@bot.command(name="say")
async def say(ctx: commands.Context, *, message: str):
    await ctx.send(message)


@bot.command(name="setup")
async def setup(ctx: commands.Context):
    """Envoie le guide de configuration (embed structuré)."""
    await ctx.send(embed=account_setup_embed())


@bot.command(name="embed")
async def embed_cmd(ctx: commands.Context, title: str, *, description: str):
    """Embed personnalisé : !embed "Mon titre" Texte du message"""
    embed = discord.Embed(title=title, description=description, color=0x3498DB)
    await ctx.send(embed=embed)


@bot.command(name="send")
async def send_to_channel(ctx: commands.Context, channel_id: int, *, message: str):
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send(f"Canal {channel_id} introuvable.")
        return
    await channel.send(message)
    await ctx.send(f"Message envoyé dans {channel.mention}.", embed=discord.Embed(
        description=f"Message envoyé dans {channel.mention}.",
        color=0x3498DB,
    ))


@bot.command(name="sendsetup")
async def send_setup(ctx: commands.Context, channel_id: int):
    """Envoie le guide setup dans un salon : !sendsetup 123456789"""
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send("Salon introuvable.")
        return
    await channel.send(embed=account_setup_embed())
    await ctx.send(embed=discord.Embed(
        description=f"Guide envoyé dans {channel.mention}.",
        color=0x3498DB,
    ))


def _validate_token(token: str) -> None:
    if token.isdigit():
        raise SystemExit(
            "DISCORD_TOKEN ressemble à un ID d'application, pas au token du bot. "
            "Va sur discord.com/developers → Bot → Reset Token."
        )
    if len(token) == 64 and all(c in "0123456789abcdef" for c in token.lower()):
        raise SystemExit(
            "DISCORD_TOKEN ressemble à la clé publique, pas au token du bot. "
            "Utilise le token sous Bot → Reset Token."
        )
    if token.count(".") != 2:
        raise SystemExit(
            "DISCORD_TOKEN invalide (format attendu : xxx.yyy.zzz). "
            "Recopie le token depuis Bot → Reset Token, sans guillemets ni espaces."
        )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant. Définis la variable sur Railway ou dans .env.")

    _validate_token(TOKEN)
    bot.run(TOKEN)
