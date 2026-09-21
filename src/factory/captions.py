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
# Hook card: smaller, boxed (BorderStyle 3), top-centre (alignment 8), inside the
# safe area — MarginV keeps it out of the top 10% that platform UI covers.
_HOOK_STYLE_VALUES = (
    "Hook,{font},{hook_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HA0000000,"
    "-1,0,0,0,100,100,0,0,3,14,0,8,80,80,{hook_margin},1"
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
    f"Style: {_HOOK_STYLE_VALUES}\n"
    "\n"
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)

# Hold the last card on screen briefly rather than cutting to nothing.
_TAIL_HOLD = 0.3
# ASS colours are &HBBGGRR&
HIGHLIGHT_YELLOW = "&H00FFFF&"


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


def karaoke_lines(words: list[Word], per_card: int, *, uppercase: bool = False) -> list[str]:
    """One Dialogue per spoken word; the card stays up, the current word is highlighted.

    This is the "word pop" / karaoke style standard on story channels: 3-5 word
    pages so the eye has context, colour on the word being spoken so it tracks
    the audio.
    """
    out: list[str] = []
    for i in range(0, len(words), per_card):
        chunk = words[i : i + per_card]
        next_start = words[i + per_card].start if i + per_card < len(words) else None
        for j, w in enumerate(chunk):
            start = w.start
            if j + 1 < len(chunk):
                end = max(w.end, chunk[j + 1].start)
            elif next_start is not None:
                end = max(w.end, next_start)
            else:
                end = w.end + _TAIL_HOLD
            parts = []
            for k, ww in enumerate(chunk):
                txt = _escape(ww.text.upper() if uppercase else ww.text)
                parts.append(f"{{\\1c{HIGHLIGHT_YELLOW}}}{txt}{{\\r}}" if k == j else txt)
            text = " ".join(parts)
            out.append(
                f"Dialogue: 0,{format_time(start)},{format_time(end)},Word,,0,0,0,,{text}\n"
            )
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
    highlight: bool = False,
    hook: str | None = None,
    hook_seconds: float = 3.0,
) -> str:
    """Render word timings as a complete ASS subtitle document.

    highlight=True keeps a whole card on screen and colours the spoken word.
    hook=... shows a boxed title card in the upper third for the first
    `hook_seconds`, so the video reads even when muted.
    """
    header = _HEADER.format(
        width=width, height=height, font=font, size=size, outline=outline, shadow=shadow,
        hook_size=max(int(size * 0.5), 40), hook_margin=int(height * 0.14),
    )
    lines = [header]
    if hook:
        lines.append(
            f"Dialogue: 1,{format_time(0)},{format_time(hook_seconds)},Hook,,0,0,0,,"
            f"{_escape(hook.strip())}\n"
        )
    if highlight:
        lines.extend(karaoke_lines(words, per_card, uppercase=uppercase))
        return "".join(lines)
    for start, end, text in group_words(words, per_card):
        if uppercase:
            text = text.upper()
        lines.append(
            f"Dialogue: 0,{format_time(start)},{format_time(end)},Word,,0,0,0,,{_escape(text)}\n"
        )
    return "".join(lines)
