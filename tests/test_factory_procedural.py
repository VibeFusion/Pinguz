"""Tests for procedural backgrounds and the music bed."""

from __future__ import annotations

import numpy as np
import pytest

from factory import assemble, music, procedural
from factory import bank as bankmod


@pytest.mark.parametrize("kind", sorted(procedural.GENERATORS))
def test_generators_yield_correct_frames(kind):
    frames = list(procedural.GENERATORS[kind](0.2, 1, width=64, height=96, fps=10))
    assert len(frames) == 2
    for f in frames:
        assert f.shape == (96, 64, 3) and f.dtype == np.uint8
    assert frames[0].tobytes() != frames[1].tobytes()  # something moves


def test_generators_are_deterministic():
    a = next(procedural.bounce(0.1, 5, width=32, height=48, fps=10))
    b = next(procedural.bounce(0.1, 5, width=32, height=48, fps=10))
    assert np.array_equal(a, b)


def test_render_clip_and_bank(tmp_path):
    b = bankmod.Bank(tmp_path / "bank")
    made = bankmod.add_procedural(b, ["flow"], per_kind=1, seconds=0.5, width=64, height=96)
    assert len(made) == 1 and made[0].category == "proc-flow" and made[0].path.exists()
    assert abs(assemble.probe_duration(made[0].path) - 0.5) < 0.2
    assert bankmod.Bank(tmp_path / "bank").categories() == {"proc-flow": 1}


def test_unknown_generator(tmp_path):
    with pytest.raises(ValueError, match="Unknown generator"):
        procedural.render_clip("nope", tmp_path / "x.mp4")


def test_ambient_pad_is_quiet_and_sized():
    pad = music.ambient_pad(2.0, seed=1, sr=8000)
    assert pad.shape == (16000,) and pad.dtype == np.float32
    assert 0.2 < float(np.abs(pad).max()) <= 0.31  # normalised to a bed level
