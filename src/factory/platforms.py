"""Per-platform packaging: duration limits, safe zones, and post metadata.

One master 9:16 render is exported once per platform: the video is trimmed only
when it exceeds that platform's ceiling, and a `meta.json` carries the title,
caption, hashtags and any warnings (e.g. TikTok Creator Rewards wants ≥ 60 s).
Numbers are the published limits as of 2026; adjust `PLATFORMS` when they move.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import assemble


@dataclass(frozen=True)
class SafeZone:
    """Fractions of the frame that platform UI may cover (top / bottom / right)."""

    top: float
    bottom: float
    right: float


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    max_seconds: float
    min_seconds: float
    # Below this the platform's monetisation program does not count the view.
    monetise_min_seconds: float | None
    title_max: int
    caption_max: int
    hashtags_max: int
    hashtags_recommended: int
    safe_zone: SafeZone
    notes: tuple[str, ...] = ()
    required_tags: tuple[str, ...] = ()


# Safe zones from the platforms' own creator guidelines: keep text out of the top
# ~12-14 % (status bar, "Following/For You"), the bottom ~30-35 % (caption, music,
# progress bar) and the right ~15 % (like/comment/share rail).
_SHORT_FORM_ZONE = SafeZone(top=0.14, bottom=0.35, right=0.16)

PLATFORMS: dict[str, Platform] = {
    "youtube": Platform(
        key="youtube", name="YouTube Shorts",
        max_seconds=180.0, min_seconds=5.0, monetise_min_seconds=None,
        title_max=100, caption_max=5000, hashtags_max=15, hashtags_recommended=3,
        safe_zone=_SHORT_FORM_ZONE, required_tags=("Shorts",),
        notes=(
            "Under the July 2025 inauthentic-content policy, mass-produced narration over "
            "stock footage is demonetisation-prone: add a creator perspective (verdict, "
            "reaction, or on-screen commentary) before scaling.",
            "Title doubles as the Shorts feed headline; the first 40 chars carry the hook.",
        ),
    ),
    "instagram": Platform(
        key="instagram", name="Instagram Reels",
        max_seconds=180.0, min_seconds=3.0, monetise_min_seconds=None,
        title_max=0, caption_max=2200, hashtags_max=30, hashtags_recommended=5,
        safe_zone=_SHORT_FORM_ZONE,
        notes=("Reels have no title field: the first line of the caption is the hook.",
               "Cover frame is picked from the video; the 0-3 s title card is what shows in grid."),
    ),
    "tiktok": Platform(
        key="tiktok", name="TikTok",
        max_seconds=600.0, min_seconds=3.0, monetise_min_seconds=60.0,
        title_max=0, caption_max=4000, hashtags_max=10, hashtags_recommended=4,
        safe_zone=_SHORT_FORM_ZONE,
        notes=("Creator Rewards Program only pays on videos of 60 s or longer that hold "
               "attention; sub-60 s uploads are discovery only.",
               "Caption text is searchable: put the story keywords in plain words, not only tags."),
    ),
    "facebook": Platform(
        key="facebook", name="Facebook Reels",
        max_seconds=90.0, min_seconds=3.0, monetise_min_seconds=None,
        title_max=0, caption_max=2200, hashtags_max=10, hashtags_recommended=3,
        safe_zone=_SHORT_FORM_ZONE,
        notes=("Reels over 90 s upload as regular video posts, not Reels.",),
    ),
    "snapchat": Platform(
        key="snapchat", name="Snapchat Spotlight",
        max_seconds=60.0, min_seconds=5.0, monetise_min_seconds=None,
        title_max=0, caption_max=160, hashtags_max=5, hashtags_recommended=2,
        safe_zone=SafeZone(top=0.16, bottom=0.30, right=0.16),
        notes=("Spotlight submissions are capped at 60 s; longer masters are trimmed to the "
               "hook and the export flags it.",
               "Topics use #hashtags in the description; keep it one line."),
    ),
    "reddit": Platform(
        key="reddit", name="Reddit",
        max_seconds=900.0, min_seconds=1.0, monetise_min_seconds=None,
        title_max=300, caption_max=40000, hashtags_max=0, hashtags_recommended=0,
        safe_zone=SafeZone(top=0.0, bottom=0.0, right=0.0),
        notes=("Story subreddits are text-first: the export includes a text post (title + "
               "narration) alongside the video for subs that allow video.",
               "Hashtags do nothing on Reddit; flair and subreddit choice do."),
    ),
}

ORDER = ("youtube", "instagram", "tiktok", "facebook", "snapchat", "reddit")


@dataclass
class Export:
    platform: str
    video: str
    seconds: float
    trimmed: bool
    title: str
    caption: str
    hashtags: list[str]
    warnings: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


def _clip_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def build_caption(meta: dict, platform: Platform) -> tuple[str, str, list[str]]:
    """Return (title, caption, hashtags) for one platform from a script's metadata."""
    title = str(meta.get("title") or meta.get("hook") or "").strip()
    hook = str(meta.get("hook") or title).strip()
    raw_tags = [str(t).lstrip("#").strip() for t in meta.get("hashtags") or []]
    raw_tags = [t for t in raw_tags if t]
    tags = list(platform.required_tags) + [t for t in raw_tags if t not in platform.required_tags]
    tags = tags[: platform.hashtags_max]
    tag_line = " ".join(f"#{t}" for t in tags)

    if platform.key == "reddit":
        body = str(meta.get("narration") or "").strip()
        return _clip_text(title, platform.title_max), body, []

    verdict = str(meta.get("verdict") or "").strip()
    cta = "Full story in the video. What would you do?"
    parts = [hook, f"My take: {verdict}" if verdict else "", cta, tag_line]
    caption = "\n\n".join(p for p in parts if p)
    return _clip_text(title, platform.title_max), _clip_text(caption, platform.caption_max), tags


