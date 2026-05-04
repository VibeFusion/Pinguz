# Pinguz

An MCP server that gives Claude image and video generation, backed by [Muapi.ai](https://muapi.ai). Think of it as the open, BYO-key alternative to Higgsfield — same model lineup (Flux, Seedance, Kling, Veo, Wan, Hunyuan, Midjourney, Imagen, Nano Banana, …), wired straight into your Claude session.

## Tools

- `generate_image(prompt, model="flux-dev-image", aspect_ratio="1:1")` — text-to-image, returns a URL.
- `generate_video(prompt, model="seedance-v2.0-t2v", duration=5, aspect_ratio="16:9", quality="basic", image_url=None)` — text-to-video, or image-to-video when `image_url` is set with an `*-i2v` model.
- `list_models()` — supported model IDs grouped by category.

> Duration limits depend on the model. Seedance 2.0 supports 5/10/15s; Veo, Kling, and Wan offer their own ranges. The 5-second cap you may have seen is a per-model default, not a platform limit.

## Setup

```bash
pip install -e .
export MUAPI_API_KEY=sk-...   # get one at https://muapi.ai
pinguz                        # runs the MCP server over stdio
```

## Connect to Claude Code

```bash
claude mcp add pinguz -- pinguz
# or with the env var inline:
claude mcp add pinguz --env MUAPI_API_KEY=sk-... -- pinguz
```

Then in any Claude Code session: *"generate a 9:16 video of a penguin surfing a neon wave with seedance, 10 seconds"* — Claude will call `generate_video` and hand back the URL.

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

## Project layout

```
src/pinguz/
  server.py    # FastMCP tool definitions
  muapi.py     # async API client (submit + poll)
```

The Muapi pattern is async: `POST /api/v1/{model}` returns a `request_id`, then `GET /api/v1/predictions/{request_id}/result` is polled until `status == "completed"`. Image jobs wait up to 3 minutes; video jobs up to 10.
