"""ffmpeg rendering: cut clips → concat → burn captions → mux narration."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # only for annotations — avoids the timeline → bank → assemble cycle
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


# Broadcast-ish loudness for speech-led shorts; platforms normalise to about here anyway.
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


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
    music_path: Path | None = None,
    music_db: float = -18.0,
    total: float | None = None,
) -> list[str]:
    """Build the ffmpeg argv.

    `ass_name` must be a bare filename in the working directory the command is
    run from — that sidesteps filtergraph path escaping entirely.

    With `music_path`, the bed is looped under the narration at `music_db`,
    side-chain ducked by the voice, then the mix is loudness-normalised.

    `total` overrides the output length (default: the segments' sum). When it is
    longer than the narration the voice track is padded with silence so the music
    bed keeps playing under an end card.
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
    music_index = None
    if music_path is not None:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        music_index = audio_index + 1

    parts: list[str] = []
    for i in range(len(segments)):
        parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1,setpts=PTS-STARTPTS[v{i}]"
        )
    inputs = "".join(f"[v{i}]" for i in range(len(segments)))
    parts.append(f"{inputs}concat=n={len(segments)}:v=1:a=0[vc]")
    parts.append(f"[vc]ass={ass_name}[vout]")

    length = total if total is not None else sum(seg.duration for seg in segments)
    if length <= 0:
        raise RenderError("total must be positive")
    pad = f"apad=whole_dur={length:.3f}"
    if music_index is None:
        parts.append(f"[{audio_index}:a]{pad},{LOUDNORM},aresample=48000[aout]")
    else:
        parts.append(f"[{audio_index}:a]{pad},asplit=2[nar][sc]")
        parts.append(f"[{music_index}:a]volume={music_db}dB[mus]")
        parts.append(
            "[mus][sc]sidechaincompress=threshold=0.02:ratio=10:attack=50:release=500[duck]"
        )
        parts.append(
            f"[nar][duck]amix=inputs=2:duration=first:dropout_transition=0,"
            f"{LOUDNORM},aresample=48000[aout]"
        )

    # loudnorm buffers the whole audio stream, so -shortest fires late; cap the
    # output at the planned video length explicitly.
    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[vout]", "-map", "[aout]",
        "-t", f"{length:.3f}",
        "-r", str(fps),
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
    **kwargs: int | str | float | Path | None,
) -> Path:
    """Run ffmpeg and return the output path. Raises RenderError on failure."""
    audio_path = audio_path.resolve()
    ass_path = ass_path.resolve()
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if kwargs.get("music_path") is not None:
        kwargs["music_path"] = Path(str(kwargs["music_path"])).resolve()
    cmd = build_command(segments, audio_path, ass_path.name, out_path, **kwargs)  # type: ignore[arg-type]
    r = subprocess.run(cmd, cwd=ass_path.parent, capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderError(f"ffmpeg failed ({r.returncode}):\n{r.stderr.strip()[-2000:]}")
    return out_path
