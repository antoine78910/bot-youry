import asyncio
import json
import re
from pathlib import Path

import discord

from channel_utils import delete_bot_messages

CONTENT_GENERATOR_TEMPLATE = "content_generator_welcome"
CONTENT_COLOR = 0x57F287  # green accent like reference panel
CONFIG_PATH = Path(__file__).parent / "channel_config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _staff_role_ids() -> list[int]:
    ids: list[int] = []
    for raw in _load_config().get("staff_role_ids", []):
        if str(raw).isdigit():
            ids.append(int(raw))
    return ids


def _sanitize_username(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_-]", "", name.lower().replace(" ", "-"))
    return (cleaned or "user")[:90]


def thread_name_for(user: discord.User) -> str:
    return f"clips-{_sanitize_username(user.name)}"


def panel_embed() -> discord.Embed:
    return discord.Embed(
        title="🎬 Content Generator",
        description=(
            "Click a button below to generate a unique clip.\n\n"
            "**Generate Content** — 1 video\n"
            "**Batch Generate** — 3 videos (different hooks, body, music & effects)\n\n"
            "Each export gets random color, scale, rotation, text position & end cut."
        ),
        color=CONTENT_COLOR,
    )


def thread_welcome_embed(user: discord.User, mode: str) -> discord.Embed:
    mode_label = "Batch generate" if mode == "batch" else "Generate content"
    return discord.Embed(
        title="🎬 Your clips workspace",
        description=(
            f"Hey {user.mention} — welcome to your private clips thread.\n\n"
            f"You opened this via **{mode_label}**.\n\n"
            "Your generated clips will appear here as:\n"
            f"{user.mention} 🎬 + video file.\n\n"
            "Place assets in `assets/clips/` on the bot server "
            "(see `assets/clips/README.md`)."
        ),
        color=CONTENT_COLOR,
    )


async def _add_staff_to_thread(thread: discord.Thread) -> None:
    guild = thread.guild
    if guild is None:
        return
    for role_id in _staff_role_ids():
        role = guild.get_role(role_id)
        if role is None:
            continue
        for member in role.members:
            try:
                await thread.add_user(member)
            except discord.HTTPException:
                pass


async def find_clips_thread(
    channel: discord.TextChannel,
    user: discord.User,
) -> discord.Thread | None:
    name = thread_name_for(user)
    for thread in channel.threads:
        if thread.name == name:
            return thread
    try:
        async for thread in channel.archived_threads(limit=100):
            if thread.name == name:
                if thread.archived:
                    await thread.edit(archived=False)
                try:
                    await thread.add_user(user)
                except discord.HTTPException:
                    pass
                await _add_staff_to_thread(thread)
                return thread
    except discord.HTTPException:
        pass
    return None


async def get_or_create_clips_thread(
    channel: discord.TextChannel,
    member: discord.Member,
    *,
    mode: str,
) -> discord.Thread:
    existing = await find_clips_thread(channel, member)
    if existing:
        return existing

    thread = await channel.create_thread(
        name=thread_name_for(member),
        type=discord.ChannelType.private_thread,
        invitable=False,
        auto_archive_duration=10080,
        reason=f"Clips workspace for {member}",
    )
    await thread.add_user(member)
    await _add_staff_to_thread(thread)
    await thread.send(embed=thread_welcome_embed(member, mode))
    return thread


async def post_clip_to_thread(
    channel: discord.TextChannel,
    user: discord.User | discord.Member,
    video: discord.Attachment | discord.File | Path,
    *,
    caption_emoji: str = "🎬",
) -> discord.Message:
    """
    Deliver a generated clip to the user's private thread.
    Call this when the generation API is ready.
    """
    member = user if isinstance(user, discord.Member) else None
    if member is None and channel.guild:
        member = channel.guild.get_member(user.id)

    if member is None:
        raise ValueError("Member must be in the guild to resolve their clips thread.")

    thread = await find_clips_thread(channel, user)
    if thread is None:
        thread = await get_or_create_clips_thread(channel, member, mode="single")

    content = f"{user.mention} {caption_emoji}"
    if isinstance(video, Path):
        return await thread.send(content, file=discord.File(video))
    if isinstance(video, discord.File):
        return await thread.send(content, file=video)
    return await thread.send(content, file=await video.to_file())


