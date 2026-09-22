import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, "/home/user/Pinguz/src")
from factory import procedural

F = Path("fonts")
ANTON = str(F / "Anton-Regular.ttf")
BEBAS = str(F / "BebasNeue-Regular.ttf")
MONT = str(F / "Montserrat[wght].ttf")
YELLOW = (245, 196, 0)
INK = (20, 24, 32)


def mont(size, wght=800):
    f = ImageFont.truetype(MONT, size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def background(w, h, seed=7, frame=75, kind="flow"):
    gen = getattr(procedural, kind)(seconds=frame / 30 + 0.1, seed=seed, width=w, height=h, fps=30)
    fr = None
    for i, fr in enumerate(gen):
        if i >= frame:
            break
    img = Image.fromarray(fr).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(2))
    # darken with a vertical gradient so text wins
    grad = Image.new("L", (1, h))
    for y in range(h):
        t = y / h
        v = int(255 * (0.72 - 0.30 * abs(t - 0.5) * 2))  # darkest in the middle band
        grad.putpixel((0, y), max(0, min(255, v)))
    grad = grad.resize((w, h))
    dark = Image.new("RGB", (w, h), INK)
    return Image.composite(dark, img, grad)


def outlined(draw, xy, text, font, fill, outline=(0, 0, 0), width=8, anchor="la"):
    x, y = xy
    for dx in range(-width, width + 1, 2):
        for dy in range(-width, width + 1, 2):
            if dx * dx + dy * dy <= width * width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def wordmark(draw, cx, y, size=44):
    f = mont(size, 900)
    t = "JURY'S IN"
    tw = draw.textlength(t, font=f)
    pad = 22
    box = (cx - tw / 2 - pad, y, cx + tw / 2 + pad, y + size + 26)
    draw.rounded_rectangle(box, radius=14, fill=YELLOW)
    draw.text((cx, y + 13), t, font=f, fill=INK, anchor="ma")


def lines_block(draw, lines, cx, top, font, gap, colors, outline_w):
    y = top
    for text, color in zip(lines, colors):
        outlined(draw, (cx, y), text, font, color, width=outline_w, anchor="ma")
        y += font.size + gap
    return y


def cover_916(path):
    w, h = 1080, 1920
    img = background(w, h)
    d = ImageDraw.Draw(img)
    wordmark(d, w / 2, 150)
    big = ImageFont.truetype(ANTON, 168)
    lines = ["MY ROOMMATE", "SECRETLY PAID", "MY RENT", "FOR 6 MONTHS"]
    colors = ["white", "white", "white", YELLOW]
    total = len(lines) * (168 + 6)
    top = (h - total) / 2 - 40
    y = lines_block(d, lines, w / 2, top, big, 6, colors, 10)
    sub = mont(50, 700)
    outlined(d, (w / 2, y + 40), "He went pale. Then he pulled up", sub, "white", width=6, anchor="ma")
    outlined(d, (w / 2, y + 104), "a spreadsheet.", sub, "white", width=6, anchor="ma")
    tag = ImageFont.truetype(BEBAS, 64)
    outlined(d, (w / 2, h - 300), "SO. DO I ASK HIM TO STAY?", tag, YELLOW, width=6, anchor="ma")
    img.save(path, quality=95)


def cover_169(path):
    w, h = 1280, 720
    img = background(w, h, seed=7, frame=75)
    d = ImageDraw.Draw(img)
    wordmark(d, 190, 40, size=30)
    big = ImageFont.truetype(ANTON, 118)
    lines = ["MY ROOMMATE SECRETLY", "PAID MY RENT", "FOR 6 MONTHS"]
    colors = ["white", "white", YELLOW]
    y = 165
    for t, c in zip(lines, colors):
        outlined(d, (60, y), t, big, c, width=8, anchor="la")
        y += 124
    tag = ImageFont.truetype(BEBAS, 54)
    outlined(d, (60, h - 110), "SO. DO I ASK HIM TO STAY?", tag, YELLOW, width=5, anchor="la")
    img.save(path, quality=95)


def cover_11(path):
    w, h = 1080, 1080
    img = background(w, h, seed=7, frame=75)
    d = ImageDraw.Draw(img)
    wordmark(d, w / 2, 70, size=38)
    big = ImageFont.truetype(ANTON, 150)
    lines = ["MY ROOMMATE", "SECRETLY PAID", "MY RENT", "FOR 6 MONTHS"]
    colors = ["white", "white", "white", YELLOW]
    lines_block(d, lines, w / 2, 250, big, 4, colors, 9)
    img.save(path, quality=95)


def icon_fallback(path):
    # Owned vector-style fallback in case the AI icon needs replacing: yellow disc, ink gavel.
    s = 1024
    img = Image.new("RGB", (s, s), INK)
    d = ImageDraw.Draw(img)
    d.ellipse((72, 72, s - 72, s - 72), fill=YELLOW)
    f = ImageFont.truetype(ANTON, 300)
    d.text((s / 2, s / 2 - 40), "JI", font=f, fill=INK, anchor="mm")
    d.rounded_rectangle((s / 2 - 210, s / 2 + 160, s / 2 + 210, s / 2 + 200), radius=20, fill=INK)
    img.save(path)


out = Path("out"); out.mkdir(exist_ok=True)
cover_916(out / "cover_9x16.jpg")
cover_169(out / "thumb_16x9.jpg")
cover_11(out / "cover_1x1.jpg")
icon_fallback(out / "icon_fallback.png")
print("ok", [p.name for p in out.iterdir()])
