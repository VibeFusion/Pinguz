# Channel brief — tech tips (short + long form)

Draft, 2026-10-03. A second channel next to Jury's In. Nothing in `src/factory/`
supports this yet; section 6 lists the code changes it needs.

## 1. Positioning

**Niche:** everyday-device tips for people who aren't "tech people": the phone,
laptop and free apps they already have. It's narrow enough to own and broad enough
to keep a daily output going.

**Promise:** "One thing your device already does that you didn't know about."

**Name ideas** (check handles before committing):
- **Hidden Setting**: the format in two words; the thumbnails write themselves ("HIDDEN SETTING #47").
- **Tap Twice**: short, verb-led, sounds like an instruction.
- **Already Free**: leans into "stop paying for X" videos, which do well.

Recommended: **Hidden Setting**. The numbering builds a collectible series, and the
name still fits long-form ("10 Hidden Settings in iOS 26").

## 2. Formats

| | Short | Long |
|---|---|---|
| Aspect | 9:16, 1080×1920 | 16:9, 1920×1080 |
| Length | 25–40 s (70–110 words) | 8–12 min (1,300–1,900 words) |
| Cadence | 1/day | 1/week |
| Picture | Screen recording of the device, zoomed + arrow callouts | Screen recording + chapter cards + face-free B-roll between sections |
| Voice | Adam (ElevenLabs), same as Jury's In | Same voice, slower read (stability up) |
| Captions | Word-by-word karaoke | Sentence captions + YouTube chapters |
| Job | Discovery, subscribers | Watch time, AdSense (long-form RPM is several × Shorts) |

The two feed each other: every long video is built from 8–12 tips that each
ran as a Short first. The Shorts that performed best become the long video's
list, and each of those Shorts' pinned comments links to the full video.

### Short structure (≈30 s)
1. **0–2 s: result first.** Show the end state on screen and say what it does. No "hey guys", no "did you know".
2. **2–20 s: steps.** 2–4 steps, one per cut, zoom on each tap target.
3. **20–27 s: bonus or warning.** "Bonus: hold it down and…", or "Turn this off if…". This beat is the reason to watch to the end.
4. **27–30 s: verdict line + CTA.** "Hidden setting #12. Follow for #13 tomorrow."

### Long structure (≈10 min)
1. **0–30 s: cold open.** The most impressive tip of the list, shown fully.
2. **30–45 s: the setup.** What the list is, what device/OS version, no intro sequence.
3. **Tips in rising order.** Weakest first-half tip early, strongest saved for last, a "pattern break" every ~2 min (a myth bust, a "this one's dangerous" warning).
4. **Last 30 s: payoff + end screen.** Point to the matching Short playlist.

## 3. Rules (non-negotiable)

- **Every tip is filmed on a real device.** The script agent drafts, but a human
  runs the steps and records them. A wrong menu path kills trust, and the
  comments will catch it within the hour.
- **State the OS version on screen.** "iOS 26", "Android 16 / Pixel", "Windows 11 24H2".
- **No AI B-roll pretending to be a UI.** AI clips are fine only as section
  breaks in long-form, never as the demonstration.
- **AI-voice disclosure** in the description, same wording style as Jury's In.
  Screen recordings + original scripts + a real host perspective (the closing line)
  keep this clear of YouTube's 2025 inauthentic/mass-produced content policy.
- **No piracy, account-sharing or ToS-breaking "hacks".** They get demonetised
  and they attract the wrong audience.

## 4. First 20 Short premises

1. iPhone: the hidden ruler and spirit level in the Measure app
2. iPhone: back tap — double-tap the back of the phone to take a screenshot
3. iPhone: turn any photo into a sticker by long-pressing the subject
4. iPhone: swipe left on the calculator display to delete one digit
5. iPhone: make the flashlight brighter/dimmer from Control Center
6. Android: pin an app to the screen so a kid can't leave it
7. Android: Circle to Search on anything on screen
8. Android: tap the build number 7 times — what developer options are actually useful
9. Windows: Win + V clipboard history
10. Windows: Win + Shift + S, then the text extractor in Snipping Tool
11. Windows: shake a window to minimise every other window (and how to turn it back on)
12. Mac: hold Option while clicking the Wi-Fi icon
13. Mac: Cmd + Shift + 5 screen recording with no app
14. Chrome: reopen a closed tab with Ctrl/Cmd + Shift + T — and the whole window
15. Gmail: undo send and how to make the window 30 s
16. Google Maps: share a live location that expires
17. YouTube: press numbers 1–9 to jump to 10–90 % of a video
18. Wi-Fi: show a saved Wi-Fi password as a QR code (Android + iPhone)
19. Free app that replaces a paid one: e.g. a free PDF editor already in the OS
20. "Stop doing this": closing apps on iPhone doesn't save battery

## 5. First 3 long-form premises

1. **"15 iPhone settings to change right now"**: built from Shorts 1–5 plus 10 new ones.
2. **"Windows shortcuts that feel illegal"**: Shorts 9–11, 14 and more.
3. **"Free tools that replace apps you're paying for"**: one per category, with a cost total at the end.

## 6. Finished Short script (#1)

> Your iPhone has a ruler, and a spirit level, and you've never opened them.
> Open the Measure app. Point it at anything and tap plus at each end —
> that's the length, in centimetres or inches.
> Now swipe up and tap Level. Lay the phone on a shelf and it goes green when it's straight.
> Bonus: on a Pro model it can measure how tall someone is. Just point it at them.
> Hidden setting number one. Follow, number two drops tomorrow.

78 words, ≈28 s. Shot list: Measure icon → measuring a book → Level tab → phone
on shelf turning green → height measurement on a door frame (no faces).

## 7. What the factory needs for this

1. **`--broll` input**: render over a user-supplied screen recording instead of the clip bank (crop/scale to 9:16 or 16:9).
2. **Callouts**: timed zoom-ins and arrow overlays from a small JSON (`[{t, x, y, zoom}]`).
3. **`tech tip` script style** in `story.py` with its own system prompt and lint (no preamble, OS version named, ≤ 4 steps).
4. **Length presets**: `tip-short` (70–110 words) and `tip-long` (1,300–1,900 words, with chapter markers emitted as YouTube timestamps).
5. **16:9 render path** in `assemble.py` for long-form (currently 9:16 only).