async def _generate_clips_for_user(
    parent_channel: discord.TextChannel,
    member: discord.Member,
    thread: discord.Thread,
    *,
    count: int,
) -> tuple[int, str | None]:
    from clip_assembler import (
        ClipAssemblyError,
        assemble_clip,
        assets_status,
        recipe_summary,
    )

    status = assets_status()
    if not status["ffmpeg"]:
        return 0, "FFmpeg is not installed on the bot machine."
    if status["hooks"] < 1 or status["bodies"] < 1 or status["music"] < 1:
        return (
            0,
            "Missing clip assets. Add files to `assets/clips/hooks`, `body`, and `music`.",
        )

    progress = await thread.send(
        f"🎬 Generating **{count}** clip(s)… This can take 1–3 min each.",
    )
    created = 0
    last_error: str | None = None

    for index in range(count):
        try:
            output_path, recipe = await asyncio.to_thread(
                assemble_clip,
                seed=hash((member.id, index, progress.id)) & 0xFFFFFFFF,
            )
            await post_clip_to_thread(parent_channel, member, output_path)
            await thread.send(
                f"**Clip {index + 1}/{count}** — {recipe_summary(recipe)}",
                suppress_embeds=True,
            )
            output_path.unlink(missing_ok=True)
            created += 1
            if count == 1:
                await thread.send(f"✅ Clip ready — check the video above.")
            elif index + 1 == count:
                await thread.send(f"✅ All **{created}** clips are ready.")
        except ClipAssemblyError as exc:
            last_error = str(exc)
            await thread.send(f"❌ Clip {index + 1} failed: {exc}")
        except discord.HTTPException as exc:
            last_error = str(exc)
            await thread.send(f"❌ Could not upload clip {index + 1}: {exc}")

    try:
        await progress.delete()
    except discord.HTTPException:
        pass

    return created, last_error


async def _handle_clip_request(interaction: discord.Interaction, mode: str) -> None:
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(
            "This panel only works in a text channel.",
            ephemeral=True,
        )
        return

    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "Could not resolve your server membership.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        thread = await get_or_create_clips_thread(
            interaction.channel,
            interaction.user,
            mode=mode,
        )
    except discord.HTTPException as exc:
        await interaction.followup.send(
            f"Could not create your clips thread: {exc}",
            ephemeral=True,
        )
        return

    from clip_assembler import load_batch_size

    count = load_batch_size() if mode == "batch" else 1
    await interaction.followup.send(
        f"🎬 Generating **{count}** clip(s) in {thread.mention}. "
        "You'll get a ping when each video is ready (1–3 min each).",
        ephemeral=True,
    )

    created, error = await _generate_clips_for_user(
        interaction.channel,
        interaction.user,
        thread,
        count=count,
    )

    if created == 0 and error:
        await thread.send(f"❌ Generation failed: {error}")


class ContentGeneratorView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Generate Content",
        style=discord.ButtonStyle.success,
        emoji="🎬",
        custom_id="youry_content_generate",
    )
    async def generate_content(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await _handle_clip_request(interaction, mode="single")

    @discord.ui.button(
        label="Batch Generate",
        style=discord.ButtonStyle.primary,
        emoji="📦",
        custom_id="youry_content_batch",
    )
    async def batch_generate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await _handle_clip_request(interaction, mode="batch")


def content_generator_panel_fingerprint() -> str:
    from publish_sync import _embed_payload, _hash_payload

    return _hash_payload(
        {
            "embed": _embed_payload(panel_embed()),
            "buttons": ["youry_content_generate", "youry_content_batch"],
        }
    )


async def publish_content_generator_welcome(
    channel: discord.TextChannel,
    bot_user: discord.ClientUser,
    *,
    force: bool = False,
) -> list[int]:
    if force:
        await delete_bot_messages(channel, bot_user)
        sent = await channel.send(embed=panel_embed(), view=ContentGeneratorView())
        return [sent.id]

    from publish_sync import sync_embed_messages

    return await sync_embed_messages(
        channel, bot_user, [panel_embed()], view=ContentGeneratorView()
    )
