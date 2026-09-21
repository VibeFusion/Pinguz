"""Tests for TTS providers and alignment handling."""

from __future__ import annotations

import base64
import wave

import httpx
import numpy as np
import pytest
import respx

from factory import tts


def test_words_from_alignment_splits_on_whitespace():
    chars = list("hi there")
    starts = [i * 0.1 for i in range(len(chars))]
    ends = [s + 0.1 for s in starts]
    words = tts.words_from_alignment(chars, starts, ends)
    assert [w.text for w in words] == ["hi", "there"]
    assert words[0].start == 0.0 and words[0].end == pytest.approx(0.2)
    assert words[1].start == pytest.approx(0.3) and words[1].end == pytest.approx(0.8)


def test_words_from_alignment_length_mismatch():
    with pytest.raises(tts.TTSError, match="mismatched"):
        tts.words_from_alignment(["a"], [0.0], [])


def test_stub_writes_silence_and_monotonic_timings(tmp_path):
    speech = tts.Stub().synthesize("I quit my job. Then it got weird.", tmp_path / "voice")
    assert speech.audio_path.suffix == ".wav" and speech.audio_path.exists()
    assert [w.text for w in speech.words][:3] == ["I", "quit", "my"]
    for a, b in zip(speech.words, speech.words[1:]):
        assert a.end <= b.start
    with wave.open(str(speech.audio_path)) as wf:
        assert wf.getnframes() / wf.getframerate() == pytest.approx(speech.duration, abs=0.01)


@respx.mock
def test_elevenlabs_parses_timestamps(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    route = respx.post(f"{tts.ELEVENLABS_BASE_URL}/text-to-speech/v1/with-timestamps").mock(
        return_value=httpx.Response(
            200,
            json={
                "audio_base64": base64.b64encode(b"MP3DATA").decode(),
                "alignment": {
                    "characters": list("go now"),
                    "character_start_times_seconds": [0, 0.1, 0.2, 0.3, 0.4, 0.5],
                    "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                },
            },
        )
    )
    speech = tts.ElevenLabs(voice_id="v1").synthesize("go now", tmp_path / "voice")
    assert route.called
    assert route.calls[0].request.headers["xi-api-key"] == "k"
    assert speech.audio_path.read_bytes() == b"MP3DATA"
    assert [w.text for w in speech.words] == ["go", "now"]
    assert speech.duration == pytest.approx(0.6)


@respx.mock
def test_elevenlabs_auth_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "bad")
    respx.post(f"{tts.ELEVENLABS_BASE_URL}/text-to-speech/v1/with-timestamps").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(tts.TTSError, match="authentication"):
        tts.ElevenLabs(voice_id="v1").synthesize("x", tmp_path / "v")


def test_elevenlabs_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(tts.TTSError, match="ELEVENLABS_API_KEY"):
        tts.ElevenLabs(voice_id="v1").synthesize("x", tmp_path / "v")


def test_get_provider_unknown():
    with pytest.raises(tts.TTSError, match="Unknown TTS provider"):
        tts.get_provider("nope")


def test_split_sentences():
    assert tts.split_sentences("One. Two! Three? Four") == ["One.", "Two!", "Three?", "Four"]


def test_spread_words_is_monotonic_and_fills_span():
    words = tts.spread_words("I quit my job today.", 2.0, 4.0)
    assert [w.text for w in words] == ["I", "quit", "my", "job", "today."]
    assert words[0].start == 2.0 and words[-1].end == pytest.approx(3.98, abs=1e-6)
    for a, b in zip(words, words[1:]):
        assert a.end <= b.start
    assert words[1].end - words[1].start > words[0].end - words[0].start  # longer word, longer slot


def test_speech_bounds_trims_silence():
    sr = 1000
    x = np.zeros(3000, dtype=np.float32)
    x[500:2500] = 0.5
    on, off = tts.speech_bounds(x, sr)
    assert on == pytest.approx(0.5) and off == pytest.approx(2.5)
    assert tts.speech_bounds(np.zeros(10, dtype=np.float32), sr) == (0.0, 0.01)


def test_kokoro_requires_package(monkeypatch):
    import importlib
    def boom(name):
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", boom)
    with pytest.raises(tts.TTSError, match="kokoro-onnx not installed"):
        tts.Kokoro()._load()
