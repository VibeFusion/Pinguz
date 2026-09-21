"""Script agent: turn an idea into a retention-optimised narration script.

Stories are original and synthetic — never scraped — so there is no Reddit
ToS exposure and the hook can be tuned directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel, ConfigDict, Field

MODEL = "claude-opus-5"
_BETAS = ["server-side-fallback-2026-07-01"]

STYLES = [
    "AITA",
    "TIFU",
    "petty revenge",
    "malicious compliance",
    "confession",
    "entitled parents",
    "workplace drama",
    "relationship advice",
]


class ScriptError(Exception):
    """Raised when the model refuses or returns an unusable script."""


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Video title, under 70 characters, curiosity-driven")
    style: str = Field(description="Subreddit-style genre, e.g. AITA, TIFU, petty revenge")
    hook: str = Field(description="The first spoken sentence. Must be a cold open — no preamble")
    narration: str = Field(
        description=(
            "Full spoken script including the hook. First person, past tense, plain "
            "conversational English, 130-170 words, ends on the payoff line"
        )
    )
    hashtags: list[str] = Field(description="3-5 hashtags without the # symbol")

    @property
    def word_count(self) -> int:
        return len(self.narration.split())

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> Script:
        return cls.model_validate_json(path.read_text())


class Idea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    premise: str = Field(description="One-sentence premise of the story")
    style: str = Field(description="Best-fit style from the allowed list")
    why_it_hooks: str = Field(description="The emotional/curiosity trigger, in one clause")


class IdeaList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideas: list[Idea]


SCRIPT_SYSTEM = """\
You write narration scripts for 45-60 second vertical story videos in the style of
popular Reddit story channels. The audio is the whole show: it plays over unrelated
"oddly satisfying" background footage with word-by-word captions.

Retention rules — these are what make the format work:
- Cold open. The first sentence IS the hook: a shocking claim, a confession, or an
  impossible situation stated flatly. No "so", no "story time", no context first.
- A second hook around 15 seconds in: a twist, a reveal, or an escalation.
- Withhold the payoff until the final sentence. The last line resolves the tension
  and lands as a punchline or a gut-punch.
- Plain spoken English, first person, past tense, short sentences. Read-aloud ready:
  no emojis, no markdown, no bracketed asides, no character names longer than one
  word, numbers written as words.
- 130-170 words. Every sentence advances the story; cut anything that doesn't.

The story is original fiction you invent. It must not reproduce or closely
paraphrase any real post. Keep it PG-13: no slurs, no graphic violence, no
sexual content, nothing that targets a real person or a protected group.
"""

IDEAS_SYSTEM = """\
You generate premises for original 45-60 second Reddit-style story videos. Each
premise must contain a built-in hook: an impossible situation, a betrayal with a
twist, a satisfying comeuppance, or a confession with a reveal. Vary the settings
(work, family, neighbours, school, travel, dating, roommates) and avoid clichés
already saturated on the platform. Premises are original fiction, PG-13.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _check_refusal(response: BetaMessage) -> None:
    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        why = getattr(details, "explanation", None) or "no explanation"
        raise ScriptError(f"Model declined this request: {why}")
    if response.stop_reason == "max_tokens":
        raise ScriptError("Response was cut off — increase max_tokens")


def write_script(
    idea: str,
    *,
    style: str | None = None,
    client: anthropic.Anthropic | None = None,
    model: str = MODEL,
) -> Script:
    """Turn a premise (or a rough draft) into a finished Script."""
    client = client or _client()
    if style:
        style_line = f"Style: {style}\n"
    else:
        style_line = f"Pick the best style from: {', '.join(STYLES)}\n"
    response = client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        system=SCRIPT_SYSTEM,
        messages=[{"role": "user", "content": f"{style_line}Premise or draft:\n{idea}"}],
        output_format=Script,
        output_config={"effort": "medium"},
        betas=_BETAS,
        fallbacks="default",
    )
    _check_refusal(response)
    script = response.parsed_output
    if script is None:
        raise ScriptError("Model returned no structured output")
    return script


def generate_ideas(
    niche: str,
    n: int = 10,
    *,
    client: anthropic.Anthropic | None = None,
    model: str = MODEL,
) -> list[Idea]:
    """Produce `n` original premises for a niche (e.g. 'petty revenge at work')."""
    client = client or _client()
    response = client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        system=IDEAS_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Niche: {niche}\nGenerate exactly {n} premises. "
                    f"Allowed styles: {', '.join(STYLES)}."
                ),
            }
        ],
        output_format=IdeaList,
        output_config={"effort": "medium"},
        betas=_BETAS,
        fallbacks="default",
    )
    _check_refusal(response)
    parsed = response.parsed_output
    if parsed is None:
        raise ScriptError("Model returned no structured output")
    return parsed.ideas


def save_ideas(ideas: list[Idea], path: Path) -> None:
    path.write_text(json.dumps([i.model_dump() for i in ideas], indent=2))
