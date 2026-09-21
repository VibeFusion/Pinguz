"""Prompt catalog for the background clip bank.

Every clip is "oddly satisfying" B-roll: continuous, rhythmic, no faces, no text.
The visual channel must never compete with the narration, so prompts avoid
anything with narrative content of its own.
"""

from __future__ import annotations

from dataclasses import dataclass

STYLE_SUFFIX = (
    "vertical 9:16 framing, close-up, continuous smooth motion, soft even lighting, "
    "sharp focus, high detail, no people, no faces, no text, no watermark, seamless loop"
)

CATEGORIES: dict[str, list[str]] = {
    "kinetic-sand": [
        "a metal blade slicing cleanly through a block of pastel kinetic sand on a white table",
        "kinetic sand being pressed into a star mold and released, crumbling slowly",
        "a wide flat scraper pushing a wall of glittering kinetic sand across a board",
        "kinetic sand pouring from a cup and collapsing into soft dunes",
    ],
    "soap-cutting": [
        "a sharp knife shaving thin curls off a bar of bright yellow soap",
        "dry soap bar being scored into a grid and each cube snapping off",
        "a lavender soap block sliced into perfect even slabs on a wooden board",
        "translucent glycerin soap cubes tumbling out of a mold one by one",
    ],
    "hydraulic-press": [
        "a hydraulic press slowly crushing a stack of colorful crayons",
        "a hydraulic press flattening a rubber duck, top-down view",
        "a hydraulic press compressing a block of foam sponge until it bursts sideways",
        "a hydraulic press squeezing a bar of soap into a smooth flat disc",
    ],
    "slime": [
        "glossy teal slime stretched slowly between two hands wearing white gloves",
        "a cup of clear slime with glitter poured onto a mirror surface",
        "fluffy pink slime pressed flat and lifted, forming long strings",
        "crunchy slime full of foam beads being squeezed and folded",
    ],
    "food-processing": [
        "corn cobs pouring from a bucket into a giant steel bowl of boiling water",
        "fresh pasta being extruded from a brass machine in dozens of even strands",
        "a mandoline slicing a cucumber into perfectly uniform thin discs",
        "a steel roller pressing sesame candy flat as it slides across a marble slab",
    ],
    "wood-splitting": [
        "a cone log splitter drilling into a round oak log until it cracks apart",
        "a splitting maul driving into a birch log that splits cleanly down the middle",
        "kindling being split rapidly from a block of pine with a hatchet",
        "wood chips flying as a chisel carves a deep groove into a plank",
    ],
    "pressure-washing": [
        "a pressure washer stripping black grime from a concrete patio in clean stripes",
        "moss blasted off a brick wall by a pressure washer, clean red brick emerging",
        "a pressure washer clearing years of dirt from a wooden deck, plank by plank",
        "algae being blasted off a white plastic fence with a pressure washer",
    ],
    "marble-run": [
        "hundreds of glass marbles cascading down a wooden marble run with many tiers",
        "a single steel ball rolling through a wooden track with gentle turns and drops",
        "marbles funneling through a spiral vortex track into a collection tray",
        "colorful marbles racing down a sand track with banked curves",
    ],
    "candle-carving": [
        "a hot knife carving ribbons from a multicolored layered candle, curls falling",
        "a candle being dipped into vibrant wax and pulled out in one smooth motion",
        "a rotating candle being shaved into a smooth spiral pattern",
        "melted wax dripping down a pillar candle forming smooth layers",
    ],
    "paint-mixing": [
        "thick white paint being folded into deep blue paint with a palette knife",
        "a paint mixer stirring a bucket of orange paint into a smooth vortex",
        "three colors of acrylic paint pressed together under a glass plate and spread",
        "a spatula scraping a rainbow of paints in one long stroke across a canvas",
    ],
}


@dataclass(frozen=True)
class ClipPrompt:
    category: str
    text: str


def build_prompt(base: str) -> str:
    """Attach the shared style suffix to a base scene description."""
    return f"{base.strip().rstrip('.')}, {STYLE_SUFFIX}"


def all_prompts(
    categories: list[str] | None = None,
    per_category: int | None = None,
) -> list[ClipPrompt]:
    """Return prompts for the requested categories (all by default)."""
    cats = categories or list(CATEGORIES)
    unknown = [c for c in cats if c not in CATEGORIES]
    if unknown:
        raise ValueError(
            f"Unknown categories: {', '.join(unknown)}. Valid: {', '.join(CATEGORIES)}"
        )
    out: list[ClipPrompt] = []
    for cat in cats:
        bases = CATEGORIES[cat]
        if per_category is not None:
            bases = bases[:per_category]
        out.extend(ClipPrompt(cat, build_prompt(b)) for b in bases)
    return out
