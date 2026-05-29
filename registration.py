import os

import discord

from channel_utils import delete_bot_messages

REGISTRATION_TEMPLATE = "registration_welcome"

WELCOME_MESSAGE = """🚀 Welcome to the **Youry** Clipping Campaign
Click the button below to begin your registration.

You'll be asked for:
• Instagram username
• Phone Number
• Payout method (PayPal / Crypto / Bank Transfer)
• Payout details

Once you register, you're officially in the campaign — start clipping, posting, and earning right away."""


def _log_channel_id() -> int | None:
    raw = os.getenv("REGISTRATION_LOG_CHANNEL_ID", "").strip()
    if raw.isdigit():
        return int(raw)
    return None


class RegistrationModal(discord.ui.Modal, title="Youry Clipping Registration"):
    instagram = discord.ui.TextInput(
        label="Instagram Username (Clipping Account)",
        placeholder="@yourhandle",
        required=True,
        max_length=100,
    )
    phone = discord.ui.TextInput(
        label="Phone Number",
        placeholder="+1 555 555 5555",
        required=True,
        max_length=30,
    )
    payout_method = discord.ui.TextInput(
        label="Payout Method",
        placeholder="PayPal / Crypto / Bank Transfer",
        required=True,
        max_length=100,
    )
    payout_details = discord.ui.TextInput(
        label="Payout Details (email / wallet / bank)",
        placeholder="your@email.com / wallet address / IBAN...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📋 Nouvelle inscription — Youry Clipping",
            color=0x9B59B6,
        )
        embed.add_field(name="Utilisateur Discord", value=interaction.user.mention, inline=False)
        embed.add_field(name="ID Discord", value=str(interaction.user.id), inline=True)
        embed.add_field(
            name="Instagram Username",
            value=self.instagram.value or "—",
            inline=False,
        )
        embed.add_field(name="Phone Number", value=self.phone.value or "—", inline=False)
        embed.add_field(name="Payout Method", value=self.payout_method.value or "—", inline=False)
        embed.add_field(
            name="Payout Details",
            value=self.payout_details.value or "—",
            inline=False,
        )

        log_id = _log_channel_id()
        if log_id and interaction.client:
            log_channel = interaction.client.get_channel(log_id)
            if isinstance(log_channel, discord.TextChannel):
                await log_channel.send(embed=embed)

        await interaction.response.send_message(
            "✅ **Registration complete!** You're officially in the Youry Clipping campaign.",
            ephemeral=True,
        )


class RegisterView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.primary,
        custom_id="youry_clipping_register",
    )
    async def register(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_modal(RegistrationModal())


async def publish_registration_welcome(
    channel: discord.TextChannel,
    bot_user: discord.ClientUser,
    *,
    clear_old: bool = True,
) -> None:
    if clear_old:
        await delete_bot_messages(channel, bot_user)
    await channel.send(WELCOME_MESSAGE, view=RegisterView())
