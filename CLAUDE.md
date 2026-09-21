# Pinguz — Claude Code Context

## What This Project Is

Two things in one repo:

1. **`pinguz`** — a FastMCP server wrapping the [Muapi.ai](https://muapi.ai) API. Gives
   Claude (Code or Desktop) five tools for AI image and video generation. Not an end-user app.
2. **`factory`** — a CLI that mass-produces 9:16 "Reddit story over oddly-satisfying footage"
   shorts: Claude writes the script, ElevenLabs voices it, Pinguz generates the background
   clips, ffmpeg assembles it with word-by-word captions. **This is the current focus.**

Plus 19 Higgsfield production prompt skills in `.claude/skills/` (Claude prompt guides only;
they do not call Pinguz).

## Commands

```bash
pip install -e ".[dev]"          # required before first use

ruff check src tests             # lint  (line-length 100, rules E F I UP)
pyright src                      # type-check — CI runs this, not mypy
python -m pytest tests/ -q       # 53+ tests, no network; use `python -m`, a stray global
                                 # `pytest` may not see the package
MUAPI_API_KEY=sk-... python scripts/smoke_test.py   # live Muapi smoke test (costs credits)
```

CI (`.github/workflows/ci.yml`) runs lint → pyright → pytest on Python 3.10/3.11/3.12.
All three must pass before a PR is mergeable.

## Layout

```
src/pinguz/
  models.py     — typed model registry (ModelInfo + lookup helpers)
  muapi.py      — async HTTP client: submit / poll / run / check / extract_url
  server.py     — FastMCP tool definitions (the 5 exposed tools)
src/factory/
  prompts.py    — prompt catalog for satisfying B-roll (10 categories × 4)
  bank.py       — batch-generate clips via pinguz.muapi; bank/manifest.json
  story.py      — Claude script + ideas agent (structured output, refusal fallbacks)
  tts.py        — ElevenLabs with word timestamps; `stub` provider for offline runs
  captions.py   — word timings → ASS subtitles
  timeline.py   — seeded cut planner (2–4 s cuts, no consecutive clip repeats)
  assemble.py   — ffmpeg render, 1080×1920 H.264/AAC
  platforms.py  — per-platform limits/safe zones; `factory export` packaging
  cli.py        — `factory bank | bank-import | bank-list | ideas | script | make | export`
scripts/smoke_test.py
tests/          — test_muapi, test_server, test_factory_*
.claude/mcp.json, .claude/skills/
ATLAS_PRODUCTION_GUIDE.md — Higgsfield model/skill reference for the ATLAS brand
```

## Environment

```bash
MUAPI_API_KEY        # pinguz + factory bank        (required for any generation)
ANTHROPIC_API_KEY    # factory ideas / script       (claude-opus-5)
ELEVENLABS_API_KEY   # factory make --tts elevenlabs (optional: --tts stub needs no key)
ELEVENLABS_VOICE_ID  # optional, defaults to a premade voice
```

`.env.example` lists all of them. Never commit `.env`.

## Factory workflow

```bash
factory bank --dry-run                  # print the prompts
factory bank --per-category 2           # 20 clips into bank/ (≈4 in flight)
factory ideas "petty revenge at work" -n 10 --out ideas.json
factory script "premise…" --style AITA --out script.json
factory script "premise…" --length long --out tiktok.json   # 175–200 words, ≥ 60 s
factory make --script script.json --out out/x.mp4 --seed 42
factory make --text "raw narration" --tts stub --out out/test.mp4   # no keys needed
factory export --video out/x.mp4 --script script.json          # per-platform folders
```

`factory make` writes a sidecar `.json` recording every cut (clip id, offset, duration) so a
video is reproducible from its seed. ffmpeg is resolved from `PATH`, falling back to the
static binary in `imageio-ffmpeg` — do not add a system ffmpeg dependency.

Design rules that matter for the format:
- Background must never carry narrative: no faces, no text, continuous motion.
- Stories are **original fiction** from the script agent — never scrape Reddit.
- The script agent's retention structure (cold open, second hook ~15 s, payoff last)
  lives in `story.script_system()`; word budgets per length in `story.LENGTHS`
  (short 120–140, long 175–200). Change them there, not in the CLI.
- Every script carries a `verdict` (the host's one-line take). `factory make` renders it as a
  3 s end card after the narration (music keeps playing via `apad`); `factory export` puts it
  in captions. This is the creator-perspective layer YouTube's 2025 policy asks for.
- Default ElevenLabs voice is premade **Adam** (`pNInz6obpgDQGcFmaJgB`): the narrator most
  viral Reddit-story channels use and the user's pick. Override with `--voice` or
  `ELEVENLABS_VOICE_ID`.
- Platform limits (durations, caption/hashtag caps, safe zones) live in `platforms.PLATFORMS`;
  `docs/PUBLISHING.md` has the upload-API notes per platform.

## The Five MCP Tools

| Tool | Blocking | Returns |
|---|---|---|
| `generate_image` | Yes (up to 3 min) | `{url, model, request_id}` |
| `generate_video` | Yes (up to 10 min) | `{url, model, request_id}` |
| `submit_video` | No | `{job_id, status, model}` |
| `poll_job` | No | `{status}` or `{status, url}` |
| `list_models` | No | grouped model catalog |

## Muapi client notes

- `mcp` is pinned `<2`: mcp 2.x renamed `FastMCP` → `MCPServer`. Migrating is a real change
  to `server.py`, not a pin bump.
- Retries 5xx up to `_MAX_RETRIES` with exponential backoff; 401/402/422/429 map to
  `MuapiError` with a clear message.
- `run()` = `submit()` + `poll()`; `submit()` + `check()` back the non-blocking tools.
- To add a model, append a `ModelInfo` to `MODELS` in `models.py` — nothing else changes.

## Testing conventions

- No network in tests: `respx` for HTTP, `monkeypatch` on `pinguz.muapi` for the bank.
- `tests/test_factory_assemble.py` does a real (tiny) ffmpeg render — keep it small so CI
  stays fast.
- Prefer testing pure functions (`captions.to_ass`, `timeline.plan`, `assemble.build_command`)
  over end-to-end.

## MCP registration

`.claude/mcp.json` points at the `pinguz` entry point. Manual: 
`claude mcp add pinguz --env MUAPI_API_KEY=sk-... -- pinguz`

## Higgsfield skills

`.claude/skills/*` are slash-command prompt guides for Higgsfield's models. They are
unrelated to the factory pipeline and do not call Pinguz. See `ATLAS_PRODUCTION_GUIDE.md`
for the skill-to-model mapping.
