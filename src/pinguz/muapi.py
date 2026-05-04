"""Async client for the Muapi.ai REST API."""

from __future__ import annotations

import asyncio
import os

import httpx

BASE_URL = "https://api.muapi.ai/api/v1"


class MuapiError(Exception):
    """Raised when the Muapi API returns an error or a job fails."""


class MuapiClient:
    def __init__(self, api_key: str | None = None, request_timeout: float = 60.0):
        key = api_key or os.environ.get("MUAPI_API_KEY")
        if not key:
            raise MuapiError("MUAPI_API_KEY is not set")
        self._headers = {"x-api-key": key, "Content-Type": "application/json"}
        self._timeout = request_timeout

    async def submit(self, model: str, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                f"{BASE_URL}/{model}", json=payload, headers=self._headers
            )
        if r.status_code == 401:
            raise MuapiError("Authentication failed — check MUAPI_API_KEY")
        if r.status_code == 402:
            raise MuapiError("Billing issue — insufficient credits on Muapi account")
        if r.status_code == 422:
            raise MuapiError(f"Invalid request: {r.text}")
        if r.status_code == 429:
            raise MuapiError("Rate limited — try again shortly")
        r.raise_for_status()
        data = r.json()
        request_id = data.get("request_id")
        if not request_id:
            raise MuapiError(f"No request_id in response: {data}")
        return request_id

    async def wait(
        self, request_id: str, *, max_wait: float, interval: float = 3.0
    ) -> dict:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + max_wait
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while loop.time() < deadline:
                r = await client.get(
                    f"{BASE_URL}/predictions/{request_id}/result",
                    headers=self._headers,
                )
                r.raise_for_status()
                data = r.json()
                status = data.get("status")
                if status == "completed":
                    return data
                if status == "failed":
                    raise MuapiError(f"Generation failed: {data}")
                await asyncio.sleep(interval)
        raise MuapiError(f"Timed out after {max_wait}s waiting for {request_id}")

    async def run(self, model: str, payload: dict, *, max_wait: float) -> dict:
        request_id = await self.submit(model, payload)
        return await self.wait(request_id, max_wait=max_wait)
