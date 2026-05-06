# ATLAS Brand — Higgsfield Production Guide

> Premium outdoor adventure gear brand. Color language: matte charcoal + slate grey. Aesthetic: mountain / wilderness / technical performance.

---

## Model Reference

### Image Models

| Model | Strengths | Best For | Aspect Ratios |
|---|---|---|---|
| `nano_banana_2` | Ultra-sharp 4K detail, photorealistic textures, excellent product rendering, strong character work | Product shots, character portraits, CGI renders, anime/stylized art, UGC characters | Any — 4:3 for product, 9:16 for portrait, 16:9 for landscape |
| `cinematic_studio_2_5` | Wide-angle cinematic composition, editorial depth, anamorphic lens look, environmental light | Brand establishing shots, fashion editorial, retail/real estate interiors, landscape hero images | 16:9 and 9:16 preferred |

**Rule of thumb**: Use `nano_banana_2` when the subject is in close — products, characters, textures. Use `cinematic_studio_2_5` when the scene is the story — environments, interiors, wide landscapes.

### Video Models

| Model | Strengths | Modes | Max Duration | Best For |
|---|---|---|---|---|
| `seedance_2_0` | Identity-preserving I2V, consistent character/object continuity, smooth camera movement | `std`, `fast` | 15 s | I2V workflows, product 360, brand story, editorial, all short-form formats |
| `kling3_0` | Multi-shot cinematic, superior motion physics, audio generation, dramatic camera work | `std`, `pro` | 10 s | Cinematic B-roll, orbiting hero shots, music video quality, establishing shots |

**Rule of thumb**: Use `seedance_2_0` for everything that starts from a keyframe (I2V). Use `kling3_0` when you want the most cinematic output on wide landscape/action sequences and audio matters.

---

## Critical Parameter Notes

These are non-obvious constraints that will cause silent failures or errors if ignored:

- **`seedance_2_0` modes**: only `std` and `fast`. Do NOT pass `pro` — it will error.
- **`kling3_0` modes**: only `std` and `pro`. Do NOT pass audio parameters directly.
- **No `generate_audio` for video models**: Audio is accepted via `medias` array only, not as a top-level param.
- **No `sound` parameter for `kling3_0`**: Silently ignored or errors depending on version.
- **I2V role**: Always `"role": "start_image"` for frame-anchored generation.
- **Full UUIDs only**: `job_display` requires complete `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` format. Never abbreviate.
- **`show_generations` only returns completed items**: In-progress jobs are invisible. Don't poll it repeatedly; just wait for completion.

---

## The 19 Skills — Reference Card

Skills live in `.claude/skills/`. Invoke via `/skill-name` in Claude Code. Each skill provides Seedance 2.0 on Higgsfield optimized prompt templates.

### Image Generation Skills

