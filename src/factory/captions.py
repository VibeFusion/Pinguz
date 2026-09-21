"""Word-timed captions → ASS subtitles (word-by-word, centered, bold outline)."""

from __future__ import annotations

from .tts import Word

_STYLE_FIELDS = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
    "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)
# Bold white text, black outline, translucent shadow, alignment 5 = dead centre.
_STYLE_VALUES = (
    "Word,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
    "-1,0,0,0,100,100,0,0,1,{outline},{shadow},5,60,60,0,1"
)
_HEADER = (
    "[Script Info]\n"
    "ScriptType: v4.00+\n"
    "PlayResX: {width}\n"
    "PlayResY: {height}\n"
    "WrapStyle: 0\n"
    "ScaledBorderAndShadow: yes\n"
    "\n"
    "[V4+ Styles]\n"
    f"Format: {_STYLE_FIELDS}\n"
    f"Style: {_STYLE_VALUES}\n"
    "\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)

# Hold the last card on screen briefly rather than cutting to nothing.
_TAIL_HOLD = 0.3


def format_time(seconds: float) -> str:
    """Format seconds as ASS h:mm:ss.cc (centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    total_cs = round(seconds * 100)
    h, rem = divmod(total_cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escape(text: str) -> str:
    # Braces open override blocks in ASS; backslash starts escapes.
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def group_words(words: list[Word], per_card: int) -> list[tuple[float, float, str]]:
    """Group words into (start, end, text) cards.

    Each card ends where the next begins so there is never a blank frame
    between words; the final card holds for a short tail.
    """
    if per_card < 1:
        raise ValueError("per_card must be >= 1")
    cards: list[tuple[float, float, str]] = []
    for i in range(0, len(words), per_card):
        chunk = words[i : i + per_card]
        cards.append((chunk[0].start, chunk[-1].end, " ".join(w.text for w in chunk)))
    out: list[tuple[float, float, str]] = []
    for i, (start, end, text) in enumerate(cards):
        if i + 1 < len(cards):
            end = max(end, cards[i + 1][0])
        else:
            end = end + _TAIL_HOLD
        out.append((start, end, text))
    return out


def to_ass(
    words: list[Word],
    *,
    per_card: int = 1,
    width: int = 1080,
    height: int = 1920,
    font: str = "Arial",
    size: int = 110,
    outline: int = 8,
    shadow: int = 3,
    uppercase: bool = False,
) -> str:
    """Render word timings as a complete ASS subtitle document."""
    header = _HEADER.format(
        width=width, height=height, font=font, size=size, outline=outline, shadow=shadow
    )
    lines = [header]
    for start, end, text in group_words(words, per_card):
        if uppercase:
            text = text.upper()
        lines.append(
            f"Dialogue: 0,{format_time(start)},{format_time(end)},Word,,0,0,0,,{_escape(text)}\n"
        )
    return "".join(lines)
