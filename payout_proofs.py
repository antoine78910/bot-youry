from pathlib import Path

import discord

from channel_utils import delete_bot_messages

PAYOUT_PROOFS_TEMPLATE = "payout_proofs"
PROOFS_DIR = Path(__file__).parent / "assets" / "payout_proofs"

# Post order (01.png … 12.png)
PROOF_FILENAMES = [f"{i:02d}.png" for i in range(1, 13)]


def list_proof_image_paths() -> list[Path]:
    paths: list[Path] = []
    for name in PROOF_FILENAMES:
        path = PROOFS_DIR / name
        if path.is_file():
            paths.append(path)
    if paths:
        return paths
    return sorted(PROOFS_DIR.glob("*.png")) if PROOFS_DIR.is_dir() else []


async def publish_payout_proofs(
    channel: discord.TextChannel,
    bot_user: discord.ClientUser,
    *,
    clear_old: bool = True,
) -> None:
    """Post payout proof screenshots (one image per message)."""
    images = list_proof_image_paths()
    if not images:
        raise FileNotFoundError(
            f"No images in {PROOFS_DIR}. Add 01.png–12.png payout screenshots."
        )

    if clear_old:
        await delete_bot_messages(channel, bot_user)

    for image_path in images:
        await channel.send(file=discord.File(image_path))
