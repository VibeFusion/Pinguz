"""Text-to-speech with word-level timestamps.

Providers:
  elevenlabs — real voice via the /with-timestamps endpoint (ELEVENLABS_API_KEY)
  kokoro     — offline neural voice (kokoro-onnx, Apache-2.0), no key, sentence-exact timing
  stub       — silent audio with estimated timings, for offline dev and tests
"""

from __future__ import annotations

import base64
import importlib
import os
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx
import numpy as np

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
# ElevenLabs premade "Adam": the narrator most viral Reddit-story channels use, and the
# voice the user picked over Sarah/Liam in listening tests. Rachel is 21m00Tcm4TlvDq8ikWAM.
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
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


# ── Kokoro (offline) ──────────────────────────────────────────────────────────

KOKORO_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
DEFAULT_KOKORO_VOICE = "am_michael"
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_SENTENCE_GAP = 0.18  # seconds of silence inserted between sentences


def split_sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_RE.split(text.strip()) if s]


def speech_bounds(samples: np.ndarray, sr: int, threshold: float = 0.02) -> tuple[float, float]:
    """(onset, offset) in seconds of the audible part of a clip."""
    loud = np.flatnonzero(np.abs(samples) > threshold)
    if loud.size == 0:
        return 0.0, len(samples) / sr
    return float(loud[0]) / sr, float(loud[-1] + 1) / sr


def spread_words(sentence: str, start: float, end: float) -> list[Word]:
    """Distribute a sentence's words across [start, end] weighted by length.

    Every word costs its letters plus one unit for the gap after it, which
    tracks natural speech to within ~80 ms in practice.
    """
    tokens = sentence.split()
    if not tokens:
        return []
    weights = np.array([len(t.strip(".,!?;:'\"")) + 1 for t in tokens], dtype=float)
    edges = np.concatenate([[0.0], np.cumsum(weights)]) / weights.sum()
    span = end - start
    return [
        Word(tok, start + span * edges[i], start + span * edges[i + 1] - 0.02)
        for i, tok in enumerate(tokens)
    ]


def kokoro_dir() -> Path:
    return Path(os.environ.get("KOKORO_DIR") or Path.home() / ".cache" / "factory" / "kokoro")


def ensure_kokoro_models(dir: Path | None = None) -> Path:
    """Download the two Kokoro model files (~350 MB) on first use."""
    dir = dir or kokoro_dir()
    dir.mkdir(parents=True, exist_ok=True)
    for name in KOKORO_FILES:
        dest = dir / name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        print(f"  downloading {name} → {dir} …")
        url = f"{KOKORO_RELEASE}/{name}"
        with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
    return dir


class Kokoro:
    """Offline neural TTS via kokoro-onnx. `pip install "pinguz[kokoro]"`.

    Each sentence is synthesized separately so sentence boundaries are exact;
    words inside a sentence are spread by length. Good enough for word-by-word
    captions without a forced aligner.
    """

    def __init__(self, *, voice: str | None = None, speed: float = 1.0) -> None:
        self.voice = voice or os.environ.get("KOKORO_VOICE", DEFAULT_KOKORO_VOICE)
        self.speed = speed
        self._engine: Any = None

    def _load(self) -> Any:
        if self._engine is None:
            try:
                mod = importlib.import_module("kokoro_onnx")
            except ImportError:
                raise TTSError("kokoro-onnx not installed — pip install 'pinguz[kokoro]'") from None
            d = ensure_kokoro_models()
            self._engine = mod.Kokoro(str(d / KOKORO_FILES[0]), str(d / KOKORO_FILES[1]))
        return self._engine

    def synthesize(self, text: str, out_path: Path) -> Speech:
        engine = self._load()
        words: list[Word] = []
        chunks: list[np.ndarray] = []
        t = 0.0
        sr = 24_000
        for sentence in split_sentences(text):
            samples, sr = engine.create(sentence, voice=self.voice, speed=self.speed, lang="en-us")
            samples = np.asarray(samples, dtype=np.float32)
            onset, offset = speech_bounds(samples, sr)
            words += spread_words(sentence, t + onset, t + offset)
            chunks.append(samples)
            chunks.append(np.zeros(int(_SENTENCE_GAP * sr), dtype=np.float32))
            t += len(samples) / sr + _SENTENCE_GAP
        if not chunks:
            raise TTSError("Nothing to synthesize")
        audio = np.concatenate(chunks)
        out_path = out_path.with_suffix(".wav")
        _write_wav(out_path, audio, sr)
        return Speech(out_path, words, len(audio) / sr)


def _write_wav(path: Path, samples: np.ndarray, sr: int) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


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


PROVIDERS = {"elevenlabs": ElevenLabs, "kokoro": Kokoro, "stub": Stub}


def get_provider(name: str, **kwargs: object) -> Provider:
    try:
        cls = PROVIDERS[name]
    except KeyError:
        raise TTSError(f"Unknown TTS provider '{name}'. Valid: {', '.join(PROVIDERS)}") from None
    return cls(**kwargs)  # type: ignore[arg-type]
