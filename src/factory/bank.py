"""Background clip bank: generate via Muapi, store locally, track in a manifest."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from pinguz import muapi

from . import assemble, procedural
from .prompts import ClipPrompt

MANIFEST = "manifest.json"


@dataclass(frozen=True)
class Clip:
    id: str
    path: Path
    category: str
    prompt: str
    duration: float
    model: str
    request_id: str

    def to_json(self) -> dict:
        d = asdict(self)
        d["path"] = self.path.name  # stored relative to the bank dir
        return d

    @classmethod
    def from_json(cls, d: dict, bank_dir: Path) -> Clip:
        return cls(
            id=d["id"],
            path=bank_dir / d["path"],
            category=d["category"],
            prompt=d["prompt"],
            duration=float(d["duration"]),
            model=d["model"],
            request_id=d.get("request_id", ""),
        )


class Bank:
    def __init__(self, dir: Path) -> None:
        self.dir = dir
        self._clips: list[Clip] = []
        self.load()

    @property
    def manifest_path(self) -> Path:
        return self.dir / MANIFEST

    def load(self) -> None:
        self._clips = []
        if self.manifest_path.exists():
            data = json.loads(self.manifest_path.read_text())
            self._clips = [Clip.from_json(d, self.dir) for d in data.get("clips", [])]

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        payload = {"clips": [c.to_json() for c in self._clips]}
        self.manifest_path.write_text(json.dumps(payload, indent=2))

    def add(self, clip: Clip) -> None:
        self._clips.append(clip)
        self.save()

    def clips(self, categories: list[str] | None = None) -> list[Clip]:
        if not categories:
            return list(self._clips)
        wanted = set(categories)
        return [c for c in self._clips if c.category in wanted]

    def categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self._clips:
            counts[c.category] = counts.get(c.category, 0) + 1
        return dict(sorted(counts.items()))


async def _download(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)


async def generate_one(
    bank: Bank,
    cp: ClipPrompt,
    *,
    model: str,
    duration: int,
    quality: str,
    max_wait: float,
) -> Clip:
    payload = {
        "prompt": cp.text,
        "aspect_ratio": "9:16",
        "duration": duration,
        "quality": quality,
    }
    request_id = await muapi.submit(model, payload)
    result = await muapi.poll(request_id, max_wait=max_wait)
    url = muapi.extract_url(result)
    clip_id = uuid.uuid4().hex[:8]
    bank.dir.mkdir(parents=True, exist_ok=True)
    dest = bank.dir / f"{cp.category}-{clip_id}.mp4"
    await _download(url, dest)
    actual = await asyncio.to_thread(assemble.probe_duration, dest)
    clip = Clip(
        id=clip_id,
        path=dest,
        category=cp.category,
        prompt=cp.text,
        duration=actual,
        model=model,
        request_id=request_id,
    )
    bank.add(clip)
    return clip


async def generate(
    bank: Bank,
    prompts: list[ClipPrompt],
    *,
    model: str = "seedance-v2.0-t2v",
    duration: int = 10,
    quality: str = "basic",
    concurrency: int = 4,
    max_wait: float = 600.0,
    on_done: object = None,
) -> tuple[list[Clip], list[tuple[ClipPrompt, Exception]]]:
    """Generate every prompt with a concurrency cap. Failures don't stop the batch."""
    sem = asyncio.Semaphore(concurrency)
    done: list[Clip] = []
    failed: list[tuple[ClipPrompt, Exception]] = []

    async def worker(cp: ClipPrompt) -> None:
        async with sem:
            try:
                clip = await generate_one(
                    bank, cp, model=model, duration=duration, quality=quality, max_wait=max_wait
                )
            except Exception as exc:  # noqa: BLE001 - collect, report, keep going
                failed.append((cp, exc))
                if callable(on_done):
                    on_done(cp, None, exc)
                return
            done.append(clip)
            if callable(on_done):
                on_done(cp, clip, None)

    await asyncio.gather(*(worker(cp) for cp in prompts))
    return done, failed


def add_procedural(
    bank: Bank,
    kinds: list[str],
    *,
    per_kind: int = 2,
    seconds: float = 10.0,
    seed_base: int = 0,
    width: int = 540,
    height: int = 960,
) -> list[Clip]:
    """Render procedural clips straight into the bank — no API, no credits."""
    made: list[Clip] = []
    for kind in kinds:
        for i in range(per_kind):
            seed = seed_base + i
            bank.dir.mkdir(parents=True, exist_ok=True)
            dest = bank.dir / f"proc-{kind}-{seed}.mp4"
            procedural.render_clip(
                kind, dest, seconds=seconds, seed=seed, width=width, height=height
            )
            clip = Clip(
                id=f"{kind}{seed}",
                path=dest,
                category=f"proc-{kind}",
                prompt=f"procedural {kind} seed={seed}",
                duration=assemble.probe_duration(dest),
                model="procedural",
                request_id="",
            )
            bank.add(clip)
            made.append(clip)
    return made
