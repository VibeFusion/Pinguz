"""Tests for ffmpeg command construction and an end-to-end offline render."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory import assemble, captions, timeline, tts
from factory.bank import Clip


def test_parse_duration():
    assert assemble.parse_duration("  Duration: 00:01:02.50, start: 0") == pytest.approx(62.5)
    with pytest.raises(assemble.RenderError):
        assemble.parse_duration("nothing here")


def test_build_command_layout(monkeypatch):
    monkeypatch.setattr(assemble, "ffmpeg_exe", lambda: "ffmpeg")
    clips = [
        Clip("a", Path("a.mp4"), "c", "p", 10, "m", "r"),
        Clip("b", Path("b.mp4"), "c", "p", 10, "m", "r"),
    ]
    segs = [timeline.Segment(clips[0], 1.0, 3.0), timeline.Segment(clips[1], 2.5, 2.0)]
    cmd = assemble.build_command(segs, Path("v.wav"), "captions.ass", Path("out.mp4"))
    assert cmd[0] == "ffmpeg"
    assert cmd.count("-i") == 3  # two clips + audio
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=0[vc]" in fc and "[vc]ass=captions.ass[vout]" in fc
    assert cmd[cmd.index("-map") + 1] == "[vout]"
    assert "[2:a]loudnorm" in fc and "[aout]" in cmd  # narration is input 2, normalised
    assert "-r" in cmd and cmd[cmd.index("-r") + 1] == "30"
    assert cmd[cmd.index("-t", cmd.index("-map")) + 1] == "5.000"  # capped at 3.0 + 2.0 s
    assert cmd[-1] == "out.mp4"


def test_build_command_with_music_ducks_under_voice(monkeypatch):
    monkeypatch.setattr(assemble, "ffmpeg_exe", lambda: "ffmpeg")
    clip = Clip("a", Path("a.mp4"), "c", "p", 10, "m", "r")
    cmd = assemble.build_command(
        [timeline.Segment(clip, 0, 2)], Path("v.wav"), "c.ass", Path("o.mp4"),
        music_path=Path("bed.wav"), music_db=-20,
    )
    assert cmd.count("-i") == 3 and "-stream_loop" in cmd  # clip, voice, looped bed
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "volume=-20dB" in fc
    assert "sidechaincompress" in fc and "amix=inputs=2:duration=first" in fc
    assert "loudnorm" in fc


def test_build_command_rejects_paths_in_ass_name():
    clip = Clip("a", Path("a.mp4"), "c", "p", 10, "m", "r")
    with pytest.raises(assemble.RenderError, match="bare filename"):
        assemble.build_command([timeline.Segment(clip, 0, 1)], Path("v"), "x/y.ass", Path("o"))
    with pytest.raises(assemble.RenderError, match="No segments"):
        assemble.build_command([], Path("v"), "y.ass", Path("o"))


def _make_test_clip(path: Path, seconds: float, color: str) -> None:
    subprocess.run(
        [
            assemble.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:s=180x320:r=15:d={seconds}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
        ],
        check=True,
    )


def test_end_to_end_offline_render(tmp_path):
    """Synthetic clips + stub voice + captions → real mp4 via ffmpeg."""
    clips = []
    for i, color in enumerate(["red", "blue"]):
        p = tmp_path / f"{color}.mp4"
        _make_test_clip(p, 3.0, color)
        clips.append(Clip(f"c{i}", p, "test", "p", assemble.probe_duration(p), "m", "r"))
    assert all(abs(c.duration - 3.0) < 0.2 for c in clips)

    speech = tts.Stub().synthesize("This is a short test of the pipeline.", tmp_path / "voice")
    segs = timeline.plan(clips, speech.duration, min_cut=1.0, max_cut=2.0, seed=1)
    ass = tmp_path / "captions.ass"
    ass.write_text(captions.to_ass(speech.words))

    out = assemble.render(segs, speech.audio_path, ass, tmp_path / "out" / "short.mp4",
                          width=180, height=320, fps=15, preset="ultrafast")
    assert out.exists() and out.stat().st_size > 1000
    assert abs(assemble.probe_duration(out) - speech.duration) < 0.5
