"""Generate default text-hook PNG overlays for ai / ugc / workflow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent / "assets" / "clips" / "hooks_text"

TEXTS = {
    "ai": 'Comment "AI" to try it out!',
    "ugc": 'Comment "UGC" to try',
    "workflow": 'Comment "Workflow" for the full workflow',
}

WIDTH = 1080
HEIGHT = 280


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "Arial Bold.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_label(text: str, dest: Path) -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(52)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    y = (HEIGHT - th) // 2

    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 220))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def main() -> None:
    for folder, line in TEXTS.items():
        _draw_label(line, ROOT / folder / "hook_text.png")
        print(f"Wrote {ROOT / folder / 'hook_text.png'}")


if __name__ == "__main__":
    main()