def plan_export(meta: dict, seconds: float, platform: Platform) -> Export:
    """Decide trim/warnings for one platform without touching any file."""
    title, caption, tags = build_caption(meta, platform)
    trimmed = seconds > platform.max_seconds
    out_seconds = min(seconds, platform.max_seconds)
    warnings: list[str] = []
    if trimmed:
        warnings.append(
            f"master is {seconds:.1f}s; trimmed to the {platform.max_seconds:.0f}s ceiling — "
            "the payoff is cut, re-script a shorter version for this platform"
        )
    if seconds < platform.min_seconds:
        warnings.append(f"shorter than the {platform.min_seconds:.0f}s minimum")
    if platform.monetise_min_seconds and seconds < platform.monetise_min_seconds:
        warnings.append(
            f"{seconds:.1f}s is under the {platform.monetise_min_seconds:.0f}s monetisation "
            "floor; publish for reach, or cut a ≥60 s version"
        )
    extra: dict = {"safe_zone": asdict(platform.safe_zone), "notes": list(platform.notes)}
    if platform.key == "reddit":
        extra["subreddits"] = suggest_subreddits(str(meta.get("style") or ""))
    return Export(
        platform=platform.key, video="", seconds=out_seconds, trimmed=trimmed,
        title=title, caption=caption, hashtags=tags, warnings=warnings, extra=extra,
    )


_SUBREDDITS: dict[str, tuple[str, ...]] = {
    "aita": ("AmItheAsshole", "AITAH", "TwoHotTakes"),
    "tifu": ("tifu", "stories", "TwoHotTakes"),
    "revenge": ("pettyrevenge", "ProRevenge", "MaliciousCompliance"),
    "confession": ("confession", "TrueOffMyChest", "offmychest"),
    "relationship": ("relationship_advice", "TwoHotTakes", "BestofRedditorUpdates"),
    "entitled": ("entitledparents", "EntitledPeople", "ChoosingBeggars"),
    "work": ("antiwork", "MaliciousCompliance", "TalesFromRetail"),
    "creepy": ("LetsNotMeet", "nosleep", "creepyencounters"),
}


def suggest_subreddits(style: str) -> list[str]:
    key = style.lower()
    for needle, subs in _SUBREDDITS.items():
        if needle in key:
            return list(subs)
    return ["stories", "TwoHotTakes", "BestofRedditorUpdates"]


def _trim(src: Path, dst: Path, seconds: float) -> None:
    cmd = [
        assemble.ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-t", f"{seconds:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise assemble.RenderError(proc.stderr.strip()[-2000:] or "ffmpeg trim failed")


def export_all(
    video: Path,
    meta: dict,
    out_dir: Path,
    *,
    platforms: list[str] | None = None,
    seconds: float | None = None,
) -> list[Export]:
    """Write <out_dir>/<platform>/{video.mp4, meta.json[, post.md]} for each platform."""
    keys = platforms or list(ORDER)
    unknown = [k for k in keys if k not in PLATFORMS]
    if unknown:
        raise ValueError(f"unknown platform(s): {', '.join(unknown)}")
    total = seconds if seconds is not None else assemble.probe_duration(video)
    results: list[Export] = []
    for key in keys:
        p = PLATFORMS[key]
        ex = plan_export(meta, total, p)
        dest = out_dir / key
        dest.mkdir(parents=True, exist_ok=True)
        target = dest / "video.mp4"
        if ex.trimmed:
            _trim(video, target, ex.seconds)
        else:
            shutil.copyfile(video, target)
        ex.video = str(target)
        (dest / "meta.json").write_text(json.dumps(asdict(ex), indent=2))
        if key == "reddit":
            subs = ", ".join(f"r/{s}" for s in ex.extra.get("subreddits", []))
            (dest / "post.md").write_text(
                f"# {ex.title}\n\n{ex.caption}\n\n---\nSuggested subreddits: {subs}\n"
            )
        results.append(ex)
    return results
