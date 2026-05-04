"""Pinguz MCP server — AI image and video generation via Muapi.ai."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import models, muapi

mcp = FastMCP("pinguz")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _image_ids() -> str:
    return ", ".join(models.ids_by_category("image"))


def _t2v_ids() -> str:
    return ", ".join(models.ids_by_category("t2v"))


def _i2v_ids() -> str:
    return ", ".join(models.ids_by_category("i2v"))


def _validate_model(model_id: str, *categories: models.Category) -> str | None:
    """Return an error string if model_id is not in any of the given categories."""
    info = models.get(model_id)
    if info is None:
        valid = sum((models.ids_by_category(c) for c in categories), [])
        return f"Unknown model '{model_id}'. Valid: {', '.join(valid)}"
    if info.category not in categories:
        valid = sum((models.ids_by_category(c) for c in categories), [])
        cats = "/".join(categories)
        return (
            f"Model '{model_id}' is a {info.category!r} model, not {cats}. "
            f"Valid: {', '.join(valid)}"
        )
    return None


# ── Tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def generate_image(
    prompt: Annotated[str, Field(description="Detailed text description of the image")],
    model: Annotated[
        str,
        Field(description=f"Image model ID. Options: {_image_ids()}"),
    ] = "flux-dev-image",
    aspect_ratio: Annotated[
        str, Field(description="Aspect ratio — e.g. 1:1, 16:9, 9:16, 4:3, 3:4")
    ] = "1:1",
) -> dict:
    """Generate an image from a text prompt.

    Returns a dict with keys:
      url         — direct link to the generated image
      model       — model used
      request_id  — Muapi job ID for reference
    """
    if err := _validate_model(model, "image"):
        return {"error": err}
    try:
        result = await muapi.run(
            model, {"prompt": prompt, "aspect_ratio": aspect_ratio}, max_wait=180.0
        )
    except muapi.MuapiError as e:
        return {"error": str(e)}
    return {"url": result.url, "model": result.model, "request_id": result.request_id}


@mcp.tool()
async def generate_video(
    prompt: Annotated[str, Field(description="Detailed text description of the video scene")],
    model: Annotated[
        str,
        Field(
            description=(
                "Video model ID. Text-to-video: "
                + _t2v_ids()
                + ". Image-to-video (requires image_url): "
                + _i2v_ids()
            )
        ),
    ] = "seedance-v2.0-t2v",
    duration: Annotated[
        int,
        Field(
            description=(
                "Duration in seconds. Seedance supports 5/10/15; "
                "Veo 3.1 up to 8; Kling/Wan/Hunyuan up to 10; Minimax up to 6"
            )
        ),
    ] = 5,
    aspect_ratio: Annotated[
        str, Field(description="Aspect ratio — e.g. 16:9, 9:16, 1:1")
    ] = "16:9",
    quality: Annotated[
        str, Field(description="'basic' or 'high' (high costs more credits)")
    ] = "basic",
    image_url: Annotated[
        str | None,
        Field(
            description=(
                "Public URL of a starting image. Required when using an image-to-video model. "
                "The image must be publicly accessible (not a local path)."
            )
        ),
    ] = None,
) -> dict:
    """Generate a video from text (or from a starting image when image_url is set).

    This call blocks until the video is ready (up to 10 min for complex jobs).
    For fire-and-forget, use submit_video + poll_job instead.

    Returns a dict with keys:
      url         — direct link to the generated video
      model       — model used
      request_id  — Muapi job ID for reference
    """
    categories: tuple[models.Category, ...] = ("t2v", "i2v")
    if err := _validate_model(model, *categories):
        return {"error": err}
    info = models.get(model)
    if info and info.max_duration and duration > info.max_duration:
        return {"error": f"Model '{model}' max duration is {info.max_duration}s (got {duration}s)"}
    payload: dict = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "quality": quality,
    }
    if image_url:
        payload["images_list"] = [image_url]
    elif info and info.category == "i2v":
        return {"error": f"Model '{model}' is an image-to-video model and requires image_url"}
    try:
        result = await muapi.run(model, payload, max_wait=600.0)
    except muapi.MuapiError as e:
        return {"error": str(e)}
    return {"url": result.url, "model": result.model, "request_id": result.request_id}


@mcp.tool()
async def submit_video(
    prompt: Annotated[str, Field(description="Detailed text description of the video scene")],
    model: Annotated[
        str,
        Field(description=f"Video model ID. T2V: {_t2v_ids()}. I2V: {_i2v_ids()}"),
    ] = "seedance-v2.0-t2v",
    duration: Annotated[int, Field(description="Duration in seconds (5, 10, or 15)")] = 5,
    aspect_ratio: Annotated[str, Field(description="Aspect ratio, e.g. 16:9")] = "16:9",
    quality: Annotated[str, Field(description="'basic' or 'high'")] = "basic",
    image_url: Annotated[str | None, Field(description="Public image URL for i2v models")] = None,
) -> dict:
    """Submit a video generation job without waiting for it to complete.

    Use this for long videos where you don't want to block.
    Check the result later with poll_job(job_id).

    Returns a dict with keys:
      job_id   — pass this to poll_job to check status
      status   — always 'submitted'
      model    — model queued
    """
    categories: tuple[models.Category, ...] = ("t2v", "i2v")
    if err := _validate_model(model, *categories):
        return {"error": err}
    info = models.get(model)
    if info and info.max_duration and duration > info.max_duration:
        return {"error": f"Model '{model}' max duration is {info.max_duration}s (got {duration}s)"}
    payload: dict = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "quality": quality,
    }
    if image_url:
        payload["images_list"] = [image_url]
    elif info and info.category == "i2v":
        return {"error": f"Model '{model}' is an image-to-video model and requires image_url"}
    try:
        request_id = await muapi.submit(model, payload)
    except muapi.MuapiError as e:
        return {"error": str(e)}
    return {"job_id": request_id, "status": "submitted", "model": model}


@mcp.tool()
async def poll_job(
    job_id: Annotated[str, Field(description="The job_id returned by submit_video")],
) -> dict:
    """Check the status of a previously submitted video job.

    Returns a dict with keys:
      status      — 'processing', 'completed', or 'failed'
      url         — video URL (only present when status is 'completed')
      job_id      — echoed back for reference
    """
    try:
        data = await muapi.check(job_id)
    except muapi.MuapiError as e:
        return {"error": str(e)}
    status = data.get("status", "unknown")
    result: dict = {"job_id": job_id, "status": status}
    if status == "completed":
        try:
            result["url"] = muapi.extract_url(data)
        except muapi.MuapiError as e:
            result["error"] = str(e)
    return result


@mcp.tool()
def list_models(
    category: Annotated[
        str | None,
        Field(description="Filter by category: 'image', 't2v', or 'i2v'. Omit for all."),
    ] = None,
) -> dict:
    """List supported Muapi.ai model IDs with descriptions, grouped by category.

    Categories:
      image — text-to-image
      t2v   — text-to-video
      i2v   — image-to-video (requires a starting image URL)
    """
    cats: list[models.Category] = ["image", "t2v", "i2v"]
    if category:
        c = category.lower()
        if c not in cats:
            return {"error": f"Unknown category '{category}'. Choose from: {', '.join(cats)}"}
        cats = [c]  # type: ignore[list-item]
    return {
        cat: [
            {"id": m.id, "description": m.description}
            | ({"max_duration_s": m.max_duration} if m.max_duration else {})
            for m in models.by_category(cat)
        ]
        for cat in cats
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
