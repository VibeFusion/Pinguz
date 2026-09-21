"""`factory` CLI — bank / ideas / script / make."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from . import assemble, captions, prompts, timeline, tts
from . import bank as bankmod

DEFAULT_BANK = Path("bank")


# ── bank ─────────────────────────────────────────────────────────────────────


def cmd_bank(args: argparse.Namespace) -> int:
    cats = args.categories.split(",") if args.categories else None
    try:
        plist = prompts.all_prompts(cats, per_category=args.per_category)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    bank = bankmod.Bank(args.dir)

    if args.dry_run:
        print(f"{len(plist)} prompts → {args.dir} (model={args.model}, {args.duration}s each)")
        for cp in plist:
            print(f"  [{cp.category}] {cp.text}")
        return 0

    print(f"▶ Generating {len(plist)} clips into {args.dir} (concurrency={args.concurrency})")

    def on_done(cp: prompts.ClipPrompt, clip: bankmod.Clip | None, exc: Exception | None) -> None:
        if clip:
            print(f"  ✓ [{cp.category}] {clip.path.name} ({clip.duration:.1f}s)")
        else:
            print(f"  ✗ [{cp.category}] {exc}")

    done, failed = asyncio.run(
        bankmod.generate(
            bank,
            plist,
            model=args.model,
            duration=args.duration,
            quality=args.quality,
            concurrency=args.concurrency,
            on_done=on_done,
        )
    )
    print(f"\n{len(done)} ok, {len(failed)} failed. Bank now: {bank.categories()}")
    return 1 if failed and not done else 0


def cmd_bank_list(args: argparse.Namespace) -> int:
    bank = bankmod.Bank(args.dir)
    clips = bank.clips()
    if not clips:
        print(f"Bank {args.dir} is empty — run `factory bank`")
        return 1
    for cat, n in bank.categories().items():
        print(f"{cat}: {n}")
    total = sum(c.duration for c in clips)
    print(f"\n{len(clips)} clips, {total:.0f}s of footage")
    return 0


# ── ideas / script ───────────────────────────────────────────────────────────


def cmd_ideas(args: argparse.Namespace) -> int:
    from . import story

    try:
        ideas = story.generate_ideas(args.niche, args.n)
    except story.ScriptError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for i, idea in enumerate(ideas, 1):
        print(f"{i:2d}. [{idea.style}] {idea.premise}\n      → {idea.why_it_hooks}")
    if args.out:
        story.save_ideas(ideas, args.out)
        print(f"\nSaved {len(ideas)} ideas → {args.out}")
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    from . import story

    idea = args.idea if args.idea else sys.stdin.read()
    try:
        script = story.write_script(idea, style=args.style)
    except story.ScriptError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"# {script.title}  [{script.style}]  ({script.word_count} words)\n")
    print(script.narration)
    print("\n" + " ".join(f"#{h}" for h in script.hashtags))
    if args.out:
        script.save(args.out)
        print(f"\nSaved → {args.out}")
    return 0


# ── make ─────────────────────────────────────────────────────────────────────


def cmd_make(args: argparse.Namespace) -> int:
    from . import story

    if args.script:
        script = story.Script.load(args.script)
        text = script.narration
        meta: dict = script.model_dump()
    elif args.text:
        text = args.text
        meta = {"narration": text}
    else:
        print("error: pass --script FILE or --text 'narration'", file=sys.stderr)
        return 2

    out = Path(args.out)
    workdir = Path(args.workdir) if args.workdir else out.with_suffix(".work")
    workdir.mkdir(parents=True, exist_ok=True)

    bank = bankmod.Bank(args.bank)
    cats = args.categories.split(",") if args.categories else None
    clips = bank.clips(cats)
    if not clips:
        print(f"error: no clips in {args.bank} — run `factory bank` first", file=sys.stderr)
        return 1

    print(f"▶ Voice ({args.tts}) …")
    try:
        provider = tts.get_provider(args.tts, voice_id=args.voice) if args.tts == "elevenlabs" \
            else tts.get_provider(args.tts)
        speech = provider.synthesize(text, workdir / "voice")
    except tts.TTSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"  {len(speech.words)} words, {speech.duration:.1f}s")

    segments = timeline.plan(
        clips, speech.duration, min_cut=args.min_cut, max_cut=args.max_cut, seed=args.seed
    )
    print(f"▶ Timeline: {len(segments)} cuts from {len({s.clip.id for s in segments})} clips")

    ass_path = workdir / "captions.ass"
    ass_path.write_text(
        captions.to_ass(speech.words, per_card=args.words_per_card, uppercase=args.uppercase)
    )

    print("▶ Rendering …")
    try:
        assemble.render(segments, speech.audio_path, ass_path, out)
    except assemble.RenderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    meta["segments"] = [
        {"clip": s.clip.id, "category": s.clip.category, "start": s.start, "duration": s.duration}
        for s in segments
    ]
    meta["duration"] = speech.duration
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(f"✓ {out}  ({speech.duration:.1f}s)  metadata → {out.with_suffix('.json')}")
    return 0


# ── parser ───────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="factory", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bank", help="generate background clips into the bank")
    b.add_argument("--dir", type=Path, default=DEFAULT_BANK)
    b.add_argument("--categories", help="comma-separated subset of categories")
    b.add_argument("--per-category", type=int, default=None, help="prompts per category")
    b.add_argument("--model", default="seedance-v2.0-t2v")
    b.add_argument("--duration", type=int, default=10)
    b.add_argument("--quality", default="basic", choices=["basic", "high"])
    b.add_argument("--concurrency", type=int, default=4)
    b.add_argument("--dry-run", action="store_true", help="print prompts, don't generate")
    b.set_defaults(func=cmd_bank)

    bl = sub.add_parser("bank-list", help="show what's in the bank")
    bl.add_argument("--dir", type=Path, default=DEFAULT_BANK)
    bl.set_defaults(func=cmd_bank_list)

    i = sub.add_parser("ideas", help="generate story premises for a niche")
    i.add_argument("niche")
    i.add_argument("-n", type=int, default=10)
    i.add_argument("--out", type=Path)
    i.set_defaults(func=cmd_ideas)

    s = sub.add_parser("script", help="turn a premise into a script (reads stdin if omitted)")
    s.add_argument("idea", nargs="?")
    s.add_argument("--style", choices=None, help="e.g. AITA, TIFU, 'petty revenge'")
    s.add_argument("--out", type=Path)
    s.set_defaults(func=cmd_script)

    m = sub.add_parser("make", help="render a short from a script")
    m.add_argument("--script", type=Path, help="script JSON from `factory script --out`")
    m.add_argument("--text", help="raw narration instead of a script file")
    m.add_argument("--out", default="out/short.mp4")
    m.add_argument("--workdir", help="where voice/captions go (default: <out>.work)")
    m.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    m.add_argument("--categories", help="restrict backgrounds to these categories")
    m.add_argument("--tts", default="elevenlabs", choices=sorted(tts.PROVIDERS))
    m.add_argument("--voice", help="ElevenLabs voice id (default: $ELEVENLABS_VOICE_ID)")
    m.add_argument("--words-per-card", type=int, default=1)
    m.add_argument("--uppercase", action="store_true")
    m.add_argument("--min-cut", type=float, default=2.0)
    m.add_argument("--max-cut", type=float, default=4.0)
    m.add_argument("--seed", type=int)
    m.set_defaults(func=cmd_make)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
