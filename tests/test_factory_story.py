"""Tests for the script contract (no network — the model call is not exercised)."""

from __future__ import annotations

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
