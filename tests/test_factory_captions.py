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


def test_karaoke_highlights_current_word_and_keeps_card():
    words = [
        Word("one", 0.0, 0.3),
        Word("two", 0.4, 0.7),
        Word("three", 0.8, 1.1),
        Word("four", 1.2, 1.5),
    ]
    lines = captions.karaoke_lines(words, per_card=3)
    assert len(lines) == 4  # one Dialogue per spoken word
    assert lines[0].endswith(",{\\1c&H00FFFF&}one{\\r} two three\n")
    assert lines[1].endswith(",one {\\1c&H00FFFF&}two{\\r} three\n")
    assert lines[3].endswith(",{\\1c&H00FFFF&}four{\\r}\n")
    # card 1 word 3 ends where card 2 begins, no gap
    assert "0:00:00.80,0:00:01.20" in lines[2]


def test_hook_card_and_highlight_in_to_ass():
    words = [Word("hi", 0.0, 0.4)]
    ass = captions.to_ass(words, hook="Big {title}", hook_seconds=2.5, highlight=True)
    assert "Style: Hook," in ass
    assert "Dialogue: 1,0:00:00.00,0:00:02.50,Hook,,0,0,0,,Big (title)" in ass
    assert "{\\1c&H00FFFF&}hi{\\r}" in ass


def test_hook_card_boxless_style():
    ass = captions.to_ass([Word("hi", 0.0, 0.4)], hook="T", hook_box=False)
    style = next(ln for ln in ass.splitlines() if ln.startswith("Style: Hook,"))
    assert ",1,6,0,8,80,80," in style  # BorderStyle 1, outline 6
    boxed = captions.to_ass([Word("hi", 0.0, 0.4)], hook="T")
    boxed_style = next(ln for ln in boxed.splitlines() if ln.startswith("Style: Hook,"))
    assert ",3,14,0,8,80,80," in boxed_style


def test_outro_verdict_card_after_narration():
    words = [Word("hi", 0.0, 0.4), Word("there", 0.4, 0.8)]
    ass = captions.to_ass(words, hook="T", outro="MY TAKE: ask him", outro_start=0.8,
                          outro_seconds=2.5, highlight=True)
    assert "Dialogue: 1,0:00:00.80,0:00:03.30,Hook,,0,0,0,,MY TAKE: ask him" in ass
    assert ass.count("Hook,,0,0,0,,") == 2  # title card + verdict card
