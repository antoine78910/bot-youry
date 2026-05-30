"""Assemble hook + body + music with anti-duplicate visual variations (FFmpeg)."""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CLIPS_ROOT = Path(__file__).parent / "assets" / "clips"


@lru_cache(maxsize=1)
def clips_root() -> Path:
    """Root folder for hook/body/music assets (override with CLIPS_ASSETS_DIR)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=True)
    except ImportError:
        pass

    override = os.getenv("CLIPS_ASSETS_DIR", "").strip().strip('"').strip("'")
    if override:
        path = Path(override)
        if path.is_dir():
            return path.resolve()
    return CLIPS_ROOT.resolve()


def hooks_dir() -> Path:
    return clips_root() / "hooks"


def hooks_text_dir() -> Path:
    return clips_root() / "hooks_text"


def body_dir() -> Path:
    return clips_root() / "body"


def music_dir() -> Path:
    return clips_root() / "music"


def output_dir() -> Path:
    return clips_root() / "output"

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac"}
TEXT_EXT = {".png", ".mp4", ".mov", ".webm"}

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS = 30
MUSIC_VOLUME = 0.42
ENCODE_PRESET = "veryfast"
ENCODE_CRF = "22"
TEXT_OVERLAY_SEC = 2.5


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


@lru_cache(maxsize=1)
def resolve_ffmpeg_bin() -> str | None:
    """Find ffmpeg.exe even when it is not on PATH (WinGet, FFMPEG_PATH, bundled)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=True)
    except ImportError:
        pass

    env_path = os.getenv("FFMPEG_PATH", "").strip().strip('"').strip("'")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return str(candidate)
        nested = candidate / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if nested.is_file():
            return str(nested)
        from_path = shutil.which(env_path)
        if from_path:
            return from_path

    from_path = shutil.which("ffmpeg")
    if from_path:
        return from_path

    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "")
        winget_root = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if winget_root.is_dir():
            for exe in winget_root.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
                if exe.is_file():
                    return str(exe)

        for fixed in (
            Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
            Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        ):
            if fixed.is_file():
                return str(fixed)

    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).is_file():
            return bundled
    except ImportError:
        pass

    return None


def resolve_ffprobe_bin() -> str | None:
    ffmpeg_bin = resolve_ffmpeg_bin()
    if ffmpeg_bin:
        probe = Path(ffmpeg_bin).with_name(
            "ffprobe.exe" if os.name == "nt" else "ffprobe"
        )
        if probe.is_file():
            return str(probe)

    from_path = shutil.which("ffprobe")
    return from_path


def ffmpeg_available() -> bool:
    return resolve_ffmpeg_bin() is not None


def _require_ffmpeg() -> str:
    binary = resolve_ffmpeg_bin()
    if not binary:
        raise ClipAssemblyError(
            "FFmpeg not found. Install FFmpeg, add it to PATH, or set "
            "FFMPEG_PATH in .env to the full path of ffmpeg.exe."
        )
    return binary


def _list_files(folder: Path, extensions: set[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith(".")
    )


def _pick_text_hook(rng: random.Random) -> tuple[Path | None, str | None]:
    if not hooks_text_dir().is_dir():
        return None, None

    categories = [
        d
        for d in hooks_text_dir().iterdir()
        if d.is_dir() and _list_files(d, TEXT_EXT | VIDEO_EXT)
    ]
    if categories:
        category = rng.choice(categories)
        chosen = rng.choice(_list_files(category, TEXT_EXT | VIDEO_EXT))
        return chosen, category.name

    root_files = _list_files(hooks_text_dir(), TEXT_EXT | VIDEO_EXT)
    if root_files:
        return rng.choice(root_files), "default"
    return None, None


def _random_recipe(rng: random.Random) -> ClipRecipe:
    hooks = _list_files(hooks_dir(), VIDEO_EXT)
    bodies = _list_files(body_dir(), VIDEO_EXT)
    tracks = _list_files(music_dir(), AUDIO_EXT)

    if not hooks:
        raise ClipAssemblyError(
            f"No videos in {hooks_dir()} — add at least one hook."
        )
    if not bodies:
        raise ClipAssemblyError(
            f"No videos in {body_dir()} — add at least one body clip."
        )
    if not tracks:
        raise ClipAssemblyError(
            f"No audio in {music_dir()} — add at least one music track."
        )

    text_hook, text_category = _pick_text_hook(rng)

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
        text_position="top",
    )


MAX_UPLOAD_BYTES = 24 * 1024 * 1024


def _run_ffmpeg(args: list[str], *, timeout: int = 600) -> None:
    cmd = [_require_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *args]
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
            ENCODE_PRESET,
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


def _overlay_xy(position: str, margin: int = 64) -> tuple[str, str]:
    """Return ffmpeg overlay expressions for x and y."""
    mapping = {
        "top": (f"(main_w-overlay_w)/2", str(margin)),
        "upper": (f"(main_w-overlay_w)/2", f"main_h*0.18"),
        "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
        "lower": (f"(main_w-overlay_w)/2", f"main_h*0.62"),
        "bottom": (f"(main_w-overlay_w)/2", f"main_h-overlay_h-{margin}"),
    }
    return mapping.get(position, mapping["top"])


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
            "FFmpeg not found. Install FFmpeg, add it to PATH, or set "
            "FFMPEG_PATH in .env to the full path of ffmpeg.exe."
        )

    rng = random.Random(seed)
    recipe = _random_recipe(rng)

    output_dir().mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = output_dir() / f"clip_{uuid.uuid4().hex}.mp4"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _render_clip(recipe, output_path)
        output_path = _ensure_upload_size(output_path)
    except ClipAssemblyError:
        output_path.unlink(missing_ok=True)
        raise

    return output_path, recipe


