"""Tests for the cut planner."""

from __future__ import annotations

from pathlib import Path

import pytest

from factory import timeline
from factory.bank import Clip


def _clip(i: int, duration: float = 10.0) -> Clip:
    return Clip(f"c{i}", Path(f"c{i}.mp4"), "cat", "p", duration, "m", "r")


def test_plan_covers_total_exactly():
    clips = [_clip(i) for i in range(3)]
    segs = timeline.plan(clips, 30.0, seed=1)
    assert abs(sum(s.duration for s in segs) - 30.0) < 1e-6
    for s in segs:
        assert 0 <= s.start and s.start + s.duration <= s.clip.duration + 1e-9
        assert s.duration <= 4.0 + 1e-9


def test_plan_never_repeats_consecutively():
    clips = [_clip(i) for i in range(4)]
    segs = timeline.plan(clips, 60.0, seed=7)
    for a, b in zip(segs, segs[1:]):
        assert a.clip is not b.clip


def test_plan_is_deterministic_with_seed():
    clips = [_clip(i) for i in range(3)]
    assert timeline.plan(clips, 20.0, seed=3) == timeline.plan(clips, 20.0, seed=3)
    assert timeline.plan(clips, 20.0, seed=3) != timeline.plan(clips, 20.0, seed=4)


def test_plan_respects_short_clips():
    clips = [_clip(0, duration=1.5), _clip(1, duration=1.5)]
    segs = timeline.plan(clips, 6.0, seed=0)
    assert all(s.duration <= 1.5 + 1e-9 for s in segs)
    assert abs(sum(s.duration for s in segs) - 6.0) < 1e-6


def test_plan_single_clip_allowed():
    segs = timeline.plan([_clip(0)], 9.0, seed=0)
    assert abs(sum(s.duration for s in segs) - 9.0) < 1e-6


def test_plan_errors():
    with pytest.raises(ValueError, match="No clips"):
        timeline.plan([], 10.0)
    with pytest.raises(ValueError, match="positive"):
        timeline.plan([_clip(0)], 0.0)
    with pytest.raises(ValueError, match="min_cut"):
        timeline.plan([_clip(0)], 5.0, min_cut=4.0, max_cut=2.0)
