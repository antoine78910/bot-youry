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
    "Feels like bitcoin in 2009",
    "How this is legal ??",
    "Got fired by my agency so i'm leaking their ENTIRE process",
    "How is this website even legal",
    "I'm so bad at marketing .. do this instead",
    "How on earth is this legal ?!",
]

WIDTH = 1080
MAX_HEIGHT = 560
H_PADDING = 40
V_PADDING = 40
MAX_FONT_SIZE = 78
MIN_FONT_SIZE = 44
TEXT_SCALE_X = 1.14
STROKE_OFFSETS = (
    (-4, 0),
    (4, 0),
    (0, -4),
    (0, 4),
    (-3, -3),
    (3, -3),
    (-3, 3),
    (3, 3),
    (-2, -2),
    (2, -2),
    (-2, 2),
    (2, 2),
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:72] or "hook"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Prefer the OS system UI bold font (Segoe UI Bold on Windows)."""
    candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)

    for name in ("segoeuib.ttf", "Segoe UI Bold.ttf", "segoeui.ttf", "arialbd.ttf"):
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


def _line_size(line: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int]:
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), line, font=font)
    width = int((bbox[2] - bbox[0]) * TEXT_SCALE_X)
    height = bbox[3] - bbox[1]
    return width, height


def _measure_block(
    lines: list[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    max_w = 0
    total_h = 0
    line_gap = 8
    for index, line in enumerate(lines):
        line_w, line_h = _line_size(line, font)
        max_w = max(max_w, line_w)
        total_h += line_h
        if index < len(lines) - 1:
            total_h += line_gap
    return max_w, total_h


def _layout(text: str) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        font = _font(size)
        lines = _wrap_lines(text, font)
        block_w, block_h = _measure_block(lines, font)
        if block_w <= WIDTH - H_PADDING * 2 and block_h <= MAX_HEIGHT - V_PADDING * 2:
            return font, lines

    font = _font(MIN_FONT_SIZE)
    return font, _wrap_lines(text, font)


def _render_line(line: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> Image.Image:
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), line, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = 12

    layer = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = pad - bbox[0]
    y = pad - bbox[1]

    for dx, dy in STROKE_OFFSETS:
        draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    stretched_w = max(1, int(layer.width * TEXT_SCALE_X))
    return layer.resize((stretched_w, layer.height), Image.Resampling.LANCZOS)


def _draw_label(text: str, dest: Path) -> None:
    font, lines = _layout(text)
    _, block_h = _measure_block(lines, font)

    img = Image.new("RGBA", (WIDTH, block_h + V_PADDING * 2), (0, 0, 0, 0))
    line_gap = 8
    y = V_PADDING

    for line in lines:
        line_img = _render_line(line, font)
        x = (WIDTH - line_img.width) // 2
        img.alpha_composite(line_img, (x, y))
        y += line_img.height + line_gap

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def main() -> None:
    for line in HOOK_LINES:
        dest = ROOT / f"{_slug(line)}.png"
        _draw_label(line, dest)
        print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
