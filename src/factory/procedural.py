"""Procedurally generated "satisfying" backgrounds — zero API cost, fully owned.

Three generators, each a pure function of (seconds, seed) so a clip can be
reproduced exactly:

  bounce — neon balls under gravity inside a ring, growing on every bounce
  sand   — falling-sand automaton fed by a wandering, colour-cycling emitter
  flow   — slow interference-pattern colour field (lava-lamp / gradient flow)

Frames are streamed to ffmpeg as raw RGB, so nothing touches disk but the mp4.
"""

from __future__ import annotations

import math
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from . import assemble

Frame = np.ndarray  # (h, w, 3) uint8

_NEON = np.array(
    [
        [255, 64, 129], [64, 196, 255], [255, 214, 10], [80, 255, 120],
        [190, 90, 255], [255, 140, 0], [0, 230, 200], [255, 255, 255],
    ],
    dtype=np.float32,
)


# ── encoder ──────────────────────────────────────────────────────────────────


def encode(frames: Iterator[Frame], path: Path, *, width: int, height: int, fps: int) -> None:
    cmd = [
        assemble.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(path),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for frame in frames:
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError:
        pass  # ffmpeg died early; its stderr below says why
    _, err = proc.communicate()  # closes stdin, waits for exit
    if proc.returncode != 0:
        raise assemble.RenderError(f"ffmpeg encode failed: {err.decode(errors='replace')[-1000:]}")


# ── bounce ───────────────────────────────────────────────────────────────────


def bounce(seconds: float, seed: int, *, width: int, height: int, fps: int) -> Iterator[Frame]:
    rng = np.random.default_rng(seed)
    n_frames = int(seconds * fps)
    cx, cy = width / 2, height / 2
    ring_r = min(width, height) * 0.44
    n = 6
    ang = rng.uniform(0, 2 * math.pi, n)
    dist = rng.uniform(0, ring_r * 0.5, n)
    pos = np.stack([cx + dist * np.cos(ang), cy + dist * np.sin(ang)], axis=1)
    vel = rng.uniform(-260, 260, (n, 2))
    rad = np.full(n, 12.0)
    colors = _NEON[rng.integers(0, len(_NEON), n)]
    gravity = 900.0
    dt = 1.0 / fps

    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    ring_d = np.hypot(xx - cx, yy - cy)
    ring_mask = (np.abs(ring_d - ring_r) < 3.0)[..., None]
    canvas = np.full((height, width, 3), 12.0, dtype=np.float32)

    for _ in range(n_frames):
        vel[:, 1] += gravity * dt
        pos += vel * dt
        rel = pos - (cx, cy)
        d = np.hypot(rel[:, 0], rel[:, 1])
        hit = d > ring_r - rad
        if hit.any():
            normal = rel[hit] / d[hit, None]
            vn = (vel[hit] * normal).sum(1, keepdims=True)
            vel[hit] = (vel[hit] - 2 * vn * normal) * 0.985
            pos[hit] = (cx, cy) + normal * (ring_r - rad[hit])[:, None]
            rad[hit] = np.minimum(rad[hit] + 0.9, ring_r * 0.35)
        canvas *= 0.88  # trail fade
        canvas += ring_mask * (240.0 - canvas) * 0.9
        for i in range(n):
            m = (xx - pos[i, 0]) ** 2 + (yy - pos[i, 1]) ** 2 < rad[i] ** 2
            canvas[m] = colors[i]
        yield np.clip(canvas, 0, 255).astype(np.uint8)


# ── sand ─────────────────────────────────────────────────────────────────────


def _hue_palette(n: int = 64) -> np.ndarray:
    t = np.linspace(0, 1, n, endpoint=False)
    r = 0.5 + 0.5 * np.cos(2 * math.pi * (t + 0.00))
    g = 0.5 + 0.5 * np.cos(2 * math.pi * (t + 0.33))
    b = 0.5 + 0.5 * np.cos(2 * math.pi * (t + 0.67))
    pal = np.stack([r, g, b], 1) * 255
    return np.vstack([[14, 14, 20], pal]).astype(np.uint8)  # index 0 = empty


def sand(seconds: float, seed: int, *, width: int, height: int, fps: int) -> Iterator[Frame]:
    rng = np.random.default_rng(seed)
    n_frames = int(seconds * fps)
    cell = 6
    gw, gh = -(-width // cell), -(-height // cell)  # ceil so the frame is always covered
    grid = np.zeros((gh, gw), dtype=np.int16)
    pal = _hue_palette()
    n_hues = len(pal) - 1
    steps_per_frame = 3  # physics runs faster than the frame rate → fast, heavy pour
    t = 0.0

    def step() -> None:
        # fall straight down where empty
        can = (grid[:-1] > 0) & (grid[1:] == 0)
        grid[1:][can] = grid[:-1][can]
        grid[:-1][can] = 0
        # slide diagonally where blocked, random side order each step
        for slide_left in ((True, False) if rng.random() < 0.5 else (False, True)):
            src = grid[:-1, 1:] if slide_left else grid[:-1, :-1]
            below = grid[1:, 1:] if slide_left else grid[1:, :-1]
            dst = grid[1:, :-1] if slide_left else grid[1:, 1:]
            can = (src > 0) & (below != 0) & (dst == 0)
            dst[can] = src[can]
            src[can] = 0

    for f in range(n_frames):
        t += 1.0 / fps
        # wandering emitter, colour drifts through the hue wheel
        ex = int(gw / 2 + gw * 0.36 * math.sin(t * 1.3) * math.cos(t * 0.41))
        hue = 1 + int((f / n_frames) * n_hues * 1.5) % n_hues
        for _ in range(steps_per_frame):
            for dx in range(-3, 4):
                x = min(max(ex + dx, 0), gw - 1)
                if grid[1, x] == 0 and rng.random() < 0.85:
                    grid[1, x] = hue
            step()
        # reset when the pile reaches the top so the clip stays lively
        if (grid[4] > 0).mean() > 0.6:
            grid[:] = 0
        frame = pal[np.clip(grid, 0, n_hues)]
        yield np.repeat(np.repeat(frame, cell, 0), cell, 1)[:height, :width]


# ── flow ─────────────────────────────────────────────────────────────────────


def flow(seconds: float, seed: int, *, width: int, height: int, fps: int) -> Iterator[Frame]:
    rng = np.random.default_rng(seed)
    n_frames = int(seconds * fps)
    scale = 0.25  # compute at quarter res, upscale — plenty for soft gradients
    w2, h2 = int(width * scale), int(height * scale)
    yy, xx = np.mgrid[0:h2, 0:w2].astype(np.float32)
    xx /= w2
    yy /= h2
    a, b, c = rng.uniform(3, 7, 3)
    phase = rng.uniform(0, 2 * math.pi, 3)
    c1, c2, c3 = _NEON[rng.choice(len(_NEON), 3, replace=False)]

    for f in range(n_frames):
        t = f / fps
        v = (
            np.sin(xx * a + t * 0.9 + phase[0])
            + np.sin(yy * b - t * 0.7 + phase[1])
            + np.sin((xx + yy) * c + t * 1.3 + phase[2])
            + np.sin(np.hypot(xx - 0.5, yy - 0.5) * 9 - t * 1.1)
        ) / 4.0  # -1..1
        u = (v + 1) / 2
        rgb = np.where(
            (u < 0.5)[..., None],
            c1 + (c2 - c1) * (u * 2)[..., None],
            c2 + (c3 - c2) * ((u - 0.5) * 2)[..., None],
        )
        frame = np.clip(rgb, 0, 255).astype(np.uint8)
        up = np.repeat(np.repeat(frame, int(1 / scale), 0), int(1 / scale), 1)
        yield up[:height, :width]


GENERATORS = {"bounce": bounce, "sand": sand, "flow": flow}


def render_clip(
    kind: str,
    path: Path,
    *,
    seconds: float = 10.0,
    seed: int = 0,
    width: int = 540,
    height: int = 960,
    fps: int = 30,
) -> Path:
    """Render one procedural clip to `path`. Deterministic for a given seed."""
    try:
        gen = GENERATORS[kind]
    except KeyError:
        raise ValueError(f"Unknown generator '{kind}'. Valid: {', '.join(GENERATORS)}") from None
    frames = gen(seconds, seed, width=width, height=height, fps=fps)
    encode(frames, path, width=width, height=height, fps=fps)
    return path
