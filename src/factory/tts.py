"""Text-to-speech with word-level timestamps.

Providers:
  elevenlabs — real voice via the /with-timestamps endpoint (ELEVENLABS_API_KEY)
  stub       — silent audio with estimated timings, for offline dev and tests
"""

from __future__ import annotations

import base64
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs premade "Rachel"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


class TTSError(Exception):
    """Raised when speech synthesis fails."""


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass
class Speech:
    audio_path: Path
    words: list[Word]
    duration: float


class Provider(Protocol):
    def synthesize(self, text: str, out_path: Path) -> Speech: ...


# ── Alignment helpers ─────────────────────────────────────────────────────────


def words_from_alignment(
    characters: list[str],
    starts: list[float],
    ends: list[float],
) -> list[Word]:
    """Collapse per-character timings into per-word timings (split on whitespace)."""
    if not (len(characters) == len(starts) == len(ends)):
        raise TTSError("Alignment arrays have mismatched lengths")
    words: list[Word] = []
    buf: list[str] = []
    w_start = 0.0
    w_end = 0.0
    for ch, s, e in zip(characters, starts, ends):
        if ch.isspace():
            if buf:
                words.append(Word("".join(buf), w_start, w_end))
                buf = []
            continue
        if not buf:
            w_start = s
        buf.append(ch)
        w_end = e
    if buf:
        words.append(Word("".join(buf), w_start, w_end))
    return words


# ── ElevenLabs ────────────────────────────────────────────────────────────────


class ElevenLabs:
    def __init__(
        self,
        *,
        voice_id: str | None = None,
        model_id: str = DEFAULT_MODEL_ID,
        api_key: str | None = None,
    ) -> None:
        self.voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)
        self.model_id = model_id
        self._api_key = api_key

    def _key(self) -> str:
        key = self._api_key or os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not key:
            raise TTSError("ELEVENLABS_API_KEY is not set")
        return key

    def synthesize(self, text: str, out_path: Path) -> Speech:
        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{self.voice_id}/with-timestamps"
        r = httpx.post(
            url,
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self._key(), "Content-Type": "application/json"},
            json={"text": text, "model_id": self.model_id},
            timeout=120.0,
        )
        if r.status_code == 401:
            raise TTSError("ElevenLabs authentication failed — check ELEVENLABS_API_KEY")
        if r.status_code >= 400:
            raise TTSError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
        data = r.json()
        audio_b64 = data.get("audio_base64")
        alignment = data.get("alignment") or {}
        if not audio_b64 or not alignment:
            raise TTSError(f"Unexpected ElevenLabs response keys: {list(data)}")
        out_path = out_path.with_suffix(".mp3")
        out_path.write_bytes(base64.b64decode(audio_b64))
        words = words_from_alignment(
            alignment["characters"],
            alignment["character_start_times_seconds"],
            alignment["character_end_times_seconds"],
        )
        duration = words[-1].end if words else 0.0
        return Speech(out_path, words, duration)


# ── Offline stub ──────────────────────────────────────────────────────────────


class Stub:
    """Estimates timings from word length and writes silent audio.

    Lets the whole pipeline run with no API keys; output is obviously silent.
    """

    rate = 2.6  # spoken words per second, used only for the pacing estimate

    def synthesize(self, text: str, out_path: Path) -> Speech:
        words: list[Word] = []
        t = 0.0
        for raw in text.split():
            dur = 0.12 + 0.05 * len(raw)
            words.append(Word(raw, t, t + dur))
            t += dur + 0.06
            if raw[-1] in ".!?":
                t += 0.25
        duration = t + 0.4
        out_path = out_path.with_suffix(".wav")
        _write_silence(out_path, duration)
        return Speech(out_path, words, duration)


def _write_silence(path: Path, seconds: float, sample_rate: int = 24_000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frames)


PROVIDERS = {"elevenlabs": ElevenLabs, "stub": Stub}


def get_provider(name: str, **kwargs: object) -> Provider:
    try:
        cls = PROVIDERS[name]
    except KeyError:
        raise TTSError(f"Unknown TTS provider '{name}'. Valid: {', '.join(PROVIDERS)}") from None
    return cls(**kwargs)  # type: ignore[arg-type]
