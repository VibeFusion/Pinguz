"""Tests for the script contract (no network — the model call is not exercised)."""

from __future__ import annotations

import pytest

from factory import story

GOOD = (
    "My landlord thanked me for the extra two thousand dollars, and I had no idea what he "
    "was talking about. " + "I paid my half every month. " * 18 + "So. Do I ask him?"
)


def test_script_lint_passes_a_good_script():
    s = story.Script(title="t", style="AITA", hook="h", narration=GOOD, hashtags=["a"])
    assert 110 <= s.word_count <= 150
    assert s.lint() == []


def test_script_lint_flags_preamble_length_and_ending():
    bad = "So story time. " + "This is a sentence about nothing at all. " * 25 + "The end."
    s = story.Script(title="t", style="AITA", hook="h", narration=bad, hashtags=[])
    problems = s.lint()
    assert any("words" in p for p in problems)
    assert any("preamble" in p for p in problems)
    assert any("end on a question" in p for p in problems)


def test_system_prompt_encodes_research_contract():
    assert "120-140 words" in story.SCRIPT_SYSTEM
    assert "END ON ENGAGEMENT" in story.SCRIPT_SYSTEM
    assert "Never a moral" in story.SCRIPT_SYSTEM


def test_length_targets_and_long_prompt():
    assert story.LENGTHS["short"][:2] == (120, 140)
    lo, hi, _ = story.LENGTHS["long"]
    assert lo >= 170  # clears TikTok's 60 s Creator Rewards floor at ~160 wpm
    long_prompt = story.script_system("long")
    assert f"{lo}-{hi} words" in long_prompt and "third escalation" in long_prompt
    assert "verdict" in story.SCRIPT_SYSTEM
    with pytest.raises(ValueError):
        story.script_system("epic")


def test_lint_uses_requested_length():
    long_text = (
        "My boss fired me by text. " + "I kept every receipt he sent. " * 28 + "So. Was I wrong?"
    )
    s = story.Script(title="t", style="AITA", hook="h", narration=long_text, hashtags=["a"])
    assert 170 <= s.word_count <= 210
    assert s.lint("long") == []
    assert any("words" in p for p in s.lint("short"))


def test_verdict_is_optional_for_old_scripts():
    s = story.Script(title="t", style="AITA", hook="h", narration=GOOD, hashtags=["a"])
    assert s.verdict == ""
    v = story.Script(title="t", style="AITA", hook="h", narration=GOOD, hashtags=["a"],
                     verdict="Ask him. Planners like that are keepers.")
    assert "keepers" in v.model_dump()["verdict"]
