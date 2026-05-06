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
