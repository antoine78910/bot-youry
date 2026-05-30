"""Assemble hook + body + music with anti-duplicate visual variations (FFmpeg)."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

CLIPS_ROOT = Path(__file__).parent / "assets" / "clips"
HOOKS_DIR = CLIPS_ROOT / "hooks"
HOOKS_TEXT_DIR = CLIPS_ROOT / "hooks_text"
BODY_DIR = CLIPS_ROOT / "body"
MUSIC_DIR = CLIPS_ROOT / "music"
OUTPUT_DIR = CLIPS_ROOT / "output"

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac"}
TEXT_EXT = {".png", ".mp4", ".mov", ".webm"}

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30


@dataclass
class ClipRecipe:
    hook: Path
    body: Path
    music: Path
    text_hook: Path | None
    text_category: str | None
    scale: float
    rotation_deg: float
    saturation: float
    brightness: float
    contrast: float
    end_trim_sec: float
    text_position: str


class ClipAssemblyError(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _list_files(folder: Path, extensions: set[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith(".")
    )


def _pick_text_hook(rng: random.Random) -> tuple[Path | None, str | None]:
    if not HOOKS_TEXT_DIR.is_dir():
        return None, None

    categories = [
        d
        for d in HOOKS_TEXT_DIR.iterdir()
        if d.is_dir() and _list_files(d, TEXT_EXT | VIDEO_EXT)
    ]
    if categories:
        category = rng.choice(categories)
        chosen = rng.choice(_list_files(category, TEXT_EXT | VIDEO_EXT))
        return chosen, category.name

    root_files = _list_files(HOOKS_TEXT_DIR, TEXT_EXT | VIDEO_EXT)
    if root_files:
        return rng.choice(root_files), "default"
    return None, None


def _random_recipe(rng: random.Random) -> ClipRecipe:
    hooks = _list_files(HOOKS_DIR, VIDEO_EXT)
    bodies = _list_files(BODY_DIR, VIDEO_EXT)
    tracks = _list_files(MUSIC_DIR, AUDIO_EXT)

    if not hooks:
        raise ClipAssemblyError(f"No videos in {HOOKS_DIR} — add at least one hook.")
    if not bodies:
        raise ClipAssemblyError(f"No videos in {BODY_DIR} — add at least one body clip.")
    if not tracks:
        raise ClipAssemblyError(f"No audio in {MUSIC_DIR} — add at least one music track.")

    text_hook, text_category = _pick_text_hook(rng)
    positions = ["top", "upper", "center", "lower", "bottom"]

    return ClipRecipe(
        hook=rng.choice(hooks),
        body=rng.choice(bodies),
        music=rng.choice(tracks),
        text_hook=text_hook,
        text_category=text_category,
        scale=rng.uniform(1.0, 1.05),
        rotation_deg=rng.uniform(-0.5, 0.5),
        saturation=rng.uniform(0.92, 1.1),
        brightness=rng.uniform(-0.04, 0.04),
        contrast=rng.uniform(0.94, 1.06),
        end_trim_sec=rng.uniform(0.08, 0.25),
        text_position=rng.choice(positions),
    )


MAX_UPLOAD_BYTES = 24 * 1024 * 1024


def _run_ffmpeg(args: list[str], *, timeout: int = 600) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]
    try:
        subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")[-800:]
        raise ClipAssemblyError(f"FFmpeg failed: {stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ClipAssemblyError("FFmpeg timed out.") from exc


def _ensure_upload_size(path: Path) -> Path:
    """Re-encode if the file exceeds Discord's upload limit."""
    if path.stat().st_size <= MAX_UPLOAD_BYTES:
        return path

    smaller = path.with_name(f"{path.stem}_compressed.mp4")
    _run_ffmpeg(
        [
            "-i",
            str(path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(smaller),
        ]
    )
    if smaller.stat().st_size <= MAX_UPLOAD_BYTES:
        path.unlink(missing_ok=True)
        return smaller
    return path


def _overlay_xy(position: str, margin: int = 48) -> tuple[str, str]:
    """Return ffmpeg overlay expressions for x and y."""
    mapping = {
        "top": (f"(main_w-overlay_w)/2", str(margin)),
        "upper": (f"(main_w-overlay_w)/2", f"main_h*0.18"),
        "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
        "lower": (f"(main_w-overlay_w)/2", f"main_h*0.62"),
        "bottom": (f"(main_w-overlay_w)/2", f"main_h-overlay_h-{margin}"),
    }
    return mapping.get(position, mapping["center"])


def assemble_clip(
    output_path: Path | None = None,
    *,
    seed: int | None = None,
) -> tuple[Path, ClipRecipe]:
    """
    Build one vertical clip. Returns (output_path, recipe used).
  """
    if not ffmpeg_available():
        raise ClipAssemblyError(
            "FFmpeg is not installed. Install it and add ffmpeg to your PATH."
        )

    rng = random.Random(seed)
    recipe = _random_recipe(rng)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = OUTPUT_DIR / f"clip_{uuid.uuid4().hex}.mp4"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_concat = OUTPUT_DIR / f"_concat_{uuid.uuid4().hex}.mp4"
    temp_video = OUTPUT_DIR / f"_video_{uuid.uuid4().hex}.mp4"

    try:
        _concat_hook_body(recipe, temp_concat)
        _apply_variations_and_audio(recipe, temp_concat, temp_video)
        _finalize_trim(recipe, temp_video, output_path)
        output_path = _ensure_upload_size(output_path)
    finally:
        temp_concat.unlink(missing_ok=True)
        temp_video.unlink(missing_ok=True)

    return output_path, recipe


def _concat_hook_body(recipe: ClipRecipe, dest: Path) -> None:
    """Normalize hook + body to 1080x1920 @ 30fps and concatenate."""
    scale_crop = (
        f"fps={OUTPUT_FPS},"
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
        "setsar=1"
    )
    filter_complex = (
        f"[0:v]{scale_crop}[v0];"
        f"[1:v]{scale_crop}[v1];"
        f"[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];"
        f"[1:a]aresample=44100,aformat=channel_layouts=stereo[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    _run_ffmpeg(
        [
            "-i",
            str(recipe.hook),
            "-i",
            str(recipe.body),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(dest),
        ]
    )


def _apply_variations_and_audio(recipe: ClipRecipe, source: Path, dest: Path) -> None:
    rot_rad = recipe.rotation_deg * 3.14159265 / 180.0
    ox, oy = _overlay_xy(recipe.text_position)

    video_chain = (
        f"eq=saturation={recipe.saturation}:brightness={recipe.brightness}:"
        f"contrast={recipe.contrast},"
        f"rotate={rot_rad}:fillcolor=black@0:ow=iw:oh=ih,"
        f"scale=iw*{recipe.scale}:ih*{recipe.scale},"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}"
    )

    inputs = ["-i", str(source), "-i", str(recipe.music)]
    filter_parts = [f"[0:v]{video_chain}[vbase]"]

    if recipe.text_hook and recipe.text_hook.suffix.lower() == ".png":
        inputs.extend(["-i", str(recipe.text_hook)])
        filter_parts.append(
            f"[vbase][2:v]overlay=x={ox}:y={oy}:enable='lt(t,2.5)'[vout]"
        )
        vout = "[vout]"
    elif recipe.text_hook and recipe.text_hook.suffix.lower() in {".mp4", ".mov", ".webm"}:
        inputs.extend(["-i", str(recipe.text_hook)])
        filter_parts.append(
            f"[2:v]scale={OUTPUT_WIDTH}:-1[txt];"
            f"[vbase][txt]overlay=x={ox}:y={oy}:enable='lt(t,2.5)'[vout]"
        )
        vout = "[vout]"
    else:
        filter_parts.append("[vbase]copy[vout]")
        vout = "[vout]"

    filter_parts.append(
        f"[0:a]volume=1.0[va];"
        f"[1:a]volume=0.18[vm];"
        f"[va][vm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
    )

    _run_ffmpeg(
        inputs
        + [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            vout,
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(dest),
        ]
    )


