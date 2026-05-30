import hashlib
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


def proof_images_fingerprint() -> str:
    parts: list[str] = []
    for path in list_proof_image_paths():
        stat = path.stat()
        parts.append(f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


async def publish_payout_proofs(
    channel: discord.TextChannel,
    bot_user: discord.ClientUser,
    *,
    force: bool = False,
) -> list[int]:
    """Post payout proof screenshots (one image per message)."""
    images = list_proof_image_paths()
    if not images:
        raise FileNotFoundError(
            f"No images in {PROOFS_DIR}. Add 01.png–12.png payout screenshots."
        )

    from publish_sync import sync_image_messages

    return await sync_image_messages(channel, bot_user, images)
