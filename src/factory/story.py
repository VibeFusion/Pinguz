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


# Word budgets per target length. ElevenLabs Adam reads ~160 words per minute, so
# "short" lands at 45-50 s (Shorts/Reels sweet spot) and "long" clears the 60 s floor
# TikTok's Creator Rewards program requires.
LENGTHS: dict[str, tuple[int, int, str]] = {
    "short": (120, 140, "45-50 seconds"),
    "long": (175, 200, "65-75 seconds"),
}
DEFAULT_LENGTH = "short"
_LINT_SLACK = 10  # words either side of the budget before lint complains


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Video title, under 70 characters, curiosity-driven")
    style: str = Field(description="Subreddit-style genre, e.g. AITA, TIFU, petty revenge")
    hook: str = Field(description="The first spoken sentence. Must be a cold open — no preamble")
    narration: str = Field(
        description=(
            "Full spoken script including the hook. First person, past tense, plain "
            "conversational English, 120-140 words, ends on a question to the viewer "
            "or a withheld reveal — never a moral"
        )
    )
    hashtags: list[str] = Field(description="3-5 hashtags without the # symbol")
    verdict: str = Field(
        default="",
        description=(
            "The channel host's own one-line take on the story, 6-14 words, first person, "
            "opinionated, e.g. 'Ask him. Anyone who plans that far ahead is a keeper.' Shown "
            "as an end card after the narration; never spoken by the narrator"
        ),
    )

    @property
    def word_count(self) -> int:
        return len(self.narration.split())

    def lint(self, length: str = DEFAULT_LENGTH) -> list[str]:
        """Cheap structural checks a script must pass before it is voiced."""
        problems: list[str] = []
        lo, hi, _ = LENGTHS[length]
        n = self.word_count
        if not lo - _LINT_SLACK <= n <= hi + _LINT_SLACK:
            problems.append(f"{n} words (want {lo}-{hi})")
        first = self.narration.strip().split(".")[0].lower()
        if first.startswith(("so ", "so,", "story time", "okay so", "this happened")):
            problems.append("opens with preamble instead of the hook")
        tail = self.narration.strip().lower()
        withheld = ("worst part.", "part two.", "part 2.", "what happened next.")
        if not (tail.endswith("?") or tail.endswith(withheld)):
            problems.append("does not end on a question or a withheld reveal")
        return problems

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


_SCRIPT_SYSTEM_TEMPLATE = """\
You write narration scripts for {seconds} vertical story videos in the style of
popular Reddit story channels. The audio is the whole show: it plays over unrelated
"oddly satisfying" background footage with word-by-word captions.

Retention rules — these are what make the format work:
- Cold open. The first sentence IS the hook: the single most shocking, specific
  line of the story, stated flatly in first person. A concrete detail (a number,
  a relationship, an object) beats an adjective. No "so", no "story time", no
  context first. Cut the backstory; get to the drama.
- A second hook around 15 seconds in: a twist, a reveal, or an escalation.
- Withhold the payoff until the final sentences. Then END ON ENGAGEMENT: either a
  direct question to the viewer ("So. Was I wrong?") or a withheld reveal
  ("And that's not even the worst part."). Never a moral, a summary, or a
  lesson — nothing that lets the viewer feel finished before they comment.
- Plain spoken English, first person, past tense, short sentences. Read-aloud ready:
  no emojis, no markdown, no bracketed asides, no character names longer than one
  word, numbers written as words.
- {lo}-{hi} words. That is a hard ceiling: at ~160 words per minute it lands at
  {seconds}. Every sentence advances the conflict; cut anything that doesn't.
{extra}
Also give a `verdict`: the channel host's own one-line reaction to the story
(6-14 words, first person, an actual opinion). It is shown as an end card, not
spoken, so it must not repeat the closing question.

The story is original fiction you invent. It must not reproduce or closely
paraphrase any real post. Keep it PG-13: no slurs, no graphic violence, no
sexual content, nothing that targets a real person or a protected group. Avoid
templated distress ("same situation, same outcome") — each story needs a
premise, an escalation and an ending that are genuinely its own.
"""

_LONG_EXTRA = """\
- For this length the second hook lands around 15 seconds AND a third escalation
  around 40 seconds; the extra words buy one more turn of the screw, never more
  backstory.
"""


def script_system(length: str = DEFAULT_LENGTH) -> str:
    """The script agent's system prompt for a target length ("short" or "long")."""
    if length not in LENGTHS:
        raise ValueError(f"length must be one of {', '.join(LENGTHS)}")
    lo, hi, seconds = LENGTHS[length]
    extra = _LONG_EXTRA if length == "long" else ""
    return _SCRIPT_SYSTEM_TEMPLATE.format(lo=lo, hi=hi, seconds=seconds, extra=extra)


SCRIPT_SYSTEM = script_system(DEFAULT_LENGTH)

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
    length: str = DEFAULT_LENGTH,
    client: anthropic.Anthropic | None = None,
    model: str = MODEL,
) -> Script:
    """Turn a premise (or a rough draft) into a finished Script.

    `length` picks the word budget from LENGTHS: "short" for Shorts/Reels, "long"
    for a TikTok cut that clears the 60 s monetisation floor.
    """
    system = script_system(length)
    client = client or _client()
    if style:
        style_line = f"Style: {style}\n"
    else:
        style_line = f"Pick the best style from: {', '.join(STYLES)}\n"
    response = client.beta.messages.parse(
        model=model,
        max_tokens=4096,
        system=system,
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
