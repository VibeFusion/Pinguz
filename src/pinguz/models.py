"""Model registry with metadata for every supported Muapi.ai model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Category = Literal["image", "t2v", "i2v"]


@dataclass(frozen=True)
class ModelInfo:
    id: str
    category: Category
    description: str
    max_duration: int | None = None  # seconds; None for image models


MODELS: list[ModelInfo] = [
    # ── Images ──────────────────────────────────────────────────────────────
    ModelInfo("flux-dev-image", "image", "Flux Dev — high quality, moderate speed"),
    ModelInfo("flux-2-pro", "image", "Flux Pro 2 — highest quality"),
    ModelInfo("flux-schnell", "image", "Flux Schnell — fastest, still good quality"),
    ModelInfo("flux-kontext-pro", "image", "Flux Kontext Pro — context-aware editing"),
    ModelInfo("midjourney", "image", "Midjourney — photorealistic and artistic"),
    ModelInfo("seedream", "image", "Seedream — stylized generations"),
    ModelInfo("nano-banana", "image", "Nano Banana Pro — fast and creative"),
    ModelInfo("imagen4", "image", "Google Imagen 4 — photorealistic"),
    ModelInfo("gpt4o", "image", "GPT-4o native image generation"),
    ModelInfo("qwen", "image", "Qwen image generation"),
    ModelInfo("hidream-fast", "image", "HiDream Fast — rapid generations"),
    # ── Text-to-video ────────────────────────────────────────────────────────
    ModelInfo("seedance-v2.0-t2v", "t2v", "Seedance 2.0 — versatile, 5/10/15 s",
              max_duration=15),
    ModelInfo("kling-v2.6-pro-t2v", "t2v", "Kling 2.6 Pro — cinematic quality",
              max_duration=10),
    ModelInfo("veo3.1-text-to-video", "t2v", "Google Veo 3.1 — best-in-class realism",
              max_duration=8),
    ModelInfo("wan2.5-text-to-video", "t2v", "Wan 2.5 — fast and expressive",
              max_duration=10),
    ModelInfo("hunyuan-text-to-video", "t2v", "Hunyuan — detailed scene rendering",
              max_duration=10),
    ModelInfo("minimax-hailuo-02-pro-t2v", "t2v", "Minimax Hailuo 02 Pro — dynamic motion",
              max_duration=6),
    # ── Image-to-video ───────────────────────────────────────────────────────
    ModelInfo("seedance-v2.0-i2v", "i2v", "Seedance 2.0 I2V — animate any image, 5/10/15 s",
              max_duration=15),
    ModelInfo("kling-v2.6-pro-i2v", "i2v", "Kling 2.6 Pro I2V — smooth motion from image",
              max_duration=10),
    ModelInfo("veo3.1-image-to-video", "i2v", "Google Veo 3.1 I2V — premium quality",
              max_duration=8),
    ModelInfo("wan2.5-image-to-video", "i2v", "Wan 2.5 I2V — natural motion",
              max_duration=10),
]

_by_id: dict[str, ModelInfo] = {m.id: m for m in MODELS}


def get(model_id: str) -> ModelInfo | None:
    return _by_id.get(model_id)


def by_category(cat: Category) -> list[ModelInfo]:
    return [m for m in MODELS if m.category == cat]


def ids_by_category(cat: Category) -> list[str]:
    return [m.id for m in MODELS if m.category == cat]
