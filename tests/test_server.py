"""Tests for the MCP server tool logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pinguz import muapi
from pinguz.server import (
    generate_image,
    generate_video,
    list_models,
    poll_job,
    submit_video,
)


def _mock_result(
    url: str = "https://cdn.example.com/out.mp4",
    model: str = "flux-dev-image",
    rid: str = "r1",
):
    return muapi.MuapiResult(url=url, request_id=rid, model=model, outputs=[{"url": url}])


# ── generate_image ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_image_success():
    with patch("pinguz.server.muapi.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_result(model="flux-dev-image")
        result = await generate_image("a sunset", model="flux-dev-image")
    assert result["url"] == "https://cdn.example.com/out.mp4"
    assert result["model"] == "flux-dev-image"
    assert "request_id" in result


@pytest.mark.asyncio
async def test_generate_image_unknown_model():
    result = await generate_image("a cat", model="not-a-real-model")
    assert "error" in result
    assert "Unknown model" in result["error"]


@pytest.mark.asyncio
async def test_generate_image_wrong_category():
    result = await generate_image("a cat", model="seedance-v2.0-t2v")
    assert "error" in result
    assert "t2v" in result["error"]


@pytest.mark.asyncio
async def test_generate_image_api_error():
    with patch("pinguz.server.muapi.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = muapi.MuapiError("Authentication failed")
        result = await generate_image("a cat", model="flux-dev-image")
    assert result == {"error": "Authentication failed"}


# ── generate_video ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_video_t2v_success():
    with patch("pinguz.server.muapi.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_result(model="seedance-v2.0-t2v")
        result = await generate_video("ocean waves", model="seedance-v2.0-t2v", duration=5)
    assert result["url"] == "https://cdn.example.com/out.mp4"


@pytest.mark.asyncio
async def test_generate_video_duration_over_max():
    result = await generate_video("ocean waves", model="seedance-v2.0-t2v", duration=99)
    assert "error" in result
    assert "max" in result["error"]


@pytest.mark.asyncio
async def test_generate_video_i2v_missing_image_url():
    result = await generate_video("dancing", model="seedance-v2.0-i2v")
    assert "error" in result
    assert "image_url" in result["error"]


@pytest.mark.asyncio
async def test_generate_video_i2v_with_image_url():
    with patch("pinguz.server.muapi.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = _mock_result(model="seedance-v2.0-i2v")
        result = await generate_video(
            "dancing", model="seedance-v2.0-i2v", image_url="https://example.com/img.jpg"
        )
    assert result["url"] == "https://cdn.example.com/out.mp4"
    _, kwargs = mock_run.call_args
    assert kwargs.get("payload", mock_run.call_args[0][1]).get("images_list") == ["https://example.com/img.jpg"]


# ── submit_video / poll_job ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_video_returns_job_id():
    with patch("pinguz.server.muapi.submit", new_callable=AsyncMock) as mock_sub:
        mock_sub.return_value = "job-xyz"
        result = await submit_video("city timelapse", model="seedance-v2.0-t2v")
    assert result["job_id"] == "job-xyz"
    assert result["status"] == "submitted"


@pytest.mark.asyncio
async def test_poll_job_processing():
    with patch("pinguz.server.muapi.check", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"status": "processing"}
        result = await poll_job("job-xyz")
    assert result["status"] == "processing"
    assert "url" not in result


@pytest.mark.asyncio
async def test_poll_job_completed():
    with patch("pinguz.server.muapi.check", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "status": "completed",
            "outputs": [{"url": "https://cdn.example.com/vid.mp4"}],
        }
        result = await poll_job("job-xyz")
    assert result["status"] == "completed"
    assert result["url"] == "https://cdn.example.com/vid.mp4"


# ── list_models ───────────────────────────────────────────────────────────────


def test_list_models_all():
    result = list_models()
    assert set(result.keys()) == {"image", "t2v", "i2v"}
    assert any(m["id"] == "flux-dev-image" for m in result["image"])
    assert any(m["id"] == "seedance-v2.0-t2v" for m in result["t2v"])


def test_list_models_filtered():
    result = list_models(category="image")
    assert "image" in result
    assert "t2v" not in result


def test_list_models_invalid_category():
    result = list_models(category="bad")
    assert "error" in result


def test_list_models_t2v_include_max_duration():
    result = list_models(category="t2v")
    seedance = next(m for m in result["t2v"] if m["id"] == "seedance-v2.0-t2v")
    assert seedance["max_duration_s"] == 15
