"""Pick background clips to cover the narration with fast, non-repeating cuts."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .bank import Clip


@dataclass(frozen=True)
class Segment:
    clip: Clip
    start: float  # offset into the clip, seconds
    duration: float


def plan(
    clips: list[Clip],
    total: float,
    *,
    min_cut: float = 2.0,
    max_cut: float = 4.0,
    seed: int | None = None,
    open_with: Clip | None = None,
    first_cut: float | None = None,
) -> list[Segment]:
    """Cover `total` seconds with cuts of min_cut–max_cut from random clips.

    Consecutive segments never reuse the same clip when more than one is
    available. Each segment starts at a random offset so the same clip looks
    different across videos.

    `open_with` forces the first clip (open on the most kinetic footage) and
    `first_cut` forces the length of that opening segment — the "open on
    motion, cut early" hook pattern.
    """
    if not clips:
        raise ValueError("No clips available — run `factory bank` first")
    if total <= 0:
        raise ValueError("total must be positive")
    if min_cut <= 0 or max_cut < min_cut:
        raise ValueError("need 0 < min_cut <= max_cut")

    rng = random.Random(seed)
    segments: list[Segment] = []
    remaining = total
    prev: Clip | None = None
    if open_with is not None or first_cut is not None:
        clip = open_with or rng.choice(clips)
        cut = min(first_cut if first_cut is not None else rng.uniform(min_cut, max_cut), remaining)
        cut = min(cut, clip.duration)
        start = rng.uniform(0.0, max(clip.duration - cut, 0.0))
        segments.append(Segment(clip, start, cut))
        remaining -= cut
        prev = clip
    while remaining > 1e-6:
        candidates = [c for c in clips if c is not prev] if len(clips) > 1 else clips
        clip = rng.choice(candidates)
        cut = min(rng.uniform(min_cut, max_cut), remaining, clip.duration)
        # Avoid a stray sliver at the end: absorb it into this cut if it fits.
        if 0 < remaining - cut < min_cut and remaining <= clip.duration:
            cut = remaining
        max_start = max(clip.duration - cut, 0.0)
        start = rng.uniform(0.0, max_start)
        segments.append(Segment(clip, start, cut))
        remaining -= cut
        prev = clip
    return segments
