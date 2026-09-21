"""ffmpeg rendering: cut clips → concat → burn captions → mux narration."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .timeline import Segment

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


class RenderError(Exception):
    """Raised when ffmpeg is missing or a render fails."""


def ffmpeg_exe() -> str:
    """Prefer a system ffmpeg; fall back to the static binary from imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
    except ImportError:  # pragma: no cover - dependency is declared
        raise RenderError("ffmpeg not found on PATH and imageio-ffmpeg is not installed") from None
    return imageio_ffmpeg.get_ffmpeg_exe()


def parse_duration(ffmpeg_stderr: str) -> float:
    m = _DURATION_RE.search(ffmpeg_stderr)
    if not m:
        raise RenderError("Could not read duration from ffmpeg output")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def probe_duration(path: Path) -> float:
    """Media duration in seconds (uses ffmpeg -i, so no ffprobe needed)."""
    r = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
    )
    return parse_duration(r.stderr)


def build_command(
    segments: list[Segment],
    audio_path: Path,
    ass_name: str,
    out_path: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    crf: int = 20,
    preset: str = "medium",
) -> list[str]:
    """Build the ffmpeg argv.

    `ass_name` must be a bare filename in the working directory the command is
    run from — that sidesteps filtergraph path escaping entirely.
    """
    if not segments:
        raise RenderError("No segments to render")
    if "/" in ass_name or "\\" in ass_name:
        raise RenderError("ass_name must be a bare filename (run ffmpeg in its directory)")

    cmd: list[str] = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y"]
    for seg in segments:
        cmd += ["-ss", f"{seg.start:.3f}", "-t", f"{seg.duration:.3f}", "-i", str(seg.clip.path)]
    cmd += ["-i", str(audio_path)]
    audio_index = len(segments)

    parts: list[str] = []
    for i in range(len(segments)):
        parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1,setpts=PTS-STARTPTS[v{i}]"
        )
    inputs = "".join(f"[v{i}]" for i in range(len(segments)))
    parts.append(f"{inputs}concat=n={len(segments)}:v=1:a=0[vc]")
    parts.append(f"[vc]ass={ass_name}[vout]")

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[vout]", "-map", f"{audio_index}:a",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out_path),
    ]
    return cmd


def render(
    segments: list[Segment],
    audio_path: Path,
    ass_path: Path,
    out_path: Path,
    **kwargs: int | str,
) -> Path:
    """Run ffmpeg and return the output path. Raises RenderError on failure."""
    audio_path = audio_path.resolve()
    ass_path = ass_path.resolve()
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(segments, audio_path, ass_path.name, out_path, **kwargs)  # type: ignore[arg-type]
    r = subprocess.run(cmd, cwd=ass_path.parent, capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderError(f"ffmpeg failed ({r.returncode}):\n{r.stderr.strip()[-2000:]}")
    return out_path
