#!/usr/bin/env python3
"""
Transcribe long videos (or audio) to text with timestamps.

Usage:
    python3 transcribe.py video1.mp4 video2.MOV
    python3 transcribe.py --model medium --language en *.mp4

Writes <name>.txt (plain transcript) and <name>.srt (subtitles) next to each input.

Requires: ffmpeg on PATH, and `pip install faster-whisper`.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

SAMPLE_RATE = 16000


def extract_audio(src: Path, dest: Path) -> None:
    """Decode any video/audio container to 16 kHz mono WAV, which is what ASR wants."""
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(src),
            "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-c:a", "pcm_s16le", str(dest),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def audio_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def fmt_timestamp(seconds: float, sep: str = ",") -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def write_outputs(segments, out_base: Path) -> int:
    """segments: iterable of (start, end, text). Returns number of segments written."""
    srt_lines, txt_lines = [], []
    count = 0
    for start, end, text in segments:
        text = text.strip()
        if not text:
            continue
        count += 1
        srt_lines.append(
            f"{count}\n{fmt_timestamp(start)} --> {fmt_timestamp(end)}\n{text}\n"
        )
        txt_lines.append(f"[{fmt_timestamp(start, '.')[:-4]}] {text}")
        print(f"  [{fmt_timestamp(start, '.')[:-4]}] {text}", flush=True)

    out_base.with_suffix(".srt").write_text("\n".join(srt_lines), encoding="utf-8")
    out_base.with_suffix(".txt").write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    return count


def run_faster_whisper(wav: Path, model_name: str, language, threads: int):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads)
    segments, _info = model.transcribe(
        str(wav),
        language=language,
        vad_filter=True,               # skip silence; big speedup on long recordings
        beam_size=5,
        condition_on_previous_text=False,  # avoids runaway repetition on long audio
    )
    for seg in segments:
        yield seg.start, seg.end, seg.text


def run_sherpa(wav: Path, model_dir: Path, vad_model: Path, threads: int):
    """Offline fallback: sherpa-onnx Whisper + Silero VAD, no Hugging Face download needed."""
    import numpy as np
    import sherpa_onnx

    recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(model_dir / "small-encoder.int8.onnx"),
        decoder=str(model_dir / "small-decoder.int8.onnx"),
        tokens=str(model_dir / "small-tokens.txt"),
        num_threads=threads,
    )

    vad_config = sherpa_onnx.VadModelConfig()
    vad_config.silero_vad.model = str(vad_model)
    vad_config.silero_vad.threshold = 0.5
    vad_config.silero_vad.min_silence_duration = 0.5
    vad_config.silero_vad.min_speech_duration = 0.25
    vad_config.silero_vad.max_speech_duration = 25.0
    vad_config.sample_rate = SAMPLE_RATE
    vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=180)

    with wave.open(str(wav)) as w:
        samples = (
            np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
            / 32768.0
        )

    window = 512
    for i in range(0, len(samples), window):
        vad.accept_waveform(samples[i : i + window])
        while not vad.empty():
            seg = vad.front
            start = seg.start / SAMPLE_RATE
            stream = recognizer.create_stream()
            stream.accept_waveform(SAMPLE_RATE, seg.samples)
            recognizer.decode_stream(stream)
            yield start, start + len(seg.samples) / SAMPLE_RATE, stream.result.text
            vad.pop()

    vad.flush()
    while not vad.empty():
        seg = vad.front
        start = seg.start / SAMPLE_RATE
        stream = recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, seg.samples)
        recognizer.decode_stream(stream)
        yield start, start + len(seg.samples) / SAMPLE_RATE, stream.result.text
        vad.pop()


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcribe videos to text with timestamps.")
    ap.add_argument("inputs", nargs="+", help="video or audio files")
    ap.add_argument("--model", default="small",
                    help="faster-whisper model: tiny/base/small/medium/large-v3 (default: small)")
    ap.add_argument("--language", default=None,
                    help="language code such as en, es, fr. Omit to auto-detect.")
    ap.add_argument("--threads", type=int, default=4, help="CPU threads (default: 4)")
    ap.add_argument("--backend", choices=["faster-whisper", "sherpa"], default="faster-whisper")
    ap.add_argument("--sherpa-model-dir", default="sherpa-onnx-whisper-small")
    ap.add_argument("--sherpa-vad", default="silero_vad.onnx")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found on PATH. Install it first "
              "(macOS: brew install ffmpeg, Ubuntu: sudo apt install ffmpeg).", file=sys.stderr)
        return 1

    failures = 0
    for raw in args.inputs:
        src = Path(raw).expanduser()
        if not src.is_file():
            print(f"ERROR: no such file: {src}", file=sys.stderr)
            failures += 1
            continue

        size_mb = src.stat().st_size / 1e6
        print(f"\n=== {src.name} ({size_mb:.1f} MB) ===", flush=True)

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "audio.wav"
            try:
                extract_audio(src, wav)
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or b"").decode(errors="replace").strip().splitlines()
                print(f"ERROR: ffmpeg could not decode {src.name}: "
                      f"{detail[-1] if detail else 'unknown error'}", file=sys.stderr)
                failures += 1
                continue

            mins = audio_duration(wav) / 60
            print(f"audio extracted: {mins:.1f} min -> transcribing "
                  f"({args.backend}, model={args.model})", flush=True)

            if args.backend == "faster-whisper":
                segments = run_faster_whisper(wav, args.model, args.language, args.threads)
            else:
                segments = run_sherpa(wav, Path(args.sherpa_model_dir),
                                      Path(args.sherpa_vad), args.threads)

            out_base = src.with_suffix("")
            n = write_outputs(segments, out_base)

        print(f"wrote {n} segments -> {out_base.name}.txt and {out_base.name}.srt", flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
