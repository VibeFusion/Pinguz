# Pinguz

An MCP server that gives Claude AI image and video generation, backed by [Muapi.ai](https://muapi.ai). Direct API access — no UI layer, BYO key, the same model lineup as Higgsfield and more: Flux, Seedance, Kling, Veo, Wan, Hunyuan, Midjourney, Imagen, Nano Banana, …

## Tools

| Tool | What it does |
|---|---|
| `generate_image` | Blocking text-to-image. Returns `{url, model, request_id}` |
| `generate_video` | Blocking text-to-video or image-to-video (set `image_url`). Returns `{url, model, request_id}` |
| `submit_video` | Fire-and-forget video submission. Returns `{job_id, status, model}` immediately |
| `poll_job` | Check a job started with `submit_video`. Returns `{status}` or `{status, url}` when done |
| `list_models` | Model catalog with descriptions, grouped by `image` / `t2v` / `i2v` |

`generate_video` blocks for up to 10 minutes. Use `submit_video` + `poll_job` when you want a non-blocking flow for long videos.

### Video duration limits

| Model | Max |
|---|---|
| Seedance 2.0 | 15 s (5/10/15) |
| Kling 2.6 Pro | 10 s |
| Veo 3.1 | 8 s |
| Wan 2.5 | 10 s |
| Hunyuan | 10 s |
| Minimax Hailuo 02 Pro | 6 s |

## Setup

```bash
git clone https://github.com/VibeFusion/Pinguz
cd Pinguz
pip install -e .
```

Get an API key at [muapi.ai](https://muapi.ai) and add it to your environment:

```bash
export MUAPI_API_KEY=sk-...
```

## Connect to Claude Code (CLI / web)

Because `.claude/mcp.json` is already in this repo, Claude Code auto-registers the server when you open the project. Make sure `pinguz` is on your PATH (`pip install -e .`) and the env var is set.

Or register it manually:

```bash
claude mcp add pinguz --env MUAPI_API_KEY=sk-... -- pinguz
```

## Connect to Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pinguz": {
      "command": "pinguz",
      "env": { "MUAPI_API_KEY": "sk-..." }
    }
  }
}
```

## Example Claude conversations

> **You:** Generate a 9:16 image of a neon penguin surfing a wave, use nano-banana
>
> **Claude:** `generate_image(prompt="neon penguin surfing a wave, vibrant colors, neon lighting", model="nano-banana", aspect_ratio="9:16")`
> → `{url: "https://…", model: "nano-banana", …}`

> **You:** Submit a 15-second Seedance video of that penguin, don't wait around
>
> **Claude:** `submit_video(prompt="...", model="seedance-v2.0-t2v", duration=15)`
> → `{job_id: "abc123", status: "submitted"}`
>
> **You:** How's the video doing?
>
> **Claude:** `poll_job(job_id="abc123")` → `{status: "completed", url: "https://…"}`

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests

# End-to-end smoke test (requires a funded Muapi key)
MUAPI_API_KEY=sk-... python scripts/smoke_test.py
```

## Project layout

```
src/pinguz/
  models.py   — typed model registry (IDs, categories, max durations)
  muapi.py    — async HTTP client with retry/backoff
  server.py   — FastMCP tool definitions
scripts/
  smoke_test.py
tests/
  test_muapi.py
  test_server.py
.claude/mcp.json     — auto-registers the server in Claude Code
.github/workflows/ci.yml
```

## How Muapi works

Every generation is async under the hood:
1. `POST /api/v1/{model}` with your prompt → returns `{request_id}`
2. Poll `GET /api/v1/predictions/{request_id}/result` until `status == "completed"`

`generate_image` and `generate_video` hide this; `submit_video` + `poll_job` expose it.

---

# Factory — shorts content pipeline

`factory` is a CLI that turns a story premise into a finished 9:16 short in the
"Reddit story over oddly-satisfying footage" format:

```
idea ──▶ script agent ──▶ voice + word timings ──▶ background cuts ──▶ captions ──▶ mp4
        (Claude)          (ElevenLabs)             (Pinguz bank)       (ASS)      (ffmpeg)
```

Stories are **original fiction written by the script agent** (nothing scraped from
Reddit) and backgrounds are **generated through Pinguz**, so every asset is owned.

## Setup

```bash
pip install -e .
export MUAPI_API_KEY=sk-...        # backgrounds (Pinguz)
export ANTHROPIC_API_KEY=sk-ant-... # script + ideas agent
export ELEVENLABS_API_KEY=...       # voice (optional: --tts stub renders silent audio)
```

ffmpeg is resolved from `PATH`, falling back to the static binary bundled with
`imageio-ffmpeg`, so nothing else needs installing.

## 1. Build the background bank (once)

```bash
factory bank --dry-run                          # see the 40 prompts
factory bank --per-category 2 --duration 10     # 20 clips, ~4 in flight at a time
factory bank-list
```

Clips land in `bank/` with a `manifest.json` (category, prompt, real duration).
Ten categories ship in `factory/prompts.py` — kinetic sand, soap cutting,
hydraulic press, slime, food processing, wood splitting, pressure washing,
marble runs, candle carving, paint mixing. Add your own there.

## 2. Get ideas, write a script

```bash
factory ideas "petty revenge at work" -n 10 --out ideas.json
factory script "My roommate secretly paid my rent for six months" --style AITA --out script.json
```

The script agent enforces the retention structure the format lives on: cold-open
hook in sentence one, a second hook around 15 s, payoff withheld to the last
line, 130–170 words, read-aloud-ready prose.

## 3. Render

```bash
factory make --script script.json --out out/roommate.mp4 --seed 42
factory make --text "raw narration…" --tts stub --out out/test.mp4   # no keys needed
```

Options: `--words-per-card 2`, `--uppercase`, `--min-cut/--max-cut` (default
2–4 s), `--categories soap-cutting,slime` to restrict backgrounds. A sidecar
`.json` records the title, hashtags, and exactly which clip/offset each cut used,
so a winning video can be reproduced or varied.

## Layout

| Module | Role |
|---|---|
| `factory/prompts.py` | prompt catalog for satisfying B-roll |
| `factory/bank.py` | batch generation via `pinguz.muapi`, local manifest |
| `factory/story.py` | Claude script + ideas agent (structured output) |
| `factory/tts.py` | ElevenLabs with word timestamps; offline stub |
| `factory/captions.py` | word timings → ASS subtitles |
| `factory/timeline.py` | seeded cut planner, no consecutive repeats |
| `factory/assemble.py` | ffmpeg render (1080×1920, H.264/AAC) |