def _scale_crop_filter() -> str:
    return (
        f"fps={OUTPUT_FPS},"
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
        "setsar=1"
    )


def _render_clip(recipe: ClipRecipe, dest: Path) -> None:
    """
    Single-pass render: hook (silent) + body + music + text overlay + variations.
    Faster than the old 3-pass pipeline (~15–30s depending on clip length).
    """
    hook_dur = _probe_duration(recipe.hook)
    body_dur = _probe_duration(recipe.body)
    total_dur = max(0.5, hook_dur + body_dur - recipe.end_trim_sec)

    scale_crop = _scale_crop_filter()
    rot_rad = recipe.rotation_deg * 3.14159265 / 180.0
    ox, oy = _overlay_xy(recipe.text_position)
    enable = f"lt(t,{TEXT_OVERLAY_SEC})"

    video_var = (
        f"eq=saturation={recipe.saturation}:brightness={recipe.brightness}:"
        f"contrast={recipe.contrast},"
        f"rotate={rot_rad}:fillcolor=black@0:ow=iw:oh=ih,"
        f"scale=iw*{recipe.scale}:ih*{recipe.scale},"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}"
    )

    inputs = ["-i", str(recipe.hook), "-i", str(recipe.body), "-i", str(recipe.music)]
    filter_parts = [
        f"[0:v]{scale_crop}[v0]",
        f"[1:v]{scale_crop}[v1]",
        f"[v0][v1]concat=n=2:v=1:a=0[vconcat]",
        f"anullsrc=r=44100:cl=stereo,atrim=duration={hook_dur:.3f}[silence]",
        (
            f"[1:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"apad=whole_dur={body_dur:.3f},atrim=duration={body_dur:.3f}[bodya]"
        ),
        f"[silence][bodya]concat=n=2:v=0:a=1[maina]",
        f"[vconcat]{video_var}[vbase]",
    ]

    if recipe.text_hook and recipe.text_hook.suffix.lower() == ".png":
        inputs.extend(["-i", str(recipe.text_hook)])
        filter_parts.append(
            f"[vbase][3:v]overlay=x={ox}:y={oy}:enable='{enable}'[vout]"
        )
        vout = "[vout]"
    elif recipe.text_hook and recipe.text_hook.suffix.lower() in {".mp4", ".mov", ".webm"}:
        inputs.extend(["-i", str(recipe.text_hook)])
        filter_parts.append(
            f"[3:v]scale={OUTPUT_WIDTH}:-1[txt];"
            f"[vbase][txt]overlay=x={ox}:y={oy}:enable='{enable}'[vout]"
        )
        vout = "[vout]"
    else:
        filter_parts.append("[vbase]copy[vout]")
        vout = "[vout]"

    filter_parts.extend(
        [
            f"[maina]volume=1.0[va]",
            (
                f"[2:a]aresample=44100,aformat=channel_layouts=stereo,"
                f"volume={MUSIC_VOLUME},aloop=loop=-1:size=2e+09,"
                f"atrim=duration={total_dur:.3f}[vm]"
            ),
            f"[va][vm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        ]
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
            "-t",
            f"{total_dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            ENCODE_PRESET,
            "-crf",
            ENCODE_CRF,
            "-threads",
            "0",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )


def _probe_duration(source: Path) -> float:
    ffprobe = resolve_ffprobe_bin()
    if ffprobe:
        probe = subprocess.run(
            [
                ffprobe,
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
        return float(probe.stdout.strip())

    ffmpeg_bin = _require_ffmpeg()
    proc = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-i", str(source), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        proc.stderr,
    )
    if not match:
        raise ClipAssemblyError("Could not read video duration.")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def recipe_summary(recipe: ClipRecipe) -> str:
    text = recipe.text_hook.name if recipe.text_hook else "none"
    return (
        f"Hook `{recipe.hook.name}` + body `{recipe.body.name}` + `{recipe.music.name}`\n"
        f"Text: `{text}` ({recipe.text_category or '—'}) @ {recipe.text_position}\n"
        f"Variations: scale {recipe.scale:.2%}, rot {recipe.rotation_deg:+.2f}°, "
        f"end trim {recipe.end_trim_sec:.2f}s"
    )


def assets_status() -> dict:
    ffmpeg_bin = resolve_ffmpeg_bin()
    return {
        "ffmpeg": ffmpeg_bin is not None,
        "ffmpeg_path": ffmpeg_bin or "",
        "clips_root": str(clips_root()),
        "hooks": len(_list_files(hooks_dir(), VIDEO_EXT)),
        "bodies": len(_list_files(body_dir(), VIDEO_EXT)),
        "music": len(_list_files(music_dir(), AUDIO_EXT)),
        "text_hooks": sum(
            len(_list_files(hooks_text_dir() / d, TEXT_EXT | VIDEO_EXT))
            for d in hooks_text_dir().iterdir()
            if d.is_dir()
        )
        if hooks_text_dir().is_dir()
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
