# Transcribing long videos to text

Two offline transcription tools. Both run entirely on your own machine — no upload step and
no file size limit, so a 188 MB / 12-minute recording is no different from a 10-second clip.

- **`transcriber.html`** — open it in Chrome, drag a video in, get timestamped text back.
  No install required; the speech model is fetched from a CDN on first run and cached.
- **`transcribe.py`** — command line batch version, below. Needs Python and ffmpeg.
- **`test_page.py`** — Playwright checks for the HTML page (`python3 test_page.py`).

## One-time setup

**1. Install ffmpeg**

- macOS: `brew install ffmpeg`
- Windows: `winget install Gyan.FFmpeg` (then reopen your terminal)
- Ubuntu/Debian: `sudo apt install ffmpeg`

**2. Install the speech-to-text engine**

```
pip install faster-whisper
```

## Transcribe

Put `transcribe.py` in the same folder as your videos, then:

```
python3 transcribe.py "RingVideo_20260524_183852.mp4"
```

Several at once, including whole folders:

```
python3 transcribe.py *.mp4 *.MOV
```

For each input you get two files next to the original:

- `NAME.txt` — plain transcript, one timestamped line per spoken passage
- `NAME.srt` — standard subtitles, loadable in VLC / QuickTime / YouTube

The model downloads itself the first time (~500 MB for `small`) and is cached afterwards.

## Options

| Flag | What it does |
|---|---|
| `--model medium` | More accurate, ~3x slower. Worth it for noisy or distant audio. |
| `--model large-v3` | Best accuracy, needs ~10 GB RAM. |
| `--language en` | Skip auto-detection. Use when you know the language. |
| `--threads 8` | Use more CPU cores to speed things up. |

## What to expect on speed

With the default `small` model, transcription runs at roughly 2–3x realtime on a typical
laptop CPU, so a 12-minute video takes about 4–6 minutes. `--model medium` roughly triples
that. If your machine has an NVIDIA GPU, add `device="cuda"` in the script for a large
speedup.

## Tips for doorbell and security camera footage

This kind of audio is often quiet, distant, and wind-heavy, which is the hardest case for
speech recognition. Two things help a lot:

- Use `--model medium` or `--model large-v3`. The accuracy gap over `small` is widest
  exactly on noisy, far-field audio.
- Pass `--language en` (or whichever language applies). Auto-detection can misfire when
  the first few seconds are mostly background noise.

Expect imperfect results regardless — treat the transcript as a searchable draft and
confirm any important wording against the audio itself. If a specific passage matters,
note its timestamp from the `.txt` file and listen to that spot directly.
