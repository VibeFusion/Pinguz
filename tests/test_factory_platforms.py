"""Per-platform export: caption building, trim decisions, file layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory import platforms

META = {
    "title": "My roommate secretly paid my rent for six months",
    "style": "confession",
    "hook": "My landlord thanked me for the extra two thousand dollars.",
    "narration": "My landlord thanked me. Do I ask him?",
    "hashtags": ["reddit", "roommate", "storytime", "confession", "plottwist", "extra"],
}


def test_every_platform_in_order() -> None:
    assert set(platforms.ORDER) == set(platforms.PLATFORMS)
    for p in platforms.PLATFORMS.values():
        assert 0 < p.min_seconds < p.max_seconds
        assert 0 <= p.safe_zone.top < 0.5 and 0 <= p.safe_zone.bottom < 0.5


def test_youtube_caption_leads_with_shorts_tag_and_hook() -> None:
    title, caption, tags = platforms.build_caption(META, platforms.PLATFORMS["youtube"])
    assert title == META["title"]
    assert tags[0] == "Shorts"
    assert caption.startswith(META["hook"])
    assert "#Shorts" in caption and "#reddit" in caption


def test_hashtags_capped_per_platform() -> None:
    _, _, tags = platforms.build_caption(META, platforms.PLATFORMS["snapchat"])
    assert len(tags) <= platforms.PLATFORMS["snapchat"].hashtags_max


def test_reddit_is_text_first() -> None:
    title, body, tags = platforms.build_caption(META, platforms.PLATFORMS["reddit"])
    assert body == META["narration"]
    assert tags == []
    assert "AmItheAsshole" not in platforms.suggest_subreddits("confession")
    assert "confession" in platforms.suggest_subreddits("confession")
    assert platforms.suggest_subreddits("AITA")[0] == "AmItheAsshole"


def test_caption_clipped_to_limit() -> None:
    long_meta = dict(META, hook="x" * 500)
    _, caption, _ = platforms.build_caption(long_meta, platforms.PLATFORMS["snapchat"])
    assert len(caption) <= platforms.PLATFORMS["snapchat"].caption_max


def test_plan_trims_only_when_over_ceiling() -> None:
    snap = platforms.plan_export(META, 75.0, platforms.PLATFORMS["snapchat"])
    assert snap.trimmed and snap.seconds == 60.0
    assert any("trimmed" in w for w in snap.warnings)
    yt = platforms.plan_export(META, 75.0, platforms.PLATFORMS["youtube"])
    assert not yt.trimmed and yt.seconds == 75.0 and yt.warnings == []


def test_tiktok_warns_under_monetisation_floor() -> None:
    ex = platforms.plan_export(META, 48.9, platforms.PLATFORMS["tiktok"])
    assert not ex.trimmed
    assert any("60" in w and "monetis" in w for w in ex.warnings)
    ok = platforms.plan_export(META, 61.0, platforms.PLATFORMS["tiktok"])
    assert ok.warnings == []


def test_export_all_writes_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\x00" * 16)
    trims: list[tuple[Path, Path, float]] = []

    def fake_trim(src: Path, dst: Path, seconds: float) -> None:
        trims.append((src, dst, seconds))
        dst.write_bytes(b"t")

    monkeypatch.setattr(platforms, "_trim", fake_trim)
    out = platforms.export_all(video, META, tmp_path / "export", seconds=70.0)
    assert [e.platform for e in out] == list(platforms.ORDER)
    for ex in out:
        assert Path(ex.video).exists()
        meta = json.loads((Path(ex.video).parent / "meta.json").read_text())
        assert meta["platform"] == ex.platform
    assert [t[2] for t in trims] == [60.0]  # only Snapchat needed a trim at 70 s
    post = (tmp_path / "export" / "reddit" / "post.md").read_text()
    assert post.startswith("# " + META["title"]) and "r/confession" in post


def test_export_all_rejects_unknown_platform(tmp_path: Path) -> None:
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\x00")
    with pytest.raises(ValueError, match="unknown platform"):
        platforms.export_all(video, META, tmp_path, platforms=["myspace"], seconds=10.0)
