"""Generate text-hook PNG overlays (one file per hook line)."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent / "assets" / "clips" / "hooks_text" / "lines"

HOOK_LINES = [
    "the art of youry",
    "This tool just replaced your ENTIRE marketing team",
    "I could literally KISS the business owner that showed me this",
    "This method is replacing marketing agencies",
    "AI just killed marketing agencies",
    "Save this before they take it down",
    "This feels illegal to know",
    "My secret AI stack revealed",
    "AI on steroids",
]

WIDTH = 1080
MAX_HEIGHT = 420
H_PADDING = 48
V_PADDING = 36
MAX_FONT_SIZE = 56
MIN_FONT_SIZE = 34


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:72] or "hook"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "Arial Bold.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_lines(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> list[str]:
    words = text.split()
    if not words:
        return [text]

    for width in (22, 18, 14, 12, 10):
        wrapped = textwrap.wrap(text, width=width)
        if len(wrapped) <= 3:
            return wrapped

    return textwrap.wrap(text, width=10)


def _measure_block(
    lines: list[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
) -> tuple[int, int]:
    max_w = 0
    total_h = 0
    line_gap = 8
    for index, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        max_w = max(max_w, bbox[2] - bbox[0])
        total_h += bbox[3] - bbox[1]
        if index < len(lines) - 1:
            total_h += line_gap
    return max_w, total_h


def _layout(text: str) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    probe = Image.new("RGBA", (WIDTH, MAX_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)

    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        font = _font(size)
        lines = _wrap_lines(text, font)
        block_w, block_h = _measure_block(lines, font, draw)
        if block_w <= WIDTH - H_PADDING * 2 and block_h <= MAX_HEIGHT - V_PADDING * 2:
            return font, lines

    font = _font(MIN_FONT_SIZE)
    return font, _wrap_lines(text, font)


def _draw_label(text: str, dest: Path) -> None:
    font, lines = _layout(text)
    probe = Image.new("RGBA", (WIDTH, MAX_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    _, block_h = _measure_block(lines, font, draw)

    img = Image.new("RGBA", (WIDTH, block_h + V_PADDING * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    line_gap = 8
    y = V_PADDING

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (WIDTH - tw) // 2

        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 220))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += th + line_gap

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def main() -> None:
    for line in HOOK_LINES:
        dest = ROOT / f"{_slug(line)}.png"
        _draw_label(line, dest)
        print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
