"""Procedural ambient music bed — royalty-free by construction.

A slow four-chord pad: detuned sine partials per note, soft attack/release,
gentle tremolo, one-pole low-pass. Deliberately featureless so it sits under
narration at −18 dB without pulling attention.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 24_000
# A-minor-ish progression (Hz): Am, F, C, G — one chord every 4 s
_CHORDS = [
    (110.0, 130.81, 164.81, 220.0),
    (87.31, 110.0, 130.81, 174.61),
    (65.41, 82.41, 98.0, 130.81),
    (98.0, 123.47, 146.83, 196.0),
]


def ambient_pad(seconds: float, seed: int = 0, *, sr: int = SR) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n, dtype=np.float32) / sr
    out = np.zeros(n, dtype=np.float32)
    chord_len = 4.0
    for ci in range(int(np.ceil(seconds / chord_len))):
        chord = _CHORDS[ci % len(_CHORDS)]
        start, end = ci * chord_len, min((ci + 1) * chord_len, seconds)
        i0, i1 = int(start * sr), int(end * sr)
        if i1 <= i0:
            break
        seg_t = t[i0:i1] - start
        env = np.minimum(seg_t / 1.2, 1.0) * np.minimum((end - start - seg_t) / 1.5, 1.0)
        env = np.clip(env, 0, 1).astype(np.float32)
        seg = np.zeros(i1 - i0, dtype=np.float32)
        for f in chord:
            for k, amp in ((1, 1.0), (2, 0.35), (3, 0.12)):
                detune = 1 + rng.uniform(-0.002, 0.002)
                seg += amp * np.sin(2 * np.pi * f * k * detune * t[i0:i1] + rng.uniform(0, 6.28))
        out[i0:i1] += seg * env
    trem = 1 - 0.15 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t))
    out *= trem
    # one-pole low-pass (~1.2 kHz) to keep it soft
    alpha = float(np.exp(-2 * np.pi * 1200 / sr))
    y = np.empty_like(out)
    acc = 0.0
    for i in range(0, n, 2048):  # chunked IIR keeps the Python loop short
        chunk = out[i : i + 2048]
        for j in range(len(chunk)):
            acc = alpha * acc + (1 - alpha) * float(chunk[j])
            y[i + j] = acc
    peak = float(np.max(np.abs(y))) or 1.0
    return (y / peak * 0.3).astype(np.float32)


def write_wav(path: Path, samples: np.ndarray, sr: int = SR) -> Path:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path
