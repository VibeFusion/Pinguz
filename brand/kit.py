"""Jury's In brand kit renders: post-card covers, banner, verdict stamps."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

F = Path("fonts")
ANTON = str(F / "Anton-Regular.ttf")
MONT = str(F / "Montserrat[wght].ttf")
YEL = (255, 214, 10)      # verdict yellow
INK = (11, 11, 15)        # court black
RED = (229, 38, 31)       # WRONG
GRN = (52, 199, 89)       # RIGHT
PAPER = (255, 255, 255)
GREY = (120, 126, 140)
NAVY = (15, 18, 28)


def mont(size, w=800):
    f = ImageFont.truetype(MONT, size)
    try:
        f.set_variation_by_axes([w])
    except Exception:
        pass
    return f


def stage(w, h):
    """Dark stage with a soft yellow glow: the card is the subject, not the backdrop."""
    img = Image.new("RGB", (w, h), NAVY)
    glow = Image.new("RGB", (w, h), NAVY)
    g = ImageDraw.Draw(glow)
    r = int(min(w, h) * 0.55)
    cx, cy = w // 2, int(h * 0.42)
    g.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(84, 66, 0))
    glow = glow.filter(ImageFilter.GaussianBlur(int(r * 0.6)))
    return Image.blend(img, glow, 0.9)


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    return lines


def arrow(d, x, y, s, fill, up=True):
    if up:
        d.polygon([(x, y + s * .55), (x + s / 2, y), (x + s, y + s * .55),
                   (x + s * .68, y + s * .55), (x + s * .68, y + s), (x + s * .32, y + s),
                   (x + s * .32, y + s * .55)], fill=fill)
    else:
        d.polygon([(x, y + s * .45), (x + s / 2, y + s), (x + s, y + s * .45),
                   (x + s * .68, y + s * .45), (x + s * .68, y), (x + s * .32, y),
                   (x + s * .32, y + s * .45)], fill=fill)


def bubble(d, x, y, s, fill):
    d.rounded_rectangle((x, y, x + s, y + s * .78), radius=s * .22, fill=fill)
    d.polygon([(x + s * .22, y + s * .7), (x + s * .18, y + s), (x + s * .48, y + s * .76)], fill=fill)


def post_card(img, x, y, w, title, sub, votes, comments, avatar=None, scale=1.0):
    d = ImageDraw.Draw(img)
    pad = int(44 * scale)
    tf = mont(int(66 * scale), 800)
    lines = wrap(d, title, tf, w - 2 * pad)
    lh = int(78 * scale)
    h = pad + int(96 * scale) + len(lines) * lh + int(120 * scale)
    # shadow + card
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x + 8, y + 26, x + w + 8, y + h + 26),
                                         radius=int(32 * scale), fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    img.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x, y, x + w, y + h), radius=int(32 * scale), fill=PAPER)
    # header: avatar, handle, meta
    ar = int(36 * scale)
    ax, ay = x + pad, y + pad
    if avatar is not None:
        av = avatar.resize((2 * ar, 2 * ar))
        mask = Image.new("L", av.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * ar, 2 * ar), fill=255)
        img.paste(av, (ax, ay), mask)
    else:
        d.ellipse((ax, ay, ax + 2 * ar, ay + 2 * ar), fill=YEL)
        d.text((ax + ar, ay + ar), "J", font=ImageFont.truetype(ANTON, int(44 * scale)), fill=INK, anchor="mm")
    d = ImageDraw.Draw(img)
    d.text((ax + 2 * ar + int(18 * scale), ay + int(2 * scale)), "u/jurysin", font=mont(int(34 * scale), 700), fill=INK)
    d.text((ax + 2 * ar + int(18 * scale), ay + int(42 * scale)), sub, font=mont(int(28 * scale), 500), fill=GREY)
    # title
    ty = y + pad + int(96 * scale)
    for ln in lines:
        d.text((x + pad, ty), ln, font=tf, fill=INK)
        ty += lh
    # footer: votes, comments
    fy = ty + int(28 * scale)
    s = int(40 * scale)
    pill = mont(int(30 * scale), 700)
    d.rounded_rectangle((x + pad, fy, x + pad + int(300 * scale), fy + int(64 * scale)),
                        radius=int(32 * scale), fill=(240, 242, 246))
    arrow(d, x + pad + int(16 * scale), fy + int(12 * scale), s, RED, up=True)
    d.text((x + pad + int(70 * scale), fy + int(16 * scale)), votes, font=pill, fill=INK)
    arrow(d, x + pad + int(216 * scale), fy + int(12 * scale), s, GREY, up=False)
    bx = x + pad + int(330 * scale)
    d.rounded_rectangle((bx, fy, bx + int(230 * scale), fy + int(64 * scale)),
                        radius=int(32 * scale), fill=(240, 242, 246))
    bubble(d, bx + int(18 * scale), fy + int(12 * scale), s, GREY)
    d.text((bx + int(74 * scale), fy + int(16 * scale)), comments, font=pill, fill=INK)
    return h


def wordmark(d, cx, y, size):
    f = mont(size, 900)
    t = "JURY'S IN"
    tw = d.textlength(t, font=f)
    pad = size * .5
    d.rounded_rectangle((cx - tw / 2 - pad, y, cx + tw / 2 + pad, y + size * 1.55), radius=size * .3, fill=YEL)
    d.text((cx, y + size * .28), t, font=f, fill=INK, anchor="ma")


def outlined(d, xy, text, font, fill, width=8, anchor="ma"):
    x, y = xy
    for dx in range(-width, width + 1, 2):
        for dy in range(-width, width + 1, 2):
            if dx * dx + dy * dy <= width * width:
                d.text((x + dx, y + dy), text, font=font, fill=INK, anchor=anchor)
    d.text((x, y), text, font=font, fill=fill, anchor=anchor)


TITLE = "My roommate secretly paid my rent for six months. Then I found the note he left next to “spring”."


def cover_916(path, avatar=None):
    w, h = 1080, 1920
    img = stage(w, h)
    d = ImageDraw.Draw(img)
    wordmark(d, w / 2, 120, 40)
    ch = post_card(img, 70, 330, 940, TITLE, "r/confession • 6h", "48.2K", "3,913", avatar)
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(ANTON, 176)
    outlined(d, (w / 2, 330 + ch + 90), "DO I ASK HIM", big, PAPER, width=10)
    outlined(d, (w / 2, 330 + ch + 90 + 176), "TO STAY?", big, YEL, width=10)
    d.text((w / 2, h - 170), "YOU DECIDE. COMMENT WRONG OR RIGHT.", font=mont(34, 800), fill=(255, 255, 255), anchor="ma")
    img.save(path, quality=95)


def cover_169(path, avatar=None):
    w, h = 1280, 720
    img = stage(w, h)
    d = ImageDraw.Draw(img)
    post_card(img, 60, 100, 640, TITLE, "r/confession • 6h", "48.2K", "3,913", avatar, scale=0.62)
    d = ImageDraw.Draw(img)
    wordmark(d, 1000, 60, 28)
    big = ImageFont.truetype(ANTON, 132)
    outlined(d, (1000, 200), "DO I ASK", big, PAPER, width=8)
    outlined(d, (1000, 332), "HIM TO", big, PAPER, width=8)
    outlined(d, (1000, 464), "STAY?", big, YEL, width=8)
    img.save(path, quality=95)


def banner(path, avatar=None):
    # YouTube channel art 2560x1440; safe area 1546x423 centred.
    w, h = 2560, 1440
    img = stage(w, h)
    d = ImageDraw.Draw(img)
    sx, sy = (w - 1546) // 2, (h - 423) // 2
    big = ImageFont.truetype(ANTON, 190)
    outlined(d, (sx + 20, sy + 20), "JURY'S IN", big, YEL, width=10, anchor="la")
    d.text((sx + 26, sy + 230), "Stories that end before the answer.", font=mont(56, 800), fill=PAPER)
    d.text((sx + 26, sy + 300), "You're the jury. New verdicts daily.", font=mont(44, 600), fill=(200, 204, 214))
    # verdict stamps as the banner's identity device
    stamp(img, sx + 1180, sy + 40, "WRONG", RED, rot=-8)
    stamp(img, sx + 1230, sy + 220, "RIGHT", GRN, rot=6)
    img.save(path, quality=95)


def stamp(img, x, y, text, color, rot=0, scale=1.0):
    f = ImageFont.truetype(ANTON, int(96 * scale))
    tmp = Image.new("RGBA", (int(420 * scale), int(160 * scale)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.rounded_rectangle((6, 6, tmp.width - 6, tmp.height - 6), radius=int(18 * scale),
                        outline=color, width=int(10 * scale))
    d.text((tmp.width / 2, tmp.height / 2), text, font=f, fill=color, anchor="mm")
    tmp = tmp.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.paste(tmp, (x, y), tmp)


def stamps(path):
    img = Image.new("RGB", (1000, 260), PAPER)
    stamp(img, 40, 40, "WRONG", RED, rot=-6)
    stamp(img, 540, 40, "RIGHT", GRN, rot=5)
    img.save(path)


if __name__ == "__main__":
    out = Path("kit"); out.mkdir(exist_ok=True)
    cover_916(out / "cover_card_9x16.jpg")
    cover_169(out / "thumb_card_16x9.jpg")
    banner(out / "banner_2560x1440.jpg")
    stamps(out / "verdict_stamps.png")
    print("ok")
