"""Tests for the clip bank manifest and mocked generation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from factory import bank as bankmod
from factory.prompts import ClipPrompt


def test_manifest_roundtrip(tmp_path):
    b = bankmod.Bank(tmp_path / "bank")
    assert b.clips() == []
    clip = bankmod.Clip("abc", tmp_path / "bank" / "soap-abc.mp4", "soap", "p", 9.9, "m", "r1")
    b.add(clip)

    b2 = bankmod.Bank(tmp_path / "bank")
    assert b2.clips() == [clip]
    assert b2.categories() == {"soap": 1}
    assert b2.clips(["soap"]) == [clip] and b2.clips(["other"]) == []


def test_generate_with_mocked_muapi(tmp_path, monkeypatch):
    async def fake_submit(model, payload):
        assert payload["aspect_ratio"] == "9:16"
        return "req-" + payload["prompt"][:3]

    async def fake_poll(request_id, *, max_wait, interval=3.0):
        if request_id == "req-bad":
            raise bankmod.muapi.MuapiError("boom")
        return {"status": "completed", "outputs": [{"url": f"https://x/{request_id}.mp4"}]}

    async def fake_download(url, dest: Path):
        dest.write_bytes(b"\x00")

    monkeypatch.setattr(bankmod.muapi, "submit", fake_submit)
    monkeypatch.setattr(bankmod.muapi, "poll", fake_poll)
    monkeypatch.setattr(bankmod, "_download", fake_download)
    monkeypatch.setattr(bankmod.assemble, "probe_duration", lambda p: 10.0)

    b = bankmod.Bank(tmp_path / "bank")
    prompts = [ClipPrompt("soap", "good one"), ClipPrompt("sand", "bad one")]
    done, failed = asyncio.run(bankmod.generate(b, prompts, concurrency=2))

    assert [c.category for c in done] == ["soap"]
    assert done[0].duration == 10.0 and done[0].path.exists()
    assert len(failed) == 1 and failed[0][0].category == "sand"
    assert bankmod.Bank(tmp_path / "bank").categories() == {"soap": 1}


def test_add_remote_downloads_and_registers(tmp_path, monkeypatch):
    async def fake_download(url, dest: Path):
        assert url == "https://x/clip.mp4"
        dest.write_bytes(b"\x00")

    monkeypatch.setattr(bankmod, "_download", fake_download)
    monkeypatch.setattr(bankmod.assemble, "probe_duration", lambda p: 8.0)
    b = bankmod.Bank(tmp_path / "bank")
    clip = asyncio.run(
        bankmod.add_remote(b, "https://x/clip.mp4", category="soap-cutting", model="seedance1_5")
    )
    assert clip.category == "soap-cutting" and clip.duration == 8.0 and clip.path.exists()
    assert bankmod.Bank(tmp_path / "bank").categories() == {"soap-cutting": 1}
