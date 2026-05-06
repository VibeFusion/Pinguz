#!/usr/bin/env python3
"""Quick end-to-end smoke test against the real Muapi.ai API.

Usage:
    MUAPI_API_KEY=sk-... python scripts/smoke_test.py

Runs one image generation and one short video generation and prints the
output URLs. Requires a funded Muapi account.
"""

from __future__ import annotations

import asyncio
import os
import sys


async def main() -> None:
    if not os.environ.get("MUAPI_API_KEY"):
        sys.exit("Set MUAPI_API_KEY before running the smoke test.")

    # import after key check so the error message is clean
    from pinguz import muapi

    print("▶ Submitting image (flux-schnell)…")
    result = await muapi.run(
        "flux-schnell",
        {"prompt": "a single red apple on a white background", "aspect_ratio": "1:1"},
        max_wait=120.0,
    )
    print(f"  ✓ Image: {result.url}")
    print(f"    job_id: {result.request_id}")

    print("\n▶ Submitting video (seedance-v2.0-t2v, 5 s)…")
    result = await muapi.run(
        "seedance-v2.0-t2v",
        {
            "prompt": "a red apple spinning slowly on a white surface",
            "aspect_ratio": "1:1",
            "duration": 5,
            "quality": "basic",
        },
        max_wait=300.0,
    )
    print(f"  ✓ Video: {result.url}")
    print(f"    job_id: {result.request_id}")

    print("\nSmoke test passed ✓")


if __name__ == "__main__":
    asyncio.run(main())
