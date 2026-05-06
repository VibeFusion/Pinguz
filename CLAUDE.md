# Pinguz — Claude Code Context

## What This Project Is

Pinguz is a FastMCP server that wraps the [Muapi.ai](https://muapi.ai) API, giving Claude and other MCP clients five tools for AI image and video generation. It is **not** a web app or CLI tool for end users — it is an MCP server registered with Claude Code or Claude Desktop.

The project also ships 19 Higgsfield production skills in `.claude/skills/` for Claude to invoke via `/skill-name` commands.

## Commands

```bash
# Install in dev mode (required before first use)
pip install -e ".[dev]"

# Run the test suite
pytest

# Run tests with coverage
pytest --cov=pinguz

# Lint
ruff check src tests

# Format
ruff format src tests

# Type-check
mypy src

# End-to-end smoke test (requires a live, funded Muapi key)
MUAPI_API_KEY=sk-... python scripts/smoke_test.py
```

## Architecture

```
src/pinguz/
  __init__.py   — package version
  models.py     — typed model registry (ModelInfo dataclass + lookup helpers)
  muapi.py      — async HTTP client: submit / poll / run / check / extract_url
  server.py     — FastMCP tool definitions (the 5 exposed tools)
scripts/
  smoke_test.py — live API smoke test
tests/
  test_muapi.py  — HTTP layer tests using respx mocks
  test_server.py — tool logic tests using AsyncMock
.claude/
  mcp.json       — auto-registers the server in Claude Code
  skills/        — 19 Higgsfield production prompt skills
```

## The Five MCP Tools

| Tool | Blocking | Returns |
|---|---|---|
| `generate_image` | Yes (up to 3 min) | `{url, model, request_id}` |
| `generate_video` | Yes (up to 10 min) | `{url, model, request_id}` |
| `submit_video` | No | `{job_id, status, model}` |
| `poll_job` | No | `{status}` or `{status, url}` |
| `list_models` | No | grouped model catalog |

## Environment

```bash
export MUAPI_API_KEY=sk-...   # required; raises MuapiError if missing
```

## Model Registry

Models live in `src/pinguz/models.py`. To add a new model, append a `ModelInfo` entry to the `MODELS` list — the server auto-discovers it with no other changes required.

Categories: `image`, `t2v` (text-to-video), `i2v` (image-to-video).

## Muapi Client Notes

- Retries on 503 up to `_MAX_RETRIES` times with exponential backoff
- 401 → `MuapiError("Authentication failed")`
- 402 → `MuapiError("Billing issue")`
- 422 → `MuapiError("Invalid request: ...")`
- `run()` = `submit()` + `poll()` combined; use for blocking tools
- `submit()` + `check()` are the primitives used by `submit_video` / `poll_job`

## Testing

Tests use `pytest-asyncio` and `respx` for HTTP mocking. No network calls in the test suite. To add a new model test, add the model ID to `models.py` and assert its presence via `list_models()`.

## MCP Registration

`.claude/mcp.json` points to the `pinguz` entry point (installed by `pip install -e .`). After install, Claude Code auto-registers the server when this project directory is open.

Manual registration:
```bash
claude mcp add pinguz --env MUAPI_API_KEY=sk-... -- pinguz
```

## Higgsfield Skills

Skills in `.claude/skills/` are invoked as slash commands. They provide production-grade prompt templates for Higgsfield's image and video models. Skills are **Claude prompt guides only** — they do not call the Pinguz MCP tools (which wrap Muapi). For Higgsfield generations, use the separate Higgsfield MCP server (`mcp__e0de92df-85e7-40c1-be0c-eb8c879adb19__*`).

See `ATLAS_PRODUCTION_GUIDE.md` for a complete skill-to-model mapping and workflow documentation.
