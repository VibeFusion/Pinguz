"""Tests for the Muapi.ai client using mocked HTTP."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from pinguz import muapi


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", "test-key")


SUBMIT_URL = f"{muapi.BASE_URL}/flux-dev-image"
RESULT_URL_TEMPLATE = f"{muapi.BASE_URL}/predictions/{{job_id}}/result"


# ── submit ────────────────────────────────────────────────────────────────────


@respx.mock
def test_submit_returns_request_id():
    respx.post(SUBMIT_URL).mock(
        return_value=httpx.Response(200, json={"request_id": "abc123"})
    )
    job_id = asyncio.run(muapi.submit("flux-dev-image", {"prompt": "cat"}))
    assert job_id == "abc123"


@respx.mock
def test_submit_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv("MUAPI_API_KEY", raising=False)
    with pytest.raises(muapi.MuapiError, match="MUAPI_API_KEY is not set"):
        asyncio.run(muapi.submit("flux-dev-image", {}))


@respx.mock
def test_submit_maps_401_to_auth_error():
    respx.post(SUBMIT_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(muapi.MuapiError, match="Authentication failed"):
        asyncio.run(muapi.submit("flux-dev-image", {"prompt": "x"}))


@respx.mock
def test_submit_maps_402_to_billing_error():
    respx.post(SUBMIT_URL).mock(return_value=httpx.Response(402))
    with pytest.raises(muapi.MuapiError, match="Billing issue"):
        asyncio.run(muapi.submit("flux-dev-image", {"prompt": "x"}))


@respx.mock
def test_submit_maps_422_to_validation_error():
    respx.post(SUBMIT_URL).mock(
        return_value=httpx.Response(422, text="bad aspect_ratio")
    )
    with pytest.raises(muapi.MuapiError, match="Invalid request"):
        asyncio.run(muapi.submit("flux-dev-image", {"prompt": "x"}))


@respx.mock
def test_submit_retries_on_503(monkeypatch):
    monkeypatch.setattr(muapi, "_MAX_RETRIES", 2)
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"request_id": "retried"})

    respx.post(SUBMIT_URL).mock(side_effect=side_effect)

    async def run():
        import unittest.mock as mock
        async def fast_sleep(n):
            pass
        with mock.patch("asyncio.sleep", fast_sleep):
            return await muapi.submit("flux-dev-image", {"prompt": "x"})

    job_id = asyncio.run(run())
    assert job_id == "retried"
    assert call_count == 3


# ── poll ─────────────────────────────────────────────────────────────────────


@respx.mock
def test_poll_returns_on_completed():
    url = RESULT_URL_TEMPLATE.format(job_id="job1")
    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            json={"status": "completed", "outputs": [{"url": "https://cdn.example.com/out.jpg"}]},
        )
    )
    result = asyncio.run(muapi.poll("job1", max_wait=10.0))
    assert result["status"] == "completed"


@respx.mock
def test_poll_raises_on_failed():
    url = RESULT_URL_TEMPLATE.format(job_id="job2")
    respx.get(url).mock(
        return_value=httpx.Response(200, json={"status": "failed", "error": "OOM"})
    )
    with pytest.raises(muapi.MuapiError, match="Generation failed"):
        asyncio.run(muapi.poll("job2", max_wait=10.0))


@respx.mock
def test_poll_times_out():
    url = RESULT_URL_TEMPLATE.format(job_id="job3")
    respx.get(url).mock(
        return_value=httpx.Response(200, json={"status": "processing"})
    )

    async def run():
        import asyncio as _asyncio
        import unittest.mock as mock
        async def fast_sleep(n):
            pass
        with mock.patch("asyncio.sleep", fast_sleep):
            loop = _asyncio.get_event_loop()
            tick = [0.0]
            def advancing_time():
                tick[0] += 5.0
                return tick[0]
            with mock.patch.object(loop, "time", advancing_time):
                return await muapi.poll("job3", max_wait=3.0)

    with pytest.raises(muapi.MuapiError, match="Timed out"):
        asyncio.run(run())


# ── extract_url ───────────────────────────────────────────────────────────────


def test_extract_url_from_dict_outputs():
    result = {"outputs": [{"url": "https://example.com/img.png"}]}
    assert muapi.extract_url(result) == "https://example.com/img.png"


def test_extract_url_raises_on_empty_outputs():
    with pytest.raises(muapi.MuapiError, match="No outputs"):
        muapi.extract_url({"outputs": []})


def test_extract_url_raises_on_missing_outputs():
    with pytest.raises(muapi.MuapiError, match="No outputs"):
        muapi.extract_url({})
