"""Pinguz MCP server — exposes Muapi.ai image and video generation as tools."""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .muapi import MuapiClient, MuapiError

IMAGE_MODELS = [
    "flux-dev-image",
    "flux-2-pro",
    "flux-schnell",
    "flux-kontext-pro",
    "midjourney",
    "seedream",
    "nano-banana",
    "imagen4",
    "gpt4o",
    "qwen",
    "hidream-fast",
]

T2V_MODELS = [
    "seedance-v2.0-t2v",
    "kling-v2.6-pro-t2v",
    "veo3.1-text-to-video",
    "wan2.5-text-to-video",
    "hunyuan-text-to-video",
    "minimax-hailuo-02-pro-t2v",
]

I2V_MODELS = [
    "seedance-v2.0-i2v",
    "kling-v2.6-pro-i2v",
    "veo3.1-image-to-video",
    "wan2.5-image-to-video",
]

mcp = FastMCP("pinguz")


def _first_url(result: dict) -> str:
    outputs = result.get("outputs") or []
    if not outputs:
        return f"No outputs returned: {result}"
    first = outputs[0]
    return first.get("url") if isinstance(first, dict) else str(first)


@mcp.tool()
async def generate_image(
    prompt: Annotated[str, Field(description="Text description of the desired image")],
    model: Annotated[
        str,
        Field(description=f"Model ID. One of: {', '.join(IMAGE_MODELS)}"),
    ] = "flux-dev-image",
    aspect_ratio: Annotated[
        str, Field(description="Aspect ratio, e.g. 1:1, 16:9, 9:16")
    ] = "1:1",
) -> str:
    """Generate an image from text. Returns the URL of the generated image."""
    try:
        client = MuapiClient()
        result = await client.run(
            model, {"prompt": prompt, "aspect_ratio": aspect_ratio}, max_wait=180.0
        )
    except MuapiError as e:
        return f"Error: {e}"
    return _first_url(result)


@mcp.tool()
async def generate_video(
    prompt: Annotated[str, Field(description="Text description of the video scene")],
    model: Annotated[
        str,
        Field(
            description=(
                "Model ID. Text-to-video: "
                + ", ".join(T2V_MODELS)
                + ". Image-to-video (set image_url): "
                + ", ".join(I2V_MODELS)
            )
        ),
    ] = "seedance-v2.0-t2v",
    duration: Annotated[
        int,
        Field(description="Duration in seconds. Common values: 5, 10, 15 (model-dependent)"),
    ] = 5,
    aspect_ratio: Annotated[str, Field(description="Aspect ratio, e.g. 16:9, 9:16")] = "16:9",
    quality: Annotated[str, Field(description="'basic' or 'high'")] = "basic",
    image_url: Annotated[
        str | None,
        Field(
            description="Public URL of a starting image. Required when using an i2v model."
        ),
    ] = None,
) -> str:
    """Generate a video from text or from a starting image. Returns the URL."""
    payload: dict = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "quality": quality,
    }
    if image_url:
        payload["images_list"] = [image_url]
    try:
        client = MuapiClient()
        result = await client.run(model, payload, max_wait=600.0)
    except MuapiError as e:
        return f"Error: {e}"
    return _first_url(result)


@mcp.tool()
def list_models() -> dict:
    """List supported Muapi.ai model IDs by category."""
    return {
        "image": IMAGE_MODELS,
        "text_to_video": T2V_MODELS,
        "image_to_video": I2V_MODELS,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
