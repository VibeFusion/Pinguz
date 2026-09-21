"""Tests for word-timed ASS caption generation."""

from __future__ import annotations

from factory import captions
from factory.tts import Word


def test_format_time_centiseconds():
    assert captions.format_time(0) == "0:00:00.00"
    assert captions.format_time(1.234) == "0:00:01.23"
    assert captions.format_time(61.5) == "0:01:01.50"
    assert captions.format_time(3600 + 2) == "1:00:02.00"
    assert captions.format_time(-1) == "0:00:00.00"


def test_group_words_extends_to_next_start_and_holds_tail():
    words = [Word("a", 0.0, 0.2), Word("b", 0.5, 0.7), Word("c", 0.9, 1.0)]
    cards = captions.group_words(words, 1)
    assert cards[0] == (0.0, 0.5, "a")  # extended to next start (no gap)
    assert cards[1] == (0.5, 0.9, "b")
    assert cards[2][0] == 0.9 and cards[2][1] > 1.0  # tail hold
    assert cards[2][2] == "c"


def test_group_words_per_card_two():
    words = [Word(t, i * 1.0, i * 1.0 + 0.5) for i, t in enumerate("one two three".split())]
    cards = captions.group_words(words, 2)
    assert [c[2] for c in cards] == ["one two", "three"]
    assert cards[0][0] == 0.0 and cards[1][0] == 2.0


def test_to_ass_structure_and_escaping():
    words = [Word("hi{there}", 0.0, 0.4), Word("ok", 0.4, 0.8)]
    ass = captions.to_ass(words, uppercase=True, width=720, height=1280)
    assert "PlayResX: 720" in ass and "PlayResY: 1280" in ass
    assert "Style: Word,Arial,110" in ass
    lines = [ln for ln in ass.splitlines() if ln.startswith("Dialogue:")]
    assert len(lines) == 2
    assert lines[0].endswith(",HI(THERE)")  # braces neutralised, uppercase applied
    assert lines[0].startswith("Dialogue: 0,0:00:00.00,0:00:00.40,Word")