def _finalize_trim(recipe: ClipRecipe, source: Path, dest: Path) -> None:
    """Mini end cut — shave a few frames off the tail."""
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(probe.stdout.strip())
    end = max(0.5, duration - recipe.end_trim_sec)

    _run_ffmpeg(
        [
            "-i",
            str(source),
            "-t",
            f"{end:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(dest),
        ]
    )


def recipe_summary(recipe: ClipRecipe) -> str:
    text = recipe.text_hook.name if recipe.text_hook else "none"
    return (
        f"Hook `{recipe.hook.name}` + body `{recipe.body.name}` + `{recipe.music.name}`\n"
        f"Text: `{text}` ({recipe.text_category or '—'}) @ {recipe.text_position}\n"
        f"Variations: scale {recipe.scale:.2%}, rot {recipe.rotation_deg:+.2f}°, "
        f"end trim {recipe.end_trim_sec:.2f}s"
    )


def assets_status() -> dict:
    return {
        "ffmpeg": ffmpeg_available(),
        "hooks": len(_list_files(HOOKS_DIR, VIDEO_EXT)),
        "bodies": len(_list_files(BODY_DIR, VIDEO_EXT)),
        "music": len(_list_files(MUSIC_DIR, AUDIO_EXT)),
        "text_hooks": sum(
            len(_list_files(HOOKS_TEXT_DIR / d, TEXT_EXT | VIDEO_EXT))
            for d in HOOKS_TEXT_DIR.iterdir()
            if d.is_dir()
        )
        if HOOKS_TEXT_DIR.is_dir()
        else 0,
    }


def load_batch_size() -> int:
    config_path = Path(__file__).parent / "channel_config.json"
    if config_path.exists():
        with config_path.open(encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("clip_batch_size", 3)
        if str(raw).isdigit():
            return max(1, min(10, int(raw)))
    return 3