| Skill | What It Does | Best Image Model | Best Video Model |
|---|---|---|---|
| `/ugc-hot-girl` | Generates photorealistic attractive female UGC creator prompts for TikTok/Instagram ads | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/higgsfield-image-auto` | Playwright automation for Higgsfield Soul 2.0 image generation | — | — |
| `/seedance-auto-generate` | Playwright automation for Seedance video from local file | — | — |
| `/ugc-video-auto` | Full pipeline: character image → video on Higgsfield via Playwright | — | — |

### Video Production Skills

| Skill | What It Does | Best Image Model | Best Video Model |
|---|---|---|---|
| `/01-cinematic` | Cinematic narrative sequences, film grammar, dramatic camera work | `cinematic_studio_2_5` | `kling3_0` (pro) |
| `/02-3d-cgi` | Photorealistic CGI product renders, floating objects, studio lighting | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/03-cartoon` | Stylized cartoon characters, bold outlines, flat color palettes | `nano_banana_2` | `seedance_2_0` |
| `/04-comic-to-video` | Static comic panels → animated video, reading order aware, halftone preservation | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/05-fight-scenes` | Action combat choreography, impact frames, speed lines | `nano_banana_2` | `kling3_0` or `seedance_2_0` |
| `/06-motion-design-ad` | Kinetic typography, graphic design in motion, brand motion identity | `cinematic_studio_2_5` | `seedance_2_0` |
| `/07-ecommerce-ad` | Product showcase ads, e-commerce hero shots, lifestyle context | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/08-anime-action` | Cel-shaded anime aesthetics, shonen/seinen genres, power-up sequences | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/09-product-360` | Orbital product showcases, 360-degree rotation, commercial photography quality | `nano_banana_2` | `seedance_2_0` (I2V) |
| `/10-music-video` | Music video visual language, beat-synchronized cuts, artist performance | `cinematic_studio_2_5` | `kling3_0` (pro) |
| `/11-social-hook` | 2-second scroll-stopping hooks for TikTok / YouTube Shorts | any | `seedance_2_0` |
| `/12-brand-story` | Long-form brand narrative, emotional arc, premium brand film quality | `cinematic_studio_2_5` | `kling3_0` or `seedance_2_0` |
| `/13-fashion-lookbook` | Editorial fashion photography, model movement, magazine aesthetic | `cinematic_studio_2_5` | `seedance_2_0` (I2V) |
| `/14-food-beverage` | Food macro photography, appetite appeal, ASMR-ready texture shots | `nano_banana_2` | `seedance_2_0` |
| `/15-real-estate` | Property showcase walkthroughs, architectural cinematography, interior reveals | `cinematic_studio_2_5` | `kling3_0` or `seedance_2_0` |

---

## Image-to-Video (I2V) Workflow

The most important production technique: generate a keyframe image → animate it with `start_image`. This gives consistency across a campaign by anchoring every video to the same subject/character/product.

### Step-by-Step

**1. Generate the keyframe image**

```
generate_image(
  model="nano_banana_2",          # or cinematic_studio_2_5
  prompt="...",                   # detailed subject/scene description
  aspect_ratio="9:16"             # match your target video ratio
)
→ returns: image job ID (UUID)
```

**2. Verify the image completed**

Use `show_generations(type="image")` to confirm status is `completed` and retrieve the full UUID. Never assume a job completed — always verify before starting I2V.

**3. Submit the I2V video**

```
generate_video(
  model="seedance_2_0",
  prompt="...",                   # describe camera movement and action
  aspect_ratio="9:16",           # must match image aspect ratio
  duration=8,
  mode="std",
  medias=[{
    "role": "start_image",
    "value": "<image-job-uuid>"
  }]
)
→ returns: video job ID (UUID)
```

**4. Retrieve the result**

Use `show_generations(type="video")` once complete. The result includes `rawUrl` for the direct MP4 link.

### I2V Prompt Writing Rules

- **Lead with the keyframe state**: "From the keyframe of [subject/scene]..." so the model knows what to anchor to.
- **Describe camera movement explicitly**: "slow push-in", "lateral slide", "crane upward", "orbit right". Vague prompts produce drift.
- **Name the duration beats**: "camera moves continuously over 8 seconds", "at 6 seconds [event]". Helps model time the motion.
- **Avoid character teleportation**: Only describe changes that could physically happen from the starting pose.
- **No text overlays**: Always end with "No text." Text generation in video is unreliable.

### Consistency Across Multiple Videos

To maintain brand/character/product consistency across a multi-clip campaign:

1. Generate **one hero keyframe** (e.g., the ATLAS mountaineer portrait, `3bc49816`)
2. Use that same image UUID as `start_image` for every video in the sequence
3. Vary the prompt for different camera angles, times of day, or scene emphasis
4. The model preserves the subject identity — face, clothing, product — across all outputs

---

## ATLAS YouTube Production — 11 Clips

All clips are in the Higgsfield library. Edit order for a standard long-form YouTube video:

### Sequence Map

```
[HOOK 5s] → [ESTABLISHING 8s] → [BRAND STORY 12s] → [LOOKBOOK 8s] →
[PRODUCT 360 8s] → [HERO MOUNTAINEER 10s] → [ALPINE B-ROLL 8s] →
[CTA PRODUCT 8s] → [ANIME VARIANT 8s] → [COMIC VARIANT 8s] → [RETAIL 8s]
```

### Clip Catalog

| # | Job ID | Clip | Duration | Ratio | Model | Type | URL |
|---|---|---|---|---|---|---|---|
| 1 | `229c1f70` | **Hook** — carabiner close-up → epic mountain scale reveal | 5s | 9:16 | Seedance 2.0 T2V | T2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085126_229c1f70-3add-4b13-bd41-9a5f721bee17.mp4) |
| 2 | `474d89d2` | **Establishing** — Scottish Highlands orbit (Kling 3.0) | 8s | 16:9 | Kling 3.0 I2V | I2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085121_474d89d2-0178-4c55-af91-87763ce79cb1.mp4) |
| 3 | `26a7f1d7` | **Brand Story** — lone mountaineer slow push-in | 12s | 16:9 | Seedance 2.0 T2V | T2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085158_26a7f1d7-7ca4-451c-b2f6-b3b69006264b.mp4) |
| 4 | `ef512db1` | **Lookbook** — female athlete editorial slide | 8s | 9:16 | Seedance 2.0 I2V | I2V | pending |
| 5 | `e4551c34` | **Product 360** — backpack orbital showcase | 8s | 4:3 | Seedance 2.0 I2V | I2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085116_e4551c34-a47d-44cb-97be-21a495c644fc.mp4) |
| 6 | `b8e736c0` | **Hero Shot** — Dolomite mountaineer crane reveal | 10s | 9:16 | Seedance 2.0 I2V | I2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085151_b8e736c0-34ad-43d2-8976-d8802dc0ab79.mp4) |
| 7 | `ce2db362` | **Alpine B-Roll** — glacial lake glide | 8s | 16:9 | Seedance 2.0 T2V | T2V | pending |
| 8 | `6a86e6f2` | **CTA** — backpack unpack + hero reveal | 8s | 9:16 | Seedance 2.0 T2V | T2V | [mp4](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085202_6a86e6f2-8db3-406e-afc4-4fd2e0d78cb7.mp4) |
| 9 | `134602f4` | **Anime Variant** — power-up aura explosion | 8s | 9:16 | Seedance 2.0 I2V | I2V | pending |
| 10 | `16b566d5` | **Comic Variant** — panel border break | 8s | 9:16 | Seedance 2.0 I2V | I2V | pending |
| 11 | `85bb07a3` | **Retail Store** — slow push to hero product | 8s | 16:9 | Seedance 2.0 I2V | I2V | pending |

### Keyframe Images

| Job ID | Subject | Model | URL |
|---|---|---|---|
| `3bc49816` | Male mountaineer, Dolomites sunrise | Nano Banana 2 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_084428_3bc49816-9e52-4703-b9a1-f8928ca64eff.png) |
| `734c98b7` | Scottish Highlands hiker silhouette | Cinematic Studio 2.5 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_084434_734c98b7-6f88-421b-91a6-6dea2344e89e.png) |
| `25666a65` | Backpack flat-lay product shot | Nano Banana 2 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_084431_25666a65-c708-47d2-8018-037be09ce902.png) |
| `8b1f8c19` | Backpack CGI floating render | Nano Banana 2 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_084532_8b1f8c19-8ed2-44b7-b8a9-f05e08ca93db.png) |
| `63c66816` | Female athlete editorial, concrete wall | Cinematic Studio 2.5 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_084528_63c66816-7348-4810-80d1-8a68143bb703.png) |
| `565c72e9` | Anime mountaineer, cel-shaded | Nano Banana 2 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085045_565c72e9-dd19-4a1a-9e5b-b6d292060315.png) |
| `890ef4d0` | Flagship store interior | Cinematic Studio 2.5 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085048_890ef4d0-6368-438f-829b-ef47f11bef14.png) |
| `f0f64919` | Comic book cover, Frank Miller style | Nano Banana 2 | [png](https://d8j0ntlcm91z4.cloudfront.net/user_3DCqImD5gqUnmHWDuQ6OxBbzp5Y/hf_20260506_085251_f0f64919-b3ce-4278-ac25-9381c7b53899.png) |

---

## Skill Demonstration Examples (ATLAS)

### `/01-cinematic` — Brand Establishing Shot
- **Keyframe**: `734c98b7` — Scottish Highlands hiker silhouette at sunset
- **Video**: `474d89d2` — slow orbit revealing the moorland valley below (Kling 3.0, 8s)
- **Technique**: Cinematic slow orbit + volumetric light + atmospheric haze = premium brand film quality
- **Verdict**: Kling 3.0 pro handles wide landscape orbits with better physics than Seedance 2.0

### `/02-3d-cgi` — Product CGI Render
- **Keyframe**: `8b1f8c19` — Backpack floating against charcoal background (Nano Banana 2, 4:3)
- **Video**: `e4551c34` — orbital showcase, aluminum buckles catching light (Seedance 2.0 I2V, 8s)
- **Technique**: Nano Banana 2 nails photorealistic material textures; Seedance 2.0 I2V preserves product geometry through the orbit
- **Verdict**: Best combo for product 360 content

### `/04-comic-to-video` — Graphic Novel Animation
- **Keyframe**: `f0f64919` — Frank Miller-style ATLAS cover, charcoal/orange, Ben-Day dots (Nano Banana 2, 9:16)
- **Video**: `16b566d5` — Ben-Day sky animates, panel borders glow and break (Seedance 2.0 I2V, 8s)
- **Technique**: Specify halftone/Ben-Day explicitly; ask for panel border "break free" motion; use reading order guidance
- **Verdict**: Nano Banana 2 accurately generates halftone comic aesthetics; Seedance 2.0 animates stylized art well

### `/08-anime-action` — Anime Power-Up
- **Keyframe**: `565c72e9` — Shonen mountaineer, cel-shaded, golden iris, electric aura (Nano Banana 2, 9:16)
- **Video**: `134602f4` — aura pulsing outward, shockwave, speed lines (Seedance 2.0 I2V, 8s)
- **Technique**: Specify `tsurime` eyes, `cel-shaded`, `bold black outlines 5px`, speed lines in image prompt; then describe power-up expansion in video prompt
- **Verdict**: Nano Banana 2 handles anime cel-shading better than Cinematic Studio 2.5

### `/09-product-360` — Backpack Orbital
- **Keyframe**: `25666a65` — Backpack flat-lay on pine with climbing accessories (Nano Banana 2, 4:3)
- **Video**: `e4551c34` — smooth left-to-right orbit, buckles glinting (Seedance 2.0 I2V, 8s, 4:3)
- **Technique**: Use 4:3 for product (wider than product portrait, less wasted space than 16:9); describe orbit direction explicitly
- **Verdict**: I2V anchoring prevents the backpack from morphing mid-orbit — critical for product accuracy

### `/11-social-hook` — YouTube Shorts Hook
- **Video**: `229c1f70` — carabiner extreme close-up → epic scale reveal (Seedance 2.0 T2V, 5s, 9:16)
- **Technique**: "Extreme close-up of [unrecognizable detail] → sudden whip-pan → rapid pull-back reveals full scale" is the core hook formula
- **Verdict**: 5s T2V hook works well as pure T2V — no image anchor needed when the subject changes dramatically

### `/12-brand-story` — Long-Form Narrative
- **Video**: `26a7f1d7` — lone mountaineer slow push-in, 12 seconds (Seedance 2.0 T2V, 16:9)
- **Video**: `b8e736c0` — Dolomite mountaineer crane upward (Seedance 2.0 I2V, 10s, from `3bc49816`)
- **Technique**: Brand story T2V at 12s with a single continuous camera movement; I2V brand story anchored to the hero character. Use "patient, deliberate" language in prompt to prevent rushed camera movement.
- **Verdict**: Both work well; I2V version has stronger character consistency because it anchors to the actual keyframe

### `/13-fashion-lookbook` — Editorial Fashion
- **Keyframe**: `63c66816` — female athlete in slate-grey ATLAS fleece (Cinematic Studio 2.5, 9:16)
- **Video**: `ef512db1` — slow lateral slide, over-shoulder gaze (Seedance 2.0 I2V, 8s)
- **Technique**: Use Cinematic Studio 2.5 for the keyframe (superior editorial framing and light); then I2V with lateral camera slide to add motion
- **Verdict**: Cinematic Studio 2.5 is the right tool for fashion editorial keyframes — Nano Banana 2 is better for close-up product/character but lacks editorial compositionnal quality

### `/15-real-estate` — Retail Interior
- **Keyframe**: `890ef4d0` — ATLAS flagship store interior (Cinematic Studio 2.5, 16:9)
- **Video**: `85bb07a3` — slow push toward hero backpack (Seedance 2.0 I2V, 8s)
- **Technique**: Cinematic Studio 2.5 for architecture/interior (it excels at interior editorial shots); slow push-in I2V preserves the spatial depth of the scene
- **Verdict**: This workflow (Cinematic Studio 2.5 keyframe → Seedance 2.0 I2V) is ideal for retail, real estate, and architectural showcase content

---

## Credit Cost Estimates

Based on observed usage during ATLAS production session:

| Generation Type | Model | Approx Credits |
|---|---|---|
| Image | `nano_banana_2` (1k res) | ~5–8 |
| Image | `cinematic_studio_2_5` (1k res) | ~8–12 |
| Video 5s T2V | `seedance_2_0` std | ~15–20 |
| Video 8s T2V | `seedance_2_0` std | ~20–25 |
| Video 10s T2V | `seedance_2_0` std | ~25–30 |
| Video 12s T2V | `seedance_2_0` std | ~30–35 |
| Video 8s I2V | `seedance_2_0` std | ~20–28 |
| Video 8s I2V | `kling3_0` std | ~30–40 |
| Video 8s I2V | `kling3_0` pro | ~50–70 |

**ATLAS total cost estimate**: 8 images (~70 credits) + 11 videos (~280 credits) ≈ **~350 credits total**

---

## Workflow Recommendations

### What Worked Well

1. **Cinematic Studio 2.5 → Seedance 2.0 I2V** is the most reliable quality pipeline for editorial, fashion, and architectural content. The keyframe quality directly sets the ceiling for video quality.

2. **Nano Banana 2 for everything close-up**: Products, characters, stylized art (anime, CGI, comic). Produces sharper textures and better material accuracy than Cinematic Studio 2.5 at this range.

3. **Kling 3.0 for wide landscapes**: The Highlands orbit (`474d89d2`) has superior motion physics compared to what Seedance 2.0 produces on wide-angle landscape I2V. Use Kling 3.0 pro for establishing shots and B-roll where cinematic quality is the priority.

4. **4:3 for product videos**: The backpack 360 (`e4551c34`) in 4:3 fills the frame better than 16:9 without the awkward empty space around a product.

5. **Explicit camera movement language**: Prompts that name specific moves ("slow crane upward", "lateral slide left", "push-in toward [subject]") produce far more predictable results than vague descriptors like "cinematic movement".

### Improvements to Make

1. **Generate at 4K**: All current keyframes are at `1k` resolution. Upgrading to `2k` or `4k` will significantly improve the ceiling for video quality, especially for product close-ups where material texture matters.

2. **Use Kling 3.0 pro for more clips**: The Highlands orbit showed Kling 3.0 produces higher cinematic quality than Seedance 2.0 on landscape sequences. The brand story clip (`26a7f1d7`) would have been stronger with Kling 3.0 pro.

3. **End-frame anchoring**: Seedance 2.0 supports `end_image` role in addition to `start_image`. Generating a start keyframe AND an end keyframe then submitting both creates a controlled transition — useful for before/after, sunrise-to-sunset, or character-transformation sequences.

4. **Batch keyframe variants**: For A/B testing, generate 3–4 keyframe variants at image stage (different models, lighting, compositions) then run I2V on all. Video generation time is the bottleneck; having multiple keyframe options is cheap.

5. **Character sheets for UGC**: For brand spokesperson content, generate a full character sheet (frontal, profile, three-quarter, action pose) as separate keyframes all from the same prompt seed. Submit all as I2V for a consistent character across multiple ads.

6. **Separate aspect ratios by platform**:
   - YouTube long-form: 16:9
   - YouTube Shorts / TikTok / Reels: 9:16
   - Product e-commerce: 4:3 or 1:1
   - Fashion editorial: 9:16
   Plan the ratio at keyframe generation stage — re-generating at a different ratio is expensive.

7. **Muapi.ai as a cheaper fallback**: The Pinguz MCP server (wrapping Muapi.ai) provides access to many of the same models (Seedance, Kling, Veo, Wan, Flux) at potentially lower cost. Use it for high-volume batch generation, and Higgsfield for quality-critical hero content.

---

## Pinguz MCP vs Higgsfield MCP

| Capability | Pinguz (Muapi.ai) | Higgsfield MCP |
|---|---|---|
| Image generation | Flux Dev, Flux Pro, Midjourney, Imagen 4, GPT-4o, Qwen | Soul 2.0, Nano Banana 2, Cinematic Studio 2.5 |
| Video generation | Seedance 2.0, Kling 2.6, Veo 3.1, Wan 2.5, Hunyuan, Minimax | Seedance 2.0, Kling 3.0, Veo 3.1, Marketing Studio |
| Billing | Per-generation via Muapi key | Higgsfield credit balance |
| I2V workflow | `images_list` URL param | `medias[role=start_image]` with job UUID |
| Quality ceiling | Good | Higher (newer models, better UI integration) |
| Best use | Batch generation, budget-sensitive workflows | Hero content, campaign keyframes, highest quality |

---

## Quick-Start: New ATLAS Campaign Clip

```bash
# 1. Generate keyframe
generate_image(
  model="nano_banana_2",           # or cinematic_studio_2_5 for wide scenes
  prompt="ATLAS brand [subject]. [Detailed description]. Matte charcoal hardshell jacket. Slate grey accents. ATLAS embossed logo. [Lighting]. [Composition]. No text.",
  aspect_ratio="9:16"              # or 16:9 for landscape
)
# → image UUID: xxxxxxxx-...

# 2. Verify completed
show_generations(type="image")    # confirm status=completed, copy full UUID

# 3. Animate
generate_video(
  model="seedance_2_0",
  prompt="From the keyframe of [subject], camera [movement description]. [Lighting]. [Atmosphere]. No text.",
  aspect_ratio="9:16",
  duration=8,
  mode="std",
  medias=[{"role": "start_image", "value": "<uuid>"}]
)

# 4. Retrieve
show_generations(type="video")    # copy rawUrl when status=completed
```
