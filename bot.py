import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

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
            await channel.send("Bot en ligne !")
        else:
            print(f"Canal introuvable pour DISCORD_CHANNEL_ID={CHANNEL_ID}")


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send("Pong !")


@bot.command(name="say")
async def say(ctx: commands.Context, *, message: str):
    await ctx.send(message)


@bot.command(name="send")
async def send_to_channel(ctx: commands.Context, channel_id: int, *, message: str):
    channel = bot.get_channel(channel_id)
    if channel is None:
        await ctx.send(f"Canal {channel_id} introuvable.")
        return
    await channel.send(message)
    await ctx.send(f"Message envoyé dans {channel.mention}.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant. Copie .env.example vers .env et remplis ton token.")

    bot.run(TOKEN)
