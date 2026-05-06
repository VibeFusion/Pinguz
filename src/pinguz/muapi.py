"""Async client for the Muapi.ai REST API with retry and structured results."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx

BASE_URL = "https://api.muapi.ai/api/v1"
_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})
_MAX_RETRIES = 3


class MuapiError(Exception):
    """Raised when the Muapi API returns an error or a generation fails."""


@dataclass
class MuapiResult:
    url: str
    request_id: str
    model: str
    outputs: list[dict]


def _api_key() -> str:
    key = os.environ.get("MUAPI_API_KEY", "").strip()
    if not key:
        raise MuapiError("MUAPI_API_KEY is not set")
    return key


def _raise_for_status(r: httpx.Response) -> None:
    if r.status_code == 401:
        raise MuapiError("Authentication failed — check MUAPI_API_KEY")
    if r.status_code == 402:
        raise MuapiError("Billing issue — insufficient credits on your Muapi account")
    if r.status_code == 422:
        raise MuapiError(f"Invalid request: {r.text}")
    if r.status_code == 429:
        raise MuapiError("Rate limited — please try again shortly")
    r.raise_for_status()


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    json: dict,
    headers: dict,
) -> httpx.Response:
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            r = await client.post(url, json=json, headers=headers)
            if r.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            return r
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise MuapiError(f"Network error after {_MAX_RETRIES} retries: {exc}") from exc
    raise MuapiError(f"Request failed after {_MAX_RETRIES} retries") from last_exc


async def submit(model: str, payload: dict) -> str:
    """POST a generation request and return the request_id."""
    key = _api_key()
    headers = {"x-api-key": key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await _post_with_retry(
            client, f"{BASE_URL}/{model}", json=payload, headers=headers
        )
    _raise_for_status(r)
    data = r.json()
    request_id = data.get("request_id")
    if not request_id:
        raise MuapiError(f"No request_id in response: {data}")
    return request_id


async def poll(
    request_id: str,
    *,
    max_wait: float,
    interval: float = 3.0,
) -> dict:
    """Poll until a job completes or times out. Returns the raw result dict."""
    key = _api_key()
    headers = {"x-api-key": key}
    loop = asyncio.get_event_loop()
    deadline = loop.time() + max_wait
    async with httpx.AsyncClient(timeout=30.0) as client:
        while loop.time() < deadline:
            r = await client.get(
                f"{BASE_URL}/predictions/{request_id}/result",
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            if status == "completed":
                return data
            if status == "failed":
                raise MuapiError(f"Generation failed: {data.get('error', data)}")
            await asyncio.sleep(interval)
    raise MuapiError(f"Timed out after {max_wait:.0f}s — job {request_id} still processing")


async def check(request_id: str) -> dict:
    """Single status check (no waiting). Returns the raw result dict."""
    key = _api_key()
    headers = {"x-api-key": key}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{BASE_URL}/predictions/{request_id}/result",
            headers=headers,
        )
    r.raise_for_status()
    return r.json()


def extract_url(result: dict) -> str:
    outputs = result.get("outputs") or []
    if not outputs:
        raise MuapiError(f"No outputs in result: {result}")
    first = outputs[0]
    url = first.get("url") if isinstance(first, dict) else str(first)
    if not url:
        raise MuapiError(f"No URL in first output: {first}")
    return url


async def run(model: str, payload: dict, *, max_wait: float) -> MuapiResult:
    """Submit a job, wait for it, and return a structured MuapiResult."""
    request_id = await submit(model, payload)
    result = await poll(request_id, max_wait=max_wait)
    url = extract_url(result)
    return MuapiResult(
        url=url,
        request_id=request_id,
        model=model,
        outputs=result.get("outputs", []),
    )
