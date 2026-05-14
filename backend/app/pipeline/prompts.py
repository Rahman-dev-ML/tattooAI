"""
Tattoo edit prompts — v3 (TIGHT).

Lessons from v2:
- Long multi-zone briefs confused the image-edit model.
- "ALLOWED MOTIFS ONLY" whitelists actively fought user subjects (a user
  describing a dragon vs a fine-line whitelist of "roses, butterflies"
  produced garbage).
- photo_convert lost its reference fidelity because the style brief
  buried the "tattoo this exact reference" instruction.

Principles for v3:
1. Short focused prompts (~200-300 words). The model reads better.
2. The SUBJECT always leads. Style is a rendering descriptor, not a gatekeeper.
3. No "allowed motifs only" whitelists.
4. photo_convert with a reference image gets its own dedicated prompt
   that bypasses the style brief and pushes "replicate the reference exactly".
5. Realism block is non-negotiable and ships with every prompt.
6. Variations are ONE soft intent line per render, not 6 sub-zones.
"""
from __future__ import annotations

import random
import re
from typing import Any, Optional, Tuple


# Strip ", approximately Xcm" / "(approximately X to Y cm)" patterns from motif
# lines before they enter a prompt — the SIZE block at the top of the prompt is
# the single source of truth for size, and competing numbers in the subject line
# cause the image-edit model to average them and overshoot.
_SIZE_HINT_RE = re.compile(
    r"\s*[,(\[]?\s*approximately[^,)\]]*?\d+\s*(?:to\s*\d+\s*)?(?:cm|inches?|in)\s*[\)\]]?",
    re.IGNORECASE,
)


def _strip_size_hints(text: str) -> str:
    if not text:
        return text
    return _SIZE_HINT_RE.sub("", text).replace("  ", " ").strip().strip(",.;: ")


# Strip secondary clauses that bloat a small tattoo. When the user asks for
# small, we want a SINGLE element. "rose with three leaves and a butterfly
# above" becomes "rose". This is run only for small/subtle paths.
_ACCESSORY_CLAUSE_RE = re.compile(
    r"\s*(,|with|and|surrounded by|carrying|holding|cradling|nestled|wrapped by|embraced by|behind|above|below|beside|beneath)\s+.*$",
    re.IGNORECASE,
)


def _simplify_subject_for_small(text: str) -> str:
    """Reduce a multi-clause focal subject to its single primary noun phrase."""
    if not text:
        return text
    t = text.strip().rstrip(".,; ")
    # If the line starts with a special tag like 'EXACT lettering:' or
    # 'PRIMARY symbol:' we leave it alone.
    if t.upper().startswith(("EXACT ", "PRIMARY ", "ACCOMPANYING ")):
        return t
    simplified = _ACCESSORY_CLAUSE_RE.sub("", t).strip().rstrip(",.; ")
    # If we accidentally chopped to nothing useful, fall back.
    if len(simplified) < 6:
        return t
    return simplified


# ===========================================================================
# 1. GLOBAL BLOCKS
# ===========================================================================

NO_TEXT_RULE = (
    "NO TEXT — zero letters, words or numbers anywhere in the design. "
    "If any text appears in the output it is a failure."
)

REALISM_BLOCK = """TATTOO REALISM AND INK LOCK (MANDATORY — read carefully):
- The tattoo is REAL HEALED INK SETTLED INTO THE DERMIS. NO sticker look, NO decal look, NO printed-paper look, NO clip-art look, NO digital-illustration-on-skin look.
- Edges sit on the skin naturally and are slightly darker where lines overlap (real ink builds density at intersections). Edges are clean but NOT vector-perfect — slight organic micro-bleed where the ink has spread into the dermis.
- The ink is matte fully-healed. This is an OLD HEALED tattoo, not a fresh one. NO glossy ink shine, NO Vaseline sheen, NO fresh-tattoo wet look.
- Skin pores, hair follicles, freckles and natural skin texture are CLEARLY VISIBLE through and around the ink. The skin underneath the tattoo is preserved — pores still show, the surface is not flattened or smoothed.
- Skin tone around the tattoo is the EXACT same as the rest of the photo. ABSOLUTELY NO pink, red, orange, purple, yellow, or any coloured halo, glow, wash, patch, rectangle or background behind or around the tattoo. NO skin redness, NO irritation, NO scabbing.
- Slight natural hand-tattooed variation in line weight — lines have subtle wobble, not all perfectly parallel, not computer-perfect uniform vector. Real tattoos have human-hand imperfection.
- The design WRAPS with body curvature — follows muscle, tendon, bone and limb shape. The photo's existing lighting and shadows fall OVER the tattoo naturally; the tattoo does NOT carry its own lighting from a separate source.
- Keep the SAME body, background, skin tone, jewellery, clothing and lighting from the original photo. Do not smooth, retouch or alter the skin.
- Forbidden looks: sticker, decal, clip art, stamp, logo, badge, vector graphic, paper sketch, pen drawing, pencil drawing, digital illustration overlaid on skin, coloured background box, coloured halo behind tattoo, photographic image inserted onto skin.
- A viewer must believe this is a REAL PHOTOGRAPH of a REAL PERSON who walked out of a real tattoo studio with this exact tattoo six months ago — not an AI render of a tattoo."""

CRITICAL_CLOSER = (
    "CRITICAL: This must look like a real photograph of a real person with a real "
    "healed tattoo on real skin. If it reads as a STICKER, a DECAL, a graphic "
    "placed ON TOP of skin, or a digital illustration overlaid onto skin "
    "(instead of INK IN the skin with skin pores visible through it), it is wrong."
)


# ===========================================================================
# 2. BODY REGION ANATOMY (short, one line each)
# ===========================================================================

REGION_ANATOMY: dict[str, str] = {
    "forearm": "outer or inner forearm — design runs along the long axis of the limb and wraps slightly with the cylindrical muscle curvature.",
    "upper_arm": "upper arm / bicep — design runs along the arm length and wraps with the rounded muscle.",
    "shoulder": "deltoid cap — design follows the rounded shoulder curve.",
    "wrist": "wrist / lower forearm — small scale, follows the wrist curve and bone ridge.",
    "hand_back": "back of hand — small scale, respects knuckle creases and tendon lines.",
    "calf": "calf muscle — vertical flow along the calf belly, wraps with its curve.",
    "thigh": "thigh — runs along the leg length, follows quad shape, room for medium to large piece.",
    "chest": "chest / pec — follows the pec shape and respects the centerline.",
    "upper_back": "upper back between scapulae — flows with back curvature, respects the spine line.",
    "ribs": "ribs / flank — conservative detail, vertical flow following rib lines.",
    "ankle": "ankle / lower shin — small scale, follows the ankle bone contour.",
    "neck": "neck side / nape — conservative scale, follows the neck curve.",
    "other": "the main visible skin region in the photo — wraps with body curvature.",
    "from_photo": "skin in the photo — infer placement, scale and angle from anatomy, and wrap with the body's curvature, perspective and lighting.",
}

# When coverage=small (or strength=subtle), we anchor to a TINY specific
# landmark inside each region. This is the single biggest fix for "I asked
# for small and got medium" — image-edit models respond far better to a
# narrow named spot than to abstract size numbers.
_NARROW_PLACEMENT: dict[str, str] = {
    "forearm":   "Place one small-to-medium motif on the inner or outer forearm near the wrist-half of the limb, aligned with tendon flow and wrapped to forearm curvature.",
    "upper_arm": "Place one small-to-medium motif on the outer shoulder cap or upper bicep, following the arm's cylindrical wrap.",
    "shoulder":  "Place one small-to-medium motif on the front or outer deltoid so the piece follows shoulder curvature naturally.",
    "wrist":     "Place one compact motif on or just above the wrist crease / wrist bone area, with clean readability at glance distance.",
    "hand_back": "Place one compact motif near the thumb base or between knuckles, respecting tendon lines and knuckle creases.",
    "calf":      "Place one small-to-medium motif on the outer calf with vertical flow and subtle wrap over muscle curvature.",
    "thigh":     "Place one small-to-medium motif on the outer or front thigh, centered cleanly with natural quad wrap.",
    "chest":     "Place one small-to-medium motif on a single pec near collarbone or sternum, respecting chest contour.",
    "upper_back":"Place one small-to-medium motif on one scapula zone or upper nape zone, aligned to back flow.",
    "ribs":      "Place one compact motif on side ribs / flank with conservative detail and natural rib-line flow.",
    "ankle":     "Place one compact motif around the ankle bone / lower shin transition, readable at small scale.",
    "neck":      "Place one compact motif on the side neck / behind-ear zone, following neck curve.",
    "other":     "Place one clearly readable small-to-medium motif on a single area of visible skin with realistic wrap and perspective.",
    "from_photo":"Place one clearly readable small-to-medium motif on a single area of the visible skin in this photo, preserving anatomy and perspective.",
}


# ===========================================================================
# 3. STYLE DESCRIPTORS (one tight paragraph per style)
# ===========================================================================

STYLE_DESCRIPTORS: dict[str, str] = {
    "fine_line": (
        "REAL FINE-LINE TATTOO INK in the skin — hair-thin single-needle linework, healed dark ink that has settled into the dermis. "
        "Single weight throughout with the slightest natural pressure variation. Minimal or no shading. "
        "The lines are CRISP TATTOO INK on real skin — NOT a pencil sketch, NOT a pen drawing, NOT line art placed on top of the photo. "
        "Lots of negative space — design occupies roughly 10 to 18 percent of the visible skin. "
        "Feels delicate, intimate, executed by a master fine-line tattoo artist (Dr. Woo / JonBoy quality)."
    ),
    "minimalist": (
        "Tiny single-element TATTOO INK in the skin. Hair-thin clean linework, single weight, possibly one micro accent dot. "
        "The mark is REAL HEALED TATTOO INK that has settled into the dermis — NOT a sketch, NOT a sticker, NOT a doodle on top of the skin. "
        "Massive surrounding negative space — design occupies under 12 percent of the visible skin. "
        "One mark, breathing room everywhere. Quiet, confident, intentional."
    ),
    "blackwork": (
        "Bold confident outer contour with packed solid matte BLACK masses, and intentional negative-space windows "
        "carved through. No grey gradients — only solid black vs bare skin. Coverage roughly 25 to 45 percent. "
        "Modern blackwork sensibility (Valerie Vargas / Thomas Hooper level — not 90s tribal)."
    ),
    "traditional": (
        "American/European traditional flash style — bold confident outline, thinner interior lines, limited classic "
        "B&G whip shading and flat tonal blocks (NOT airbrushed gradients). Coverage roughly 25 to 45 percent. "
        "Reads like a clean Sailor Jerry / Ed Hardy lineage flash piece executed by a senior shop tattooer."
    ),
    "japanese": (
        "Traditional irezumi — bold confident outer contour with varying interior weight, soft controlled grey shading, "
        "structured negative space and optional thin wind-bar accents. Coverage roughly 35 to 60 percent. Design flows "
        "WITH the limb direction. Horiyoshi-lineage discipline — bold, flowing, committed."
    ),
    "realism": (
        "Black-and-grey photorealism — NO outlines anywhere. Form defined entirely by soft controlled grey gradients "
        "and deep blacks in shadow. Light direction matches the existing photo lighting. Edges fade organically into "
        "bare skin. Coverage roughly 25 to 50 percent. Nikko Hurtado / Carlos Torres B&G quality."
    ),
    "geometric": (
        "Precise geometric forms — clean straight edges, ruler-quality arcs, consistent line weight, optional measured "
        "single dotwork at vertices (NOT noise clouds). Sacred geometry, faceted forms, mandala structures. Coverage "
        "roughly 20 to 40 percent. Chaim Machlev / Dillon Forte precision."
    ),
    "ornamental": (
        "Jewelry-quality ornamental linework — baroque filigree, fine teardrops, bead-chain accents, lace openwork. "
        "Delicate interior with a slightly stronger outer rim. Looks like a piece of jewelry placed on the skin. "
        "Coverage roughly 25 to 45 percent. Jondix / Carola Deutsch ornamental sensibility."
    ),
    "script": (
        "Hand-lettered script tattoo. Letterforms have proper weight rhythm, kerning and spacing. NEVER a computer "
        "font printed on skin. Lettering follows the natural anatomical curve of the chosen body part. Minimal or "
        "no shading — the lettering is the entire tattoo."
    ),
    "auto": (
        "Professional shop-quality tattoo. Choose the most appropriate single style for the subject (fine line for "
        "delicate subjects, blackwork for bold silhouettes, traditional for classic icons, B&G realism for portraits). "
        "Commit to one style fully — do not blend multiple styles. Coverage roughly 15 to 35 percent."
    ),
    "stencil": (
        "Tattoo STENCIL style — bold clean confident OUTLINE only, hollow interiors, the look of the artist's "
        "stencil applied to skin before fill. No shading, no fill colour, no dotwork — just crisp outline. "
        "Reads as a clear graphic silhouette rendered in real tattoo ink that has settled into the skin."
    ),
}


# ===========================================================================
# 3a. STYLE ALIASES (UI labels → canonical style key)
# ===========================================================================

_STYLE_ALIASES: dict[str, str] = {
    "minimal": "minimalist",
    "realistic": "realism",
    "fine line": "fine_line",
    "fine-line": "fine_line",
    "japanese-inspired": "japanese",
    "japanese inspired": "japanese",
    "geometric interpretation": "geometric",
    "ornamental interpretation": "ornamental",
    "bw": "blackwork",
    "b&w": "blackwork",
    "blackandgrey": "realism",
    "black and grey": "realism",
    "lettering": "script",
    "type": "script",
    "irezumi": "japanese",
    # canonical ones map to themselves so any pass through normalises cleanly
    "fine_line": "fine_line",
    "minimalist": "minimalist",
    "blackwork": "blackwork",
    "traditional": "traditional",
    "japanese": "japanese",
    "realism": "realism",
    "geometric": "geometric",
    "ornamental": "ornamental",
    "script": "script",
    "auto": "auto",
    "stencil": "stencil",
}


def _normalize_style(raw: str) -> str:
    """Map any UI/legacy style label to a canonical STYLE_DESCRIPTORS key."""
    key = (raw or "").strip().lower().replace("-", "_")
    if key in STYLE_DESCRIPTORS:
        return key
    if key in _STYLE_ALIASES:
        return _STYLE_ALIASES[key]
    # try the raw form too (with spaces)
    return _STYLE_ALIASES.get((raw or "").strip().lower(), "auto")


# ===========================================================================
# 4. STYLE INTENT VARIATIONS (one soft compositional line per render)
# ===========================================================================

STYLE_INTENTS: dict[str, list[str]] = {
    "fine_line": [
        "Composition: single focal element slightly off-centre, intimate scale, generous negative space.",
        "Composition: gentle diagonal flow along the body part axis, hair-fine throughout.",
        "Composition: centred elegant placement, one focal element with at most a tiny micro accent nearby.",
        "Composition: vertical flow with a small trailing accent below the focal element.",
        "Composition: floating placement on the inner-facing surface, quiet and personal.",
    ],
    "minimalist": [
        "Composition: one tiny mark on the flattest skin area with vast surrounding negative space.",
        "Composition: subtle off-centre placement, breathing room dominates.",
        "Composition: along the natural muscle or tendon line, small and placed.",
        "Composition: inner-surface placement, intimate and personal.",
    ],
    "blackwork": [
        "Composition: strong central silhouette with planned negative-space windows carved through.",
        "Composition: asymmetric bold mass on one side, balanced by negative geometric space on the other.",
        "Composition: vertical bold piece running along the limb with a rhythm of negative windows down its length.",
        "Composition: wrapping bold composition that curves around the body part, with negative space catching light.",
    ],
    "traditional": [
        "Composition: classic flash icon centred with optional small banner or leaf-spur accents.",
        "Composition: dynamic diagonal — main icon angled for movement, with classic spark-dot accents.",
        "Composition: stacked flash vignette — main icon with one smaller classic accent above or below.",
        "Composition: compact tightly-composed icon — clean readable silhouette at distance.",
    ],
    "japanese": [
        "Composition: clear focal subject with sparse atmospheric background and thin wind-bar accents.",
        "Composition: ascending diagonal flow with the subject moving upward and structured negative space below.",
        "Composition: subject wrapping the body with optional cherry-blossom or wave accents drifting nearby.",
        "Composition: subject anchored against a small background element (wave, cloud wisp or wind bars).",
    ],
    "realism": [
        "Composition: focal subject sharpest at the centre, outer edges fading softly into bare skin.",
        "Composition: subject angled to catch the photo's existing light source, reinforcing realism.",
        "Composition: depth-of-field falloff — sharp focus at centre, organic soft edges all around.",
    ],
    "geometric": [
        "Composition: one dominant geometric form centred, with intentional empty negative space around it.",
        "Composition: nested sacred-geometry rings with bilateral symmetry along the limb axis.",
        "Composition: faceted subject built from clean triangulated planes with measured dotwork at vertices.",
        "Composition: stacked geometric forms — main shape anchored by smaller geometric accents.",
    ],
    "ornamental": [
        "Composition: jewelry-like piece centred on the body area, draping naturally with the curve.",
        "Composition: symmetrical baroque filigree with a chandelier-style drop terminal.",
        "Composition: pendant style — anchored at a natural body line with filigree extending downward.",
        "Composition: mirrored ornamental design with bilateral symmetry along the body axis.",
    ],
    "script": [
        "Baseline gently arches with the natural anatomy of the body part.",
        "Single short line of text, baseline at the natural viewing angle.",
        "Text flows along the longest axis of the body part with natural curve.",
    ],
    "auto": [
        "Composition: one clear focal element professionally placed and scaled for this body area.",
        "Composition: balanced single piece — neither too crowded nor too sparse.",
        "Composition: one cohesive subject with optional minimal supporting accent for balance.",
    ],
    "stencil": [
        "Composition: clean graphic silhouette outline, hollow inside, no fill.",
        "Composition: confident single outline rendered as if it were the artist's stencil applied to skin.",
        "Composition: bold outline with the slight irregularity of hand-applied tattoo ink.",
    ],
}


# ===========================================================================
# 5. CONCRETE MOTIF LIBRARIES PER STYLE (used when user has no explicit subject)
# ===========================================================================

MOTIFS_FINE_LINE: list[str] = [
    "single elegant rose with one open bloom and three closed buds, hair-thin contour with suggested petal veins, approximately 7cm",
    "delicate hummingbird in mid-flight with one extended wing, fine vein detail in the feathers, approximately 6cm",
    "continuous single-line orchid bloom drawn without lifting the needle, elegant interior fold lines, approximately 6cm",
    "dainty wildflower bouquet of three small flower types loosely tied with a thin ribbon, approximately 8cm",
    "snake coiled in a soft S, body shaded with delicate dotwork scales, head turned to the viewer, approximately 9cm",
    "crescent moon embraced by a thin botanical branch with five small leaves, approximately 7cm",
    "delicate butterfly with mirrored wing veins and tiny dot accents, single-needle quality, approximately 5cm",
    "peony bloom with layered petals and one trailing stem, fine interior shading on the front petal only, approximately 7cm",
    "small fox curled asleep, tail wrapped around body, fine fur strokes only on the tail tip, approximately 6cm",
    "lavender sprig of three flower clusters on a single curved stem, approximately 7cm",
    "tall ship under sail with thread-fine rigging lines and two billowing sails, approximately 7cm",
    "dragonfly with detailed wing veins and a slim segmented body, approximately 5cm",
    "compass rose with thin radiating points and a tiny star at the centre, approximately 6cm",
    "small mountain range silhouette with a crescent moon above, single continuous line, approximately 7cm",
    "tiny bird perched on a thin branch, head turned, single tail feather curving down, approximately 5cm",
    "lotus flower viewed from the side with three layered petals, single root line below, approximately 6cm",
    "single feather with detailed barbs only on one side, approximately 6cm",
    "small eye with detailed lashes and a single tear on the cheek line, approximately 5cm",
    "constellation of seven dots connected by hair-thin lines, framed by a thin circle, approximately 6cm",
    "tiny anatomical heart with delicate vein lines, no shading, approximately 5cm",
    "flowering branch of cherry blossoms with two falling petals nearby, approximately 8cm",
    "small swallow in flight with one extended wing forward, approximately 6cm",
    "delicate cat sitting in profile, tail curling forward, approximately 5cm",
    "hand-drawn fern leaf with five paired leaflets along a thin spine, approximately 7cm",
    "abstract single-line wave with three crests, ending in a tiny spray dot, approximately 7cm",
    "small key with an ornate bow and a tiny heart inside the handle, approximately 5cm",
    "delicate jellyfish with thread-fine trailing tendrils and a domed bell, approximately 7cm",
    "single arrow with feathered fletching split into three barbs, hair-thin shaft, approximately 7cm",
    "tiny anchor with a thin rope wrapping the shaft, approximately 6cm",
    "small swan in profile with elegant curved neck, approximately 6cm",
]

MOTIFS_BLACKWORK: list[str] = [
    "bold blackwork wolf head silhouette with jagged negative-space teeth and a single eye highlight in the skin, approximately 9cm",
    "solid black raven mid-takeoff with negative-space wing tips, approximately 10cm",
    "blackwork mountain triptych — three solid black peaks with two thin negative-space valleys, approximately 11cm",
    "heavy blackwork moth with patterned negative-space windows in the wings, symmetrical body, approximately 10cm",
    "solid blackwork bear paw print with three sharp negative-space claw notches, approximately 8cm",
    "thick blackwork crescent moon with a negative-space face and a single eye, approximately 9cm",
    "bold blackwork serpent in S-curve, body filled solid with negative-space scale lines carved through, approximately 12cm",
    "blackwork mandala fragment — a quarter wedge of solid blacks divided by negative-space rays, approximately 10cm",
    "solid blackwork beetle viewed from above with patterned wing-case windows, approximately 8cm",
    "heavy blackwork heart with a negative-space lightning bolt cut through, approximately 8cm",
    "blackwork lighthouse silhouette with bold radial light rays carved as negative space, approximately 10cm",
    "solid black skull with negative-space eye sockets and bold geometric jaw, approximately 9cm",
    "blackwork hand of fatima with carved negative-space interior pattern, approximately 9cm",
    "solid black koi mid-leap with carved negative-space scales and water spray dots, approximately 11cm",
    "blackwork eye-of-providence triangle with negative-space iris and bold radiating rays, approximately 10cm",
    "solid blackwork tiger head facing forward with negative-space stripe pattern, approximately 10cm",
    "blackwork sun and moon back-to-back, solid blacks with carved negative-space facial detail, approximately 10cm",
    "solid black phoenix rising with bold negative-space wing feather pattern, approximately 12cm",
    "blackwork beehive with bold negative-space honeycomb cells and three solid bees nearby, approximately 9cm",
    "heavy blackwork bull skull with horned silhouette and negative-space eye sockets, approximately 10cm",
    "solid blackwork compass with bold cardinal points and negative-space directional needle, approximately 9cm",
    "blackwork crescent moon cradling three solid black stars, with negative-space craters, approximately 9cm",
    "solid black anchor with bold rope wrap, negative-space rope highlights, approximately 9cm",
    "blackwork hand holding a solid black rose, negative-space petal divisions carved cleanly, approximately 10cm",
    "solid blackwork mushroom cluster with carved negative-space gill lines, approximately 8cm",
    "bold blackwork ouroboros snake biting its tail, solid body with negative-space scale rhythm, approximately 9cm",
    "blackwork triangle with a solid black mountain inside and a negative-space sun above the peak, approximately 9cm",
    "heavy blackwork crown silhouette with carved negative-space jewels along the band, approximately 9cm",
    "blackwork floral bouquet — three solid black blooms tied with a bold negative-space ribbon, approximately 11cm",
    "solid blackwork dagger pointing downward with carved negative-space hilt pattern, approximately 11cm",
]

MOTIFS_TRADITIONAL: list[str] = [
    "bold traditional rose in full bloom with chunky outline, layered petals rendered in classic black-and-grey shading, approximately 8cm",
    "classic swallow in flight with spread wings and a forked tail, bold black outline, approximately 7cm",
    "ornate dagger pointing downward with a wrapped grip and a small banner crossing the blade, approximately 9cm",
    "traditional skull with a cracked dome, black eye sockets and a small rose growing from one socket, approximately 9cm",
    "panther head in profile with bared teeth, bold outline and classic whip-shade fur, approximately 9cm",
    "classic anchor with rope wrap, a small bow flag at the top, approximately 8cm",
    "lit candle with a wax drip down the side and a small flame, classic flash style, approximately 7cm",
    "traditional eagle head facing forward with feathered ruff and a sharp beak, bold outline, approximately 9cm",
    "classic lighthouse on a small rocky base with a beam of light, four spark dots at the edge, approximately 10cm",
    "traditional ship in full sail crossing a small wave, banner curling above with empty interior, approximately 11cm",
    "lucky horseshoe surrounded by a small clover and three star spurs, classic composition, approximately 8cm",
    "bleeding heart with a dagger through it and a small banner curling below, approximately 9cm",
    "classic hand of fate holding an eye, bold outline and limited grey shading, approximately 9cm",
    "traditional jaguar mid-pounce with claws extended and a curling tail, approximately 10cm",
    "classic owl perched on a key with both eyes facing forward, approximately 9cm",
    "lit cigarette in a holder with curling smoke trails forming a soft frame, approximately 9cm",
    "traditional hourglass with sand mid-fall and a small banner around the frame, approximately 8cm",
    "classic bear head with mouth open mid-roar, bold outline and whip shading, approximately 9cm",
    "traditional pin-up swallow with a tiny rose held in its beak, approximately 7cm",
    "classic broken-chain with a small flame between the links, approximately 8cm",
    "traditional snake coiled around a dagger with a small rose at the hilt, approximately 10cm",
    "classic chest of treasure half open with three coins spilling out, approximately 9cm",
    "traditional buffalo skull with feathered hangings on either horn, approximately 10cm",
    "classic lit oil lamp with a small wick flame and a curling smoke trail, approximately 8cm",
    "traditional rose around a horseshoe with three leaves at the base, approximately 9cm",
    "classic flying eye with feathered wings and a small tear, approximately 8cm",
    "traditional fox head winking with a tiny banner under the chin, approximately 8cm",
    "classic battle-axe crossed with a sword, banner above with empty interior, approximately 10cm",
    "bottle of poison with skull label, classic flash with stark shading, approximately 7cm",
    "classic mermaid in a seated pose with flowing hair and a small wave below, approximately 11cm",
]

MOTIFS_JAPANESE: list[str] = [
    "irezumi koi mid-leap upstream with detailed scales, water spray dots and three trailing wind bars, approximately 13cm",
    "Japanese dragon head with whiskers, fierce eye and a curl of smoke escaping the mouth, scaled body trailing into wind bars, approximately 14cm",
    "irezumi tiger crouched with bold stripe pattern and detailed paws gripping a small rock, approximately 13cm",
    "Japanese peony in full bloom with five layered petals and a curl of leaves, approximately 10cm",
    "cherry blossom branch with seven blooms in various stages and four falling petals nearby, approximately 12cm",
    "irezumi crane in flight with extended wings, head turned and trailing wind bars below, approximately 13cm",
    "Japanese wave fragment — one cresting wave with structured foam fingers and three spray dots, approximately 11cm",
    "chrysanthemum bloom in full layered detail with a curling leaf cluster, approximately 9cm",
    "hannya mask in profile with horns, bared teeth and detailed brow shading, approximately 10cm",
    "irezumi snake coiled around a single peony with strike-pose head, approximately 12cm",
    "Japanese phoenix mid-takeoff with extended wing feathers and a trailing tail, approximately 13cm",
    "samurai helmet in three-quarter view with detailed crest and side flaps, approximately 10cm",
    "irezumi tiger head in profile with bared teeth and a single bamboo stalk crossing the composition, approximately 11cm",
    "Japanese fan half-open with a painted wave scene inside and a tassel hanging below, approximately 10cm",
    "lotus flower rising from water with three lily pads and four water dots, approximately 11cm",
    "irezumi koi pair circling in a yin-yang composition, one black, one outline only, approximately 12cm",
    "Japanese dragon coiled around a flaming pearl with smoke trails fanning outward, approximately 14cm",
    "samurai sword in a sheath with cherry blossoms drifting around the hilt, approximately 12cm",
    "irezumi maple leaf cluster with three large leaves in autumn arrangement, approximately 9cm",
    "Japanese fox spirit (kitsune) in seated pose with three tails fanned behind, approximately 11cm",
    "irezumi crane and pine branch combination — symbol of long life, approximately 12cm",
    "Japanese demon mask oni in profile with single horn and bared teeth, approximately 10cm",
    "lotus and koi together — koi mid-leap toward an opening lotus bloom, approximately 12cm",
    "Japanese snake circling a sword with a single chrysanthemum at the guard, approximately 12cm",
    "irezumi tiger and dragon facing each other across a wind-bar gap, approximately 14cm",
    "Japanese wave with a single seabird flying above the crest, approximately 11cm",
    "Japanese peony and butterfly pairing — bloom on the left, butterfly drifting upward right, approximately 11cm",
    "Japanese phoenix mid-flight with cherry blossoms scattered along the wing path, approximately 13cm",
    "irezumi tiger paw print enlarged with stripe pattern around it, approximately 9cm",
    "Japanese hawk diving with extended talons and detailed feather rendering, approximately 12cm",
]

MOTIFS_REALISM: list[str] = [
    "photoreal rose in full bloom with deep petal shadows and dewdrops on two petals, approximately 9cm",
    "photoreal lion head facing forward with a full mane in detailed black-and-grey shading, approximately 10cm",
    "photoreal human eye with detailed iris pattern, lash detail and a single tear, approximately 7cm",
    "photoreal pocket watch hanging open with detailed gears, roman numerals and a slight chain trail, approximately 10cm",
    "photoreal wolf head in three-quarter view with intense eye contact and detailed fur direction, approximately 10cm",
    "photoreal compass with brass texture, detailed needle and a worn leather strap, approximately 9cm",
    "photoreal feather floating with detailed barb separation and a soft drop shadow, approximately 9cm",
    "photoreal skull with realistic bone texture, partial cracks and a single rose growing from an eye socket, approximately 11cm",
    "photoreal koi from above with detailed scales and a soft water-ripple ground, approximately 11cm",
    "photoreal tiger head close-up with detailed eye contact and stripe rhythm, approximately 11cm",
    "photoreal hourglass with sand mid-fall, detailed grain texture and a worn wooden frame, approximately 10cm",
    "photoreal hand reaching up holding a single rose, detailed knuckle shadow, approximately 11cm",
    "photoreal owl head with detailed feather rings around the eyes, approximately 10cm",
    "photoreal vintage camera with detailed lens reflections and a leather body, approximately 10cm",
    "photoreal elephant head in profile with detailed ear texture and a small tusk, approximately 11cm",
    "photoreal anatomical heart with detailed ventricle shading and a soft drop shadow, approximately 9cm",
    "photoreal raven perched on a branch with detailed feather rendering and a piercing eye, approximately 10cm",
    "photoreal moth with photographic wing-pattern detail and a soft body fuzz, approximately 9cm",
    "photoreal hand holding a lit match with realistic flame and a thin trail of smoke, approximately 10cm",
    "photoreal bear head with detailed snout fur and a calm forward gaze, approximately 11cm",
    "photoreal swan in profile with detailed neck-feather rendering and a soft eye, approximately 11cm",
    "photoreal stag head with detailed antler branching and a calm forward gaze, approximately 11cm",
    "photoreal sailing ship at sea with detailed sail folds and a small wake, approximately 12cm",
    "photoreal fox head with detailed snout fur and bright forward eyes, approximately 10cm",
    "photoreal candle flame with realistic glow falloff and a wax drip, approximately 8cm",
    "photoreal jellyfish with translucent bell shading and trailing tendrils, approximately 11cm",
    "photoreal dog portrait with attentive eyes and detailed ear fur, approximately 10cm",
    "photoreal vintage typewriter close-up with detailed key texture, approximately 10cm",
    "photoreal violin headstock close-up with detailed wood grain and tuning pegs, approximately 10cm",
    "photoreal hand holding a worn paper plane with detailed crease shadows, approximately 10cm",
]

MOTIFS_MINIMALIST: list[str] = [
    "single-line botanical sprig — three small leaves on a thin stem, approximately 4cm tall",
    "tiny continuous-line bird in flight, single stroke, approximately 3cm wide",
    "micro constellation of five dots connected by hair-thin lines, approximately 4cm",
    "single thin-line triangle outline, approximately 3cm",
    "tiny silhouette of a cat in profile, single weight outline, approximately 3cm",
    "single-line mountain — one continuous stroke for two peaks, approximately 5cm wide",
    "tiny crescent moon — clean thin arc, approximately 2cm",
    "thin arrow — slim shaft and small flared tip, approximately 4cm",
    "single small heart outline drawn as one continuous line, approximately 2.5cm",
    "tiny butterfly silhouette in single-weight outline, approximately 3cm",
    "single-line wave — one fluid stroke with two crests, approximately 5cm",
    "tiny anchor outline, single weight, approximately 3cm",
    "minimal sun — small circle with seven thin radiating lines, approximately 4cm",
    "single-line flower — continuous loop forming five petals, approximately 4cm",
    "tiny key silhouette in single-weight outline, approximately 3cm",
    "minimal dragonfly — symmetrical thin outline, approximately 4cm",
    "tiny seedling — two leaves and a single root line, approximately 3cm",
    "single-line fish — one continuous loop forming the body and tail, approximately 4cm",
    "minimal compass — small circle with cardinal cross inside, approximately 4cm",
    "tiny paper plane silhouette in single-weight outline, approximately 3cm",
    "single-line lightning bolt, sharp angles, approximately 4cm",
    "minimal feather — one stroke for the spine, six short marks for barbs, approximately 4cm",
    "tiny lotus outline — three layered petals in single weight, approximately 3.5cm",
    "minimal eye — almond outline with a single dot iris, approximately 3cm",
    "single-line cloud — one continuous loop, approximately 4cm",
    "tiny hot-air balloon outline with a small basket, approximately 4cm",
    "minimal infinity loop — single clean stroke, approximately 4cm",
    "single-line palm tree — trunk and three thin fronds, approximately 4cm",
    "tiny coffee cup with single steam curl, single weight, approximately 3cm",
    "minimal music note — single eighth-note in clean outline, approximately 3cm",
]

MOTIFS_GEOMETRIC: list[str] = [
    "geometric wolf head built from triangulated facets with subtle dotwork shading at vertices, approximately 9cm",
    "sacred geometry — flower of life fragment with seven nested circles in clean line, approximately 8cm",
    "geometric stag with triangulated antlers branching into a constellation of dots, approximately 10cm",
    "metatron's cube with precise nested platonic forms, approximately 8cm",
    "geometric fox head with angular faceted snout and dotwork eye, approximately 8cm",
    "geometric mandala — concentric rings divided into eight angular wedges, approximately 9cm",
    "geometric whale silhouette built from clean angular planes, approximately 10cm",
    "Sri Yantra precise triangulation pattern, approximately 8cm",
    "geometric mountain range with clean overlapping triangles and a single sun disc, approximately 10cm",
    "geometric horse head with faceted muzzle and triangulated mane, approximately 9cm",
    "geometric eye-of-providence — sharp triangle with dotwork iris and radiating rays, approximately 9cm",
    "geometric tree of life with angular branching and dotwork foliage clusters, approximately 11cm",
    "geometric lion head with faceted mane forming a starburst pattern, approximately 10cm",
    "geometric whale tail rising out of a clean triangular wave, approximately 9cm",
    "geometric ouroboros — hexagonal serpent biting its tail with internal lattice, approximately 9cm",
    "geometric crow head with angular faceted feathers and a dotwork eye, approximately 9cm",
    "platonic icosahedron with thin internal structure lines, approximately 7cm",
    "geometric dolphin mid-leap with faceted body and a clean triangular wave, approximately 9cm",
    "geometric phoenix with angular wing facets and dotwork feather tips, approximately 11cm",
    "geometric butterfly with mirrored faceted wings and a clean axis, approximately 8cm",
    "geometric snake coiled into a hexagonal frame with internal lattice, approximately 9cm",
    "geometric sun and moon overlap with clean radiating thin-line rays, approximately 9cm",
    "geometric elephant head with faceted ears and dotwork tusk highlights, approximately 10cm",
    "geometric labyrinth in a clean circular frame, single thin path, approximately 8cm",
    "geometric eagle head with sharp faceted beak and triangulated crest, approximately 9cm",
    "geometric dragonfly with mirrored faceted wings and a thin segmented body, approximately 8cm",
    "geometric compass rose with eight precise points and dotwork centre, approximately 8cm",
    "geometric bear head with faceted snout and triangulated ears, approximately 9cm",
    "geometric mandala with sacred geometry overlay — flower of life inside a clean octagon, approximately 9cm",
    "geometric scorpion with angular segments and dotwork tail tip, approximately 9cm",
]

MOTIFS_ORNAMENTAL: list[str] = [
    "ornamental medallion with concentric filigree rings and tiny teardrop chandelier drops, approximately 8cm",
    "baroque cartouche frame with empty interior and curling acanthus terminals, approximately 9cm",
    "ornamental crescent moon with chandelier drops hanging from each tip, approximately 9cm",
    "filigree pendant with a central rosette and bead-chain border, approximately 8cm",
    "ornamental band with paired filigree wings extending outward at each end, approximately 11cm",
    "baroque rosette medallion with eight petal sections and tiny fleur tips, approximately 8cm",
    "ornamental lace cuff fragment with openwork windows and bead trim, approximately 11cm",
    "filigree key in elaborate baroque style with a heart-shaped bow, approximately 8cm",
    "ornamental crown silhouette with filigree interior and tiny gem dots, approximately 9cm",
    "baroque mirror frame with a single hanging filigree drop, approximately 10cm",
    "ornamental anchor wrapped in filigree rope with bead detail along the shaft, approximately 9cm",
    "filigree heart with openwork lace interior and a small chandelier drop below, approximately 8cm",
    "ornamental peacock feather with elaborate filigree eye, approximately 11cm",
    "baroque scroll-frame with a small rose at the centre and curling acanthus ends, approximately 10cm",
    "ornamental hand of fatima with elaborate interior filigree and bead trim, approximately 9cm",
    "filigree butterfly with elaborate openwork wing patterns, approximately 9cm",
    "ornamental star with filigree rays and a central jewel dot, approximately 8cm",
    "baroque dagger with filigree handle and acanthus crossguard, approximately 10cm",
    "ornamental sun with filigree corona and bead-chain rays, approximately 9cm",
    "filigree bird in flight with openwork feather pattern, approximately 9cm",
    "ornamental rosette pendant with chandelier teardrop drops, approximately 9cm",
    "baroque crown of thorns with filigree weave and small bead accents, approximately 9cm",
    "ornamental mandala with filigree petals and bead-chain centre, approximately 9cm",
    "filigree lock-and-key pair with elaborate baroque ornament, approximately 9cm",
    "ornamental compass rose with filigree cardinal points and bead-chain ring, approximately 9cm",
    "baroque arch frame with filigree columns and a single hanging drop inside, approximately 10cm",
    "ornamental fan with openwork filigree pattern and a bead-trim border, approximately 9cm",
    "filigree owl perched with elaborate baroque feather pattern, approximately 9cm",
    "ornamental quiver of arrows with filigree shaft detailing and acanthus fletching, approximately 10cm",
    "baroque seal-style medallion with central rose and curling filigree border, approximately 9cm",
]


MOTIF_LIBRARY_BY_STYLE: dict[str, list[str]] = {
    "fine_line": MOTIFS_FINE_LINE,
    "blackwork": MOTIFS_BLACKWORK,
    "traditional": MOTIFS_TRADITIONAL,
    "japanese": MOTIFS_JAPANESE,
    "realism": MOTIFS_REALISM,
    "realistic": MOTIFS_REALISM,
    "minimalist": MOTIFS_MINIMALIST,
    "minimal": MOTIFS_MINIMALIST,
    "geometric": MOTIFS_GEOMETRIC,
    "ornamental": MOTIFS_ORNAMENTAL,
    "stencil": MOTIFS_BLACKWORK,
    "auto": MOTIFS_FINE_LINE + MOTIFS_TRADITIONAL + MOTIFS_BLACKWORK,
}


# ===========================================================================
# 6. THEME → CONCRETE MOTIF LIBRARIES
# ===========================================================================

THEME_MOTIFS: dict[str, list[str]] = {
    "strength": [
        "lion head facing forward with a powerful mane",
        "single mountain peak silhouette with three small stars above",
        "compact oak tree with deep roots showing below",
        "upward arrow split into three at the tip",
        "anchor with rope wrap and a tiny rose at the base",
        "bear head in profile with bared teeth",
        "ram skull with curved horns and small floral accent",
        "wolf head in profile with a single feather behind the ear",
        "spartan helmet in profile with crest detail",
        "bull skull with horned silhouette and a small flower at the brow",
        "phoenix mid-takeoff with a small flame trail",
        "rhinoceros silhouette with a small sun behind the horn",
        "fist closed around a single olive branch",
        "tower silhouette with a small flame inside the highest window",
        "single column with a small ivy vine wrapping the base",
    ],
    "faith": [
        "small cross with a thin halo behind it",
        "single dove in flight carrying an olive branch",
        "rosary loop forming a circle around a tiny cross",
        "praying hands with a small flame above the fingertips",
        "open Bible silhouette with no text, just page edges visible",
        "single olive branch curving into a small ring",
        "shepherd's crook with a tiny lamb at the base",
        "small chapel silhouette with one window and a cross on top",
        "candle flame inside a heart outline",
        "lotus flower opening upward with a small star above",
        "kneeling figure silhouette with hands clasped",
        "bird flying out of an open cage with a small cross beside it",
        "small ark silhouette resting on a wave with a dove above",
        "single feather descending with a small star above",
        "compass with the cardinal points replaced by tiny crosses",
    ],
    "patience": [
        "tortoise silhouette with a small flower on the shell",
        "hourglass with sand mid-fall and a tiny seed at the base",
        "single bamboo stalk with three new leaves",
        "koi swimming upstream with three small ripples",
        "lotus bud not yet open, with three layered petals",
        "tree growing through a stone, roots wrapping the rock",
        "snail with detailed shell and a tiny flower nearby",
        "owl perched in stillness with eyes closed",
        "spider in a delicate web with one dewdrop",
        "candle nearly burnt down with a steady flame",
        "single feather floating slowly with three small dots trailing",
        "stone stack of five balanced rocks",
        "tea cup with a single steam curl rising",
        "moth resting on a closed flower bud",
        "river stone with a tiny sprout growing from a crack",
    ],
    "rebirth": [
        "phoenix mid-rising from a small flame base",
        "butterfly emerging from an open chrysalis",
        "lotus in full bloom rising from a small wave line",
        "fern fiddlehead unfurling with three small leaves",
        "sunrise behind a single horizon line with three rays",
        "snake shedding its skin in a soft S-curve",
        "egg cracked open with a tiny flame inside",
        "tree stump with a single new shoot growing from the centre",
        "moon cycle of three phases — crescent, full, crescent",
        "seed splitting open with two new leaves emerging",
        "phoenix feather with a small flame at the tip",
        "small flame growing into a sapling above",
        "broken chain with a butterfly emerging from the middle",
        "ouroboros with a small lotus at the centre",
        "candle relighting from its own ember with a soft glow",
    ],
    "healing": [
        "lavender sprig with three flower clusters on a thin stem",
        "small heart with a kintsugi gold crack line through the centre",
        "eucalyptus branch with seven rounded leaves on a thin stem",
        "crescent moon with a single small star inside",
        "aloe vera leaf with a single dewdrop at the tip",
        "open palm with a small sprout growing from the centre",
        "anatomical heart with vines growing through the chambers",
        "single feather with a small heart at the base",
        "cup of tea with a single mint leaf and steam curl",
        "dove perched on a sprig of olive",
        "snake shedding skin with a small flower nearby",
        "sun rising behind a small wave with three rays",
        "candle burning with a small flame and a sprig of sage",
        "moth resting on a flower in soft bloom",
        "open book with a single pressed flower on the page",
    ],
    "love": [
        "two small intertwined hearts in continuous line",
        "infinity loop with a tiny heart at the crossing point",
        "single rose bud with petals just opening",
        "lock and key placed close together with a small heart between",
        "two small birds perched on a single branch facing each other",
        "anatomical heart with a single rose growing from the top",
        "two hands forming a heart silhouette",
        "moon with a small star nestled in its curve",
        "candle with two flames merging into one",
        "two koi forming a heart in their swim path",
        "single rose with two leaves and a tiny butterfly above",
        "two doves carrying a single ribbon between them",
        "small house with a heart in the window",
        "two hands clasped with a small flame above",
        "soft figure-eight forming around a tiny rose",
    ],
    "family": [
        "tree of life with a branching crown and a deep root base",
        "linked chain of three with a tiny heart in the middle link",
        "three birds in flight ascending together",
        "small house with smoke curling from the chimney",
        "roots spreading below a short trunk like an inverted crown",
        "three hands clasped in the centre",
        "compass with three small stars at three of the cardinal points",
        "open book with three small initials replaced by tiny floral symbols",
        "three candles burning together at varying heights",
        "single tree with three distinct branches each carrying a small leaf",
        "three small birds nesting in a circular nest",
        "trio of mountains with a small sun behind",
        "three hands stacked palms-up with a small flame above",
        "three small hearts on a single thin branch",
        "three feathers tied at the base with a thin ribbon",
    ],
    "discipline": [
        "compass rose with crisp cardinal marks and a small dot at centre",
        "katana sword in clean vertical orientation with a minimal guard",
        "chess knight piece in profile",
        "shield with a heraldic cross and a small star at the top",
        "hourglass with sand mid-fall and a slim wood frame",
        "spartan helmet in profile with crest detail",
        "samurai mask with detailed brow shading",
        "wolf head with a calm forward gaze",
        "open book with a feather quill resting across the spine",
        "burning candle inside a glass lantern",
        "bow and arrow drawn back and ready",
        "anvil with a small hammer resting on top",
        "single ladder rising into a small cloud",
        "anchor with rope wrap and a small star at the base",
        "stone column with a single ivy vine at the base",
    ],
    "freedom": [
        "single bird in flight with one wing arc silhouette, soaring upward",
        "dandelion with three seeds drifting in the wind",
        "single feather floating downward with detailed quill",
        "open birdcage with the door ajar and a small bird flying away",
        "two birds flying together away from a branch",
        "small hot-air balloon rising with three small clouds",
        "broken chain with a small bird flying from the middle",
        "kite with a thin tail catching wind",
        "small sailboat on a single wave line",
        "horse mid-gallop with a flowing mane",
        "open hand releasing three small butterflies",
        "single arrow flying upward with three soft motion lines",
        "small paper plane drifting with a thin trail",
        "wave breaking with a small bird flying above",
        "compass with the needle pointing toward a single star",
    ],
    "hope": [
        "small lighthouse with three light rays cutting the dark",
        "three small stars in a gentle arc",
        "single candle flame, upright and small",
        "tiny seedling with two leaves just emerged",
        "dove carrying an olive branch",
        "small sun rising behind a horizon line with three rays",
        "anchor with a small heart at the base",
        "open hand holding a single flame",
        "small sailboat heading toward a rising sun",
        "single key with a small star inside the bow",
        "small bridge crossing a thin stream with a sun above",
        "phoenix feather with a small flame at the tip",
        "small flame inside a glass lantern",
        "compass with the needle pointing to a small star",
        "small bird perched at the top of a thin branch",
    ],
    "peace": [
        "olive branch with seven leaves on a curved stem",
        "yin-yang circle in clean thin line",
        "lotus floating on a calm water line",
        "peace dove silhouette with wings spread",
        "single cloud outline soft and floating",
        "small mountain with a still moon above",
        "single feather drifting downward with three soft dots",
        "single candle with a steady flame",
        "two hands open palm-up with a small dove above",
        "small bird perched on a thin branch with a single leaf below",
        "single lotus with three layered petals",
        "small wave line with a single bird above",
        "small tea cup with a single mint leaf",
        "moon and star nestled in a soft cloud",
        "open hand releasing a small bird",
    ],
    "loss": [
        "willow branch with drooping thin fronds",
        "tiny forget-me-not flower",
        "single feather falling with three soft dots trailing",
        "small candle still burning, with a thin trail of smoke",
        "single angel wing in soft outline",
        "small empty chair with a single rose on the seat",
        "tree with one bare branch and one leafed branch",
        "small hourglass with sand all settled at the bottom",
        "single bird flying away from a small branch",
        "moon in waning crescent with three small stars",
        "small house with a single light in one window",
        "open hand releasing a small white flower",
        "small heart with a thin crack down the centre",
        "river stone with a single sprig of forget-me-not nearby",
        "single dove flying upward toward a small star",
    ],
    "philosophy": [
        "ouroboros — snake eating its tail in a compact circle",
        "open book with a small flame above the pages",
        "atom symbol with three orbiting rings",
        "Möbius strip in a continuous twisted loop",
        "small labyrinth circle with a spiral path inward",
        "compass with the needle pointing to a small flame",
        "small key with an eye inside the bow",
        "single tree with both roots and branches in equal balance",
        "single hand holding a small lit candle",
        "small mountain with a path winding to the peak",
        "open eye inside a triangular frame",
        "single feather and inkpot together",
        "scales of justice in clean thin line",
        "small flame inside a glass lantern",
        "small infinity loop wrapping a tiny star",
    ],
}


# ===========================================================================
# 6b. THEME COMBO LIBRARY
# Curated multi-theme subjects so multi-chip selections actually express
# both themes together (instead of picking one chip's motif at random).
# Lookup is order-independent (frozen set of two chip names).
# ===========================================================================

_THEME_COMBOS: dict[frozenset[str], list[str]] = {
    frozenset({"freedom", "love"}): [
        "two small birds in flight together carrying a single small heart between them",
        "open birdcage with two small birds flying out, one carrying a tiny rose",
        "single dove in flight cradling a small heart in its beak",
    ],
    frozenset({"freedom", "hope"}): [
        "single bird flying upward toward a small bright star",
        "small hot-air balloon rising with a tiny sun above the horizon",
        "open hand releasing a single butterfly toward a thin sunray",
    ],
    frozenset({"freedom", "strength"}): [
        "strong horse mid-gallop with a flowing mane heading toward an open horizon",
        "soaring eagle with extended wings cresting a single mountain peak",
        "broken chain with a single bird flying free from the middle",
    ],
    frozenset({"freedom", "peace"}): [
        "single dove in flight carrying a small olive branch",
        "open hand releasing a small bird above a tiny olive sprig",
        "soft cloud with a single bird flying out of it",
    ],
    frozenset({"strength", "family"}): [
        "single oak tree with three deep roots reaching down and three sturdy branches reaching up",
        "lion with two small cubs sheltered between its paws",
        "three mountain peaks side by side with one larger central peak",
    ],
    frozenset({"strength", "faith"}): [
        "lion head facing forward with a small cross resting at its brow",
        "single mountain peak with a small cross at the summit",
        "anchor wrapped in a thin rosary loop",
    ],
    frozenset({"strength", "rebirth"}): [
        "phoenix mid-rising with strong outstretched wings from a small flame base",
        "lion shedding old fur with a tiny new flame at its chest",
        "tree split open with a strong young shoot growing from the centre",
    ],
    frozenset({"hope", "faith"}): [
        "small candle flame with a tiny cross at its base",
        "single dove descending toward a small lit candle",
        "rising sun behind a small cross silhouette",
    ],
    frozenset({"hope", "healing"}): [
        "single sprout growing from a small stone with a tiny sun above",
        "small candle burning quietly with a single sprig of sage beside it",
        "lavender sprig with a small sun rising behind",
    ],
    frozenset({"hope", "rebirth"}): [
        "phoenix feather with a small flame at the tip and a tiny sun above",
        "tree stump with a fresh new shoot growing toward a small sun",
        "egg cracked open with a small sprout rising and a tiny star above",
    ],
    frozenset({"love", "family"}): [
        "three small hearts on a single thin branch",
        "small house with a heart in the window and smoke curling from the chimney",
        "three hands clasped together with a tiny heart at the centre",
    ],
    frozenset({"love", "loss"}): [
        "single rose with one petal falling, a small heart at the base",
        "willow branch with a single heart hanging from a thin stem",
        "small empty chair with a single rose on the seat and a thin heart outline above",
    ],
    frozenset({"love", "healing"}): [
        "anatomical heart with vines and a single small flower growing from the top",
        "small heart with a kintsugi gold crack and a tiny sprout rising from the seam",
        "open hand cradling a single rosebud",
    ],
    frozenset({"peace", "patience"}): [
        "single lotus floating on a calm water line with a slow ripple",
        "tortoise silhouette with a small olive sprig on the shell",
        "bamboo stalk with a single still moon above",
    ],
    frozenset({"peace", "faith"}): [
        "olive branch curving into a small ring with a tiny cross at the centre",
        "single dove in flight carrying a small cross",
        "calm water line with a small lotus and a tiny cross above",
    ],
    frozenset({"loss", "rebirth"}): [
        "willow branch with a single new shoot growing from a broken stem",
        "moon waning to crescent with a tiny seedling rising below",
        "single feather descending with a small flame catching at its tip",
    ],
    frozenset({"loss", "love"}): [
        "single dove flying upward toward a small heart-shaped cloud",
        "small heart with a thin willow branch curving around it",
        "single rose with a forget-me-not at the base",
    ],
    frozenset({"discipline", "strength"}): [
        "katana sword crossed with a single feather",
        "bow drawn back with a single arrow aimed at a small star",
        "anvil with a small hammer resting on top and a tiny flame inside",
    ],
    frozenset({"philosophy", "peace"}): [
        "ouroboros with a small lotus at the centre",
        "single tree with balanced roots and branches and a small still moon above",
        "Möbius strip with a tiny olive leaf at one curve",
    ],
    frozenset({"philosophy", "freedom"}): [
        "open book with a single bird flying up from the pages",
        "small labyrinth circle with a tiny bird at its centre",
        "compass needle pointing toward a single star and a small open cage below",
    ],
}


def _combine_theme_chips(chips: list[str]) -> Optional[str]:
    """Try to find a curated combo motif for the user's chosen chips."""
    if len(chips) < 2:
        return None
    norm = [c.strip().lower() for c in chips if c and c.strip()]
    # Try every pair (most combos are 2-chip)
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            key = frozenset({norm[i], norm[j]})
            if key in _THEME_COMBOS:
                return _pick(_THEME_COMBOS[key])
    return None


# ===========================================================================
# 7. STYLE RESOLVER (smart fallback so 'auto' becomes a real style)
# ===========================================================================

_DIRECTION_STYLE_BIAS: dict[str, list[str]] = {
    "meaningful": ["fine_line", "ornamental", "blackwork", "traditional"],
    "aesthetic": ["fine_line", "ornamental", "japanese", "geometric"],
    "bold_statement": ["blackwork", "traditional", "japanese", "geometric"],
    "unsure": ["fine_line", "minimalist", "traditional", "blackwork"],
}

_LOOK_STYLE_BIAS: dict[str, list[str]] = {
    "subtle": ["fine_line", "ornamental", "realism", "minimalist"],
    "balanced": ["fine_line", "ornamental", "geometric", "japanese", "traditional"],
    "bold": ["blackwork", "traditional", "japanese", "geometric"],
}

# deep_meaning expression → preferred style ordering
_EXPRESSION_STYLE_BIAS: dict[str, list[str]] = {
    "elegant_subtle": ["fine_line", "ornamental", "realism", "minimalist"],
    "deep_symbolic": ["ornamental", "geometric", "fine_line", "blackwork"],
    "bold_powerful": ["blackwork", "traditional", "japanese"],
    "poetic": ["fine_line", "ornamental", "script"],
    "spiritual": ["ornamental", "geometric", "fine_line"],
}


def resolve_style(flow_id: str, answers: dict[str, Any]) -> str:
    """
    Pick a canonical STYLE_DESCRIPTORS key from soft inputs.
    Explicit user choice (with alias normalisation) always wins when valid.
    """
    raw = str(answers.get("style") or answers.get("conversion_style") or "").strip()
    explicit = _normalize_style(raw) if raw else ""
    if explicit and explicit in STYLE_DESCRIPTORS and explicit != "auto":
        return explicit

    if flow_id == "new_to_tattoos":
        direction = str(answers.get("tattoo_goal") or "unsure").lower()
        look = str(answers.get("look") or "balanced").lower()
        dir_bias = _DIRECTION_STYLE_BIAS.get(direction, _DIRECTION_STYLE_BIAS["unsure"])
        look_bias = _LOOK_STYLE_BIAS.get(look, _LOOK_STYLE_BIAS["balanced"])
        for s in dir_bias:
            if s in look_bias:
                return s
        return dir_bias[0]

    if flow_id == "deep_meaning":
        form = str(answers.get("form") or "symbol").lower()
        visibility = str(answers.get("visibility") or "balanced").lower()
        expression = str(answers.get("expression") or "").lower()

        if form == "script":
            return "script"

        # expression takes priority when present (it's the most direct signal)
        if expression in _EXPRESSION_STYLE_BIAS:
            bias = _EXPRESSION_STYLE_BIAS[expression]
            # narrow by visibility within the expression bias
            if visibility == "quiet":
                quiet_set = {"fine_line", "minimalist", "ornamental", "script"}
                for s in bias:
                    if s in quiet_set:
                        return s
            if visibility == "visible":
                visible_set = {"blackwork", "traditional", "japanese", "realism"}
                for s in bias:
                    if s in visible_set:
                        return s
            return bias[0]

        # fallback: visibility-only path
        if visibility == "quiet":
            return random.choice(["fine_line", "minimalist", "ornamental"])
        if visibility == "visible":
            return random.choice(["blackwork", "traditional", "japanese"])
        return random.choice(["fine_line", "ornamental", "geometric"])

    if flow_id == "from_idea":
        return explicit if explicit in STYLE_DESCRIPTORS else "auto"

    if flow_id == "photo_convert":
        return explicit if explicit in STYLE_DESCRIPTORS else "fine_line"

    return "fine_line"


# ===========================================================================
# 8. SIZE BLOCK + INTENSITY MODIFIER
#    (size is the single biggest reason the model produces sleeves when the
#     user asked for a small piece — it must be loud, concrete, and EARLY)
# ===========================================================================

# (style, coverage) -> (size_label, longest_dim_cm_range, bare_skin_pct, visual_anchor)
# visual_anchor is a concrete relatable size the model understands far better
# than abstract centimeters (e.g. "the size of a credit card").
_SIZE_TABLE: dict[tuple[str, str], tuple[str, str, str, str]] = {
    # minimalist — ALWAYS very small. Style is meaningless otherwise.
    ("minimalist", "small"):  ("TINY",   "2 to 4 cm",   "95%", "the size of a coin"),
    ("minimalist", "medium"): ("TINY",   "3 to 5 cm",   "93%", "the size of a thumbprint"),
    ("minimalist", "large"):  ("SMALL",  "4 to 6 cm",   "90%", "the size of a thumb"),

    ("fine_line", "small"):   ("SMALL",  "3 to 6 cm",   "90%", "the size of a thumb"),
    ("fine_line", "medium"):  ("MEDIUM", "7 to 11 cm",  "72%", "roughly the length of a credit card"),
    ("fine_line", "large"):   ("LARGE",  "12 to 17 cm", "55%", "roughly the size of a smartphone"),

    ("ornamental", "small"):  ("SMALL",  "4 to 7 cm",   "85%", "the size of a small pendant"),
    ("ornamental", "medium"): ("MEDIUM", "8 to 13 cm",  "65%", "the size of a credit card"),
    ("ornamental", "large"):  ("LARGE",  "14 to 20 cm", "50%", "roughly the size of a smartphone"),

    ("script", "small"):      ("SMALL",  "3 to 6 cm",   "90%", "single short word, the length of a thumb"),
    ("script", "medium"):     ("MEDIUM", "7 to 12 cm",  "72%", "short phrase, the length of a credit card"),
    ("script", "large"):      ("LARGE",  "13 to 18 cm", "55%", "longer phrase, the length of a smartphone"),

    ("geometric", "small"):   ("SMALL",  "4 to 7 cm",   "85%", "the size of a small pendant"),
    ("geometric", "medium"):  ("MEDIUM", "8 to 13 cm",  "62%", "the size of a credit card"),
    ("geometric", "large"):   ("LARGE",  "14 to 20 cm", "45%", "roughly the size of a smartphone"),

    ("traditional", "small"): ("SMALL",  "5 to 8 cm",   "82%", "the size of a small pendant"),
    ("traditional", "medium"):("MEDIUM", "9 to 14 cm",  "58%", "the size of a credit card"),
    ("traditional", "large"): ("LARGE",  "15 to 22 cm", "35%", "roughly the size of a smartphone"),

    ("blackwork", "small"):   ("SMALL",  "5 to 8 cm",   "78%", "the size of a small pendant"),
    ("blackwork", "medium"):  ("MEDIUM", "9 to 15 cm",  "55%", "the size of a credit card"),
    ("blackwork", "large"):   ("LARGE",  "16 to 24 cm", "30%", "roughly the size of a smartphone"),

    ("japanese", "small"):    ("SMALL",  "7 to 11 cm",  "70%", "roughly the length of a credit card"),
    ("japanese", "medium"):   ("MEDIUM", "12 to 18 cm", "42%", "roughly the size of a smartphone"),
    ("japanese", "large"):    ("LARGE",  "19 to 28 cm", "20%", "covering most of the body area"),

    ("realism", "small"):     ("SMALL",  "5 to 9 cm",   "78%", "the size of a small pendant"),
    ("realism", "medium"):    ("MEDIUM", "10 to 16 cm", "52%", "the size of a credit card"),
    ("realism", "large"):     ("LARGE",  "17 to 24 cm", "30%", "roughly the size of a smartphone"),

    ("auto", "small"):        ("SMALL",  "4 to 7 cm",   "85%", "the size of a small pendant"),
    ("auto", "medium"):       ("MEDIUM", "8 to 13 cm",  "62%", "the size of a credit card"),
    ("auto", "large"):        ("LARGE",  "14 to 22 cm", "40%", "roughly the size of a smartphone"),

    ("stencil", "small"):     ("SMALL",  "4 to 7 cm",   "85%", "the size of a small pendant"),
    ("stencil", "medium"):    ("MEDIUM", "8 to 13 cm",  "65%", "the size of a credit card"),
    ("stencil", "large"):     ("LARGE",  "14 to 20 cm", "45%", "roughly the size of a smartphone"),
}


def _size_block(style: str, coverage: str, strength: str = "") -> tuple[str, str]:
    """
    Returns (size_block_text, visual_anchor_phrase).

    Loud only when SMALL — medium/large get a softer paragraph because
    constraining them too hard kills bigger pieces (sleeves, full-back,
    chest pieces) that are SUPPOSED to fill the visible skin.

    Strength is NEVER used to shrink coverage. Strength controls line
    weight / shading intensity (handled by intensity_modifier), not size.
    """
    style = (style or "auto").lower()
    cov = (coverage or "medium").lower().strip()
    if cov not in ("small", "medium", "large"):
        cov = "medium"

    # Minimalist is the only style where size is locked — large is a
    # contradiction with the style itself, so silently downgrade.
    if style == "minimalist" and cov == "large":
        cov = "medium"

    label, dim_range, bare_pct, visual_anchor = _SIZE_TABLE.get(
        (style, cov), _SIZE_TABLE[("auto", cov)]
    )

    if cov == "small":
        block = (
            f"SIZE (CRITICAL — THIS IS THE MOST IMPORTANT RULE):\n"
            f"- The tattoo is {label} — {visual_anchor}.\n"
            f"- Longest dimension: {dim_range}. NOTHING LARGER.\n"
            f"- Keep it as ONE coherent piece in a single area of skin.\n"
            f"- Leave generous surrounding bare skin (about {bare_pct}).\n"
            f"- Not a sleeve or full-limb composition — keep focus on one refined, readable tattoo."
        )
    else:
        # Medium / large: state the intended scale without crushing the model.
        block = (
            f"SIZE: {label} tattoo — {visual_anchor}, roughly {dim_range} in its longest dimension. "
            f"This is a single committed piece, not a tiny accent."
        )
    return block, visual_anchor


def intensity_modifier(coverage: str, strength: str) -> str:
    """Soft styling note appended below the style descriptor — size handled in _size_block."""
    stren = (strength or "").lower().strip()
    if stren == "subtle":
        return (
            "INTENSITY: subtle and understated — finer lines and lighter shading, "
            "but still clearly readable as a professional tattoo (not faint, not washed out)."
        )
    if stren == "bold":
        return (
            "INTENSITY: confident and present — stronger weight, richer blacks "
            "where the style allows, but still respecting the SIZE block above."
        )
    return ""


# ===========================================================================
# 8b. UNIQUENESS LOCK
#    (force custom composition choices so repeated generations don't collapse
#     to the same generic tattoo icon)
# ===========================================================================

_UNIQUE_COMPOSITION_CUES: dict[str, list[str]] = {
    "fine_line": [
        "offset the focal slightly from center and use one intentional flow direction through the form",
        "use a clean primary silhouette with one subtle asymmetry so it reads custom, not template",
        "compose as a single elegant motif with one supporting contour that balances negative space",
    ],
    "minimalist": [
        "keep one clear hero stroke and one secondary accent rhythm — avoid default icon symmetry",
        "retain minimalism but use a custom silhouette edge that feels hand-composed",
        "single compact motif with one distinctive directional gesture",
    ],
    "ornamental": [
        "vary filigree density between two zones so the piece reads bespoke instead of mirrored stock",
        "use one clear ornamental spine and asymmetric terminal flourishes",
        "compose ornament around a unique central negative-space shape",
    ],
    "geometric": [
        "introduce one controlled geometric offset (axis shift or ring interruption) for uniqueness",
        "keep strict geometry but vary hierarchy between primary and secondary forms",
        "use one dominant geometric mass with a deliberate counterbalance element",
    ],
    "traditional": [
        "use one classic hero motif with a custom supporting accent, not standard flash stacking",
        "slightly vary proportion rhythm so the silhouette is not a stock flash clone",
        "compose as one unified flash-style piece with distinctive focal hierarchy",
    ],
    "blackwork": [
        "use unique negative-space carving pattern so the silhouette is recognizably custom",
        "balance one dense black mass against one deliberate skin window region",
        "create a single dominant black form with a non-generic edge rhythm",
    ],
    "japanese": [
        "drive one clear directional flow and avoid symmetrical sticker composition",
        "use one dominant movement curve with supporting secondary rhythm",
        "compose with classic irezumi flow but a unique silhouette break",
    ],
    "realism": [
        "anchor realism with one dominant light direction and one distinctive edge-fade pattern",
        "use realistic depth hierarchy so one focal zone leads and secondary zones fall back naturally",
        "compose as a custom portrait/object crop with non-generic framing",
    ],
    "script": [
        "use natural lettering rhythm with a custom baseline flow tuned to anatomy",
        "maintain readability while giving letter connections a hand-drawn cadence",
        "use one dominant word rhythm and subtle weight contrast for custom calligraphy feel",
    ],
    "stencil": [
        "keep one clear hero outline with a custom silhouette break, not stock icon tracing",
        "use confident contour hierarchy so the stencil reads as an original drawing",
        "compose outline flow with one dominant directional gesture",
    ],
    "auto": [
        "pick one committed style and compose a custom focal hierarchy, not a generic icon",
        "use one dominant motif and one subtle supporting rhythm for originality",
        "ensure silhouette reads as bespoke tattoo art, not stock flash",
    ],
}

_UNIQUE_DETAIL_CUES: list[str] = [
    "line-weight rhythm should feel human and intentional, never perfectly uniform vector lines",
    "add one subtle micro-detail cluster near the focal zone to increase custom feel",
    "preserve crisp readability while avoiding over-simplified emoji-like shape language",
    "keep negative space intentional and shaped, not accidental empty gaps",
    "make the silhouette instantly readable from a distance but distinctive up close",
]


def _uniqueness_block(style: str, flow_id: str) -> str:
    style_key = (style or "auto").lower().strip()
    cues = _UNIQUE_COMPOSITION_CUES.get(style_key, _UNIQUE_COMPOSITION_CUES["auto"])
    comp_cue = _pick(cues)
    detail_cue = _pick(_UNIQUE_DETAIL_CUES)

    flow_line = ""
    if flow_id == "from_idea":
        flow_line = (
            "- Treat the SUBJECT as client-specific art direction; do not replace it with common flash defaults."
        )
    elif flow_id == "new_to_tattoos":
        flow_line = (
            "- Reflect the selected direction/themes through imagery choices so this output is unique to this user."
        )
    elif flow_id == "deep_meaning":
        flow_line = (
            "- Express the chosen meaning with a personal symbolic composition, not a generic reusable icon."
        )

    lines = [
        "ORIGINALITY LOCK:",
        "- This must be an original custom tattoo composition, not a stock flash clone.",
        f"- Composition cue: {comp_cue}.",
        f"- Detail cue: {detail_cue}.",
    ]
    if flow_line:
        lines.append(flow_line)
    lines.append("- Keep realism exact: healed ink integrated into real skin texture and lighting.")
    return "\n".join(lines)


# ===========================================================================
# 9. FOCAL SUBJECT BUILDER PER FLOW
# ===========================================================================

def _clip(text: str, max_len: int = 600) -> str:
    t = (text or "").strip()
    return t if len(t) <= max_len else t[: max_len - 3] + "..."


_variant_rng: Optional[random.Random] = None
_variant_index_global: int = 0
_variant_pick_count: int = 0
_variant_run_salt: int = 0


def _pick(items: list[str]) -> str:
    """
    Variant-aware pick. The FIRST pick in each prompt build is the subject
    motif — we rotate that deterministically by (variant_index + run_salt)
    so that:
      - variants 0/1/2 within the same request land on three different motifs
        (fixes the 'same cross, same bird' repetition within a generation),
      - two separate runs of the same answers land on a different starting
        motif each time (fixes the 'every run = same lion / same dragon /
        same heart' repetition across generations).
    Subsequent picks use the per-variant RNG so compositional details
    still vary between variants.
    """
    global _variant_pick_count
    if not items:
        return ""
    if _variant_rng is not None:
        if _variant_pick_count == 0 and len(items) > 1:
            _variant_pick_count += 1
            offset = (_variant_index_global + _variant_run_salt) % len(items)
            return items[offset]
        _variant_pick_count += 1
        return _variant_rng.choice(items)
    return random.choice(items)


def _focal_for_flow(
    flow_id: str,
    answers: dict[str, Any],
    style: str,
) -> tuple[str, str]:
    """
    Returns (focal_subject_text, optional_extra_note).
    """
    library = MOTIF_LIBRARY_BY_STYLE.get(style, MOTIFS_FINE_LINE)

    # ---- from_idea: user-provided text IS the subject ----
    if flow_id == "from_idea":
        idea = _clip(str(answers.get("idea") or "").strip(), 400)
        notes = _clip(str(answers.get("style_notes") or "").strip(), 300)
        if not idea:
            idea = _pick(library)
        extra = f"Client's specific style notes (must follow): {notes}" if notes else ""
        return idea, extra

    # ---- new_to_tattoos: theme chips → curated combo first, fallback to single-theme motif ----
    if flow_id == "new_to_tattoos":
        chips = answers.get("meaning_chips") or []
        if isinstance(chips, str):
            chips = [c.strip() for c in chips.split(",") if c.strip()]
        chips = [str(c).strip().lower() for c in chips if c]

        combo = _combine_theme_chips(chips) if chips else None
        if combo:
            theme_str = " + ".join(chips[:3])
            note = (
                f"(This single tattoo deliberately expresses the themes: {theme_str}. "
                f"All elements above are part of one unified design that says these themes together. "
                f"Do NOT write the theme words anywhere — express them only through the imagery.)"
            )
            return combo, note

        # No curated pair found: synthesize a dual-theme focal so selected
        # chips still visibly shape one unique composition.
        if len(chips) >= 2:
            c1 = chips[0]
            c2 = chips[1]
            m1_lib = THEME_MOTIFS.get(c1, [])
            m2_lib = THEME_MOTIFS.get(c2, [])
            if m1_lib and m2_lib:
                m1 = _strip_size_hints(_pick(m1_lib))
                m2 = _strip_size_hints(_pick(m2_lib))
                merged = (
                    f"single unified composition combining {m1} integrated with {m2}, "
                    f"composed as one tattoo (not two separate stickers)"
                )
                chip_str = ", ".join(chips[:6])
                return merged, (
                    f"(This design deliberately combines the selected themes: {chip_str}. "
                    f"Fuse both ideas into one cohesive tattoo, not separate icons. "
                    f"Do NOT write theme words as text anywhere.)"
                )

        candidates: list[str] = []
        for chip in chips:
            candidates.extend(THEME_MOTIFS.get(chip, []))
        if not candidates:
            candidates = library
        chosen = _pick(candidates)
        chip_str = ", ".join(chips[:6]) if chips else "personal meaning"
        primary_chip = chips[0] if chips else "personal meaning"
        return chosen, (
            f"(This design represents the theme '{primary_chip}'. "
            f"Selected themes from the client: {chip_str}. "
            f"Express the meaning visually through the imagery above — do NOT write theme words as text anywhere.)"
        )

    # ---- deep_meaning ----
    if flow_id == "deep_meaning":
        theme = str(answers.get("meaning_theme") or "").lower()
        form = str(answers.get("form") or "symbol").lower()
        sq = _clip(str(answers.get("script_quote") or ""), 200)
        theme_lib = THEME_MOTIFS.get(theme, [])
        chosen = _pick(theme_lib) if theme_lib else _pick(library)
        if form == "script" and sq:
            return f'EXACT lettering: "{sq}". Render exactly these characters, nothing else.', ""
        if form == "symbol_script" and sq:
            return f'PRIMARY symbol: {chosen}. ACCOMPANYING small lettering near base: "{sq}".', ""
        if form == "abstract":
            return f"abstract form expressing {theme or 'the chosen theme'} — flowing organic or geometric forms, intentional, no literal objects", ""
        return chosen, ""

    # ---- photo_convert (text fallback only — reference image takes a different path) ----
    if flow_id == "photo_convert":
        subj = _clip(str(answers.get("photo_subject") or "").strip(), 300)
        if not subj:
            subj = _pick(library)
        return subj, ""

    return _pick(library), ""


# ===========================================================================
# 10. PROMPT BUILDERS
# ===========================================================================

def _is_small_path(coverage: str, strength: str) -> bool:
    """Strength does NOT count toward small — it only controls line weight."""
    return (coverage or "medium").lower().strip() == "small"


def _build_subject_prompt(
    style: str,
    region_key: str,
    flow_id: str,
    focal_subject: str,
    extra_note: str,
    intensity_note: str,
    coverage: str,
    strength: str,
    allow_text_in_design: bool = False,
) -> str:
    """Standard prompt for new_to_tattoos / from_idea / deep_meaning / photo_convert (no reference)."""
    style_descriptor = STYLE_DESCRIPTORS.get(style, STYLE_DESCRIPTORS["auto"])
    intent = _pick(STYLE_INTENTS.get(style, STYLE_INTENTS["auto"]))
    region_text = REGION_ANATOMY.get(region_key, REGION_ANATOMY["other"])
    size_block, _anchor = _size_block(style, coverage, strength)
    focal_subject = _strip_size_hints(focal_subject)

    is_small = _is_small_path(coverage, strength)
    if is_small:
        # NOTE: We deliberately DO NOT chop accessory clauses from the focal
        # subject — multi-theme combos like "two birds carrying a heart"
        # only express both themes via the full phrase. Tightness comes from
        # the narrow placement + size block + "rest stays bare" rule below.
        narrow = _NARROW_PLACEMENT.get(region_key, _NARROW_PLACEMENT["other"])
        placement_line = f"PLACEMENT — {narrow}"
    else:
        placement_line = f"PLACEMENT — {region_text}"

    if allow_text_in_design:
        text_rule = (
            "TEXT IN DESIGN: ONLY the exact lettering specified in the SUBJECT block above. "
            "No other letters, words or numbers anywhere else in the design."
        )
        text_failure = (
            "- DO add the lettering specified in the SUBJECT block, rendered as real tattoo ink. "
            "Do NOT add any extra text beyond what is specified."
        )
    else:
        text_rule = NO_TEXT_RULE
        text_failure = (
            "- DO NOT add any text, letters, numbers, or letter-like marks anywhere in the design."
        )

    # Opening line differs for small (strict "leave the rest alone") vs
    # medium/large (let the model commit to a real piece).
    if is_small:
        opening = (
            "EDIT this photograph. Add ONE single professional tattoo. Keep everything else "
            "in the photo IDENTICAL — same body, same skin, same clothing, same background, "
            "same lighting. The only change is the new tattoo."
        )
    else:
        opening = f"EDIT this photograph. Add ONE professional tattoo on the {region_text}"

    parts = [
        opening,
        "",
        placement_line,
        "",
        size_block,
        "",
        text_rule,
        "",
        "SUBJECT — draw EXACTLY this (do NOT replace with a generic flash motif):",
        focal_subject,
    ]
    if extra_note:
        parts.append(extra_note)
    parts += [
        "",
        "STYLE — render as:",
        style_descriptor,
        intent,
    ]
    if intensity_note:
        parts.append(intensity_note)
    parts += [
        "",
        _uniqueness_block(style, flow_id),
        "",
        REALISM_BLOCK,
        "",
        "CRITICAL FAILURE MODES TO AVOID:",
        text_failure,
        "- DO NOT make the lines look like a pencil or pen sketch — these are real healed tattoo ink in the skin.",
        "- DO NOT replace the requested subject with a generic flash motif. Draw the subject above.",
    ]
    if is_small:
        # Small-only constraints — without these, small reverts to medium.
        parts += [
            "- Keep this as one compact tattoo, not a sleeve or full-limb spread.",
            "- Avoid generic clip-art simplification; preserve distinctive details from the SUBJECT block.",
            "- Keep surrounding skin mostly bare while maintaining clear readability of the tattoo.",
        ]
    parts += ["", CRITICAL_CLOSER]
    return "\n".join(parts).strip()


# Per-variant variation for photo_convert. Earlier I varied pose/angle
# (head-on, three-quarter, side profile) but that forced the model to
# DEVIATE from the reference pose, which broke fidelity. Now we only
# vary render/framing details that leave the subject's pose intact.
_PHOTO_CONVERT_VARIATIONS = [
    "Variation: clean contour-first rendering, no extra elements around the subject.",
    "Variation: contour + sparse interior line accents only, no background embellishments.",
    "Variation: contour + subtle grey tattoo wash inside form shadows only, no decorative frame.",
    "Variation: contour + tiny controlled dot-shading in shadow pockets only, no extra motifs.",
]

_PHOTO_CONVERT_STYLE_LOCK: dict[str, str] = {
    "fine_line": (
        "RENDER LOCK: black/grey tattoo ink only, no full-colour fill. "
        "Use clean single-needle contour + sparse interior line detail. "
        "If tone is needed, use only very light grey wash."
    ),
    "minimalist": (
        "RENDER LOCK: black tattoo ink only, ultra-minimal lines, no colour, no dense shading, no decorative photo texture."
    ),
    "blackwork": (
        "RENDER LOCK: pure black tattoo ink only. Solid blacks only inside the tattoo silhouette, no grey photo texture transfer."
    ),
    "traditional": (
        "RENDER LOCK: tattoo flash rendering, not photo rendering. "
        "No natural photo colours copied from image 2. Prefer black/grey tattoo ink values."
    ),
    "japanese": (
        "RENDER LOCK: irezumi line and grey-value rendering, not photographic texture transfer. "
        "No natural photo colours copied from image 2."
    ),
    "realism": (
        "RENDER LOCK: black-and-grey realism tattoo only (NO full colour). "
        "Translate photo features into tattoo tonal values and controlled edges."
    ),
    "geometric": (
        "RENDER LOCK: clean black/grey geometric tattoo linework only, no photo texture, no natural colour carry-over."
    ),
    "ornamental": (
        "RENDER LOCK: ornamental black/grey tattoo linework only, no photo texture, no natural colour carry-over."
    ),
    "script": (
        "RENDER LOCK: black tattoo lettering/linework only, no colour fill, no photo texture transfer."
    ),
    "stencil": (
        "RENDER LOCK: stencil-like black outline tattoo only, hollow interiors, no colour and no photo texture transfer."
    ),
    "auto": (
        "RENDER LOCK: convert image 2 into tattoo ink rendering (black/grey), not a photographic copy."
    ),
}


def build_photo_convert_stencil_prompt(style: str) -> str:
    """
    Generate a LARGE, BOLD, ARTISTIC, BEAUTIFUL professional tattoo stencil.
    Focus on refined artistry, elegance, and refined beauty.
    """
    s = (style or "fine_line").lower().strip()
    style_note = {
        "fine_line": "Bold artistic single-needle linework with refined confidence, beautiful shading, and elegant detail.",
        "minimalist": "Bold minimal artistic linework with refined definition, high contrast, and elegant confident strokes.",
        "blackwork": "HEAVY BOLD artistic solid black masses with powerful dramatic negative-space contrast and beautiful impact.",
        "realism": "Bold beautiful artistic black-and-grey with refined dramatic shading and elegant tonal gradients.",
        "traditional": "Bold classic beautiful tattoo flash with thick confident refined strokes, strong artistic presence, and timeless beauty.",
        "japanese": "Strong bold artistic outline with beautiful elegant grey fills and high visibility with refined traditional flair.",
        "geometric": "Bold artistic precise geometric forms with thick clean elegant lines and beautiful dramatic definition.",
        "ornamental": "BOLD artistic beautiful filigree with thick elegant teardrop elements and refined elaborate flourishes.",
        "script": "Bold artistic beautiful hand-lettered script with thick elegant weight, strong refined presence, and calligraphic artistry.",
        "stencil": "THICK crisp elegant outline, bold artistic interiors, beautiful high dramatic contrast.",
        "auto": "Bold artistic beautiful professional tattoo linework with strong refined artistic presence.",
    }.get(s, "Bold artistic beautiful professional tattoo linework.")

    return (
        "Create a LARGE, BOLD, PROMINENT, BEAUTIFUL, ARTISTIC professional tattoo stencil with THICK visible elegant lines.\n"
        "CRITICAL: This stencil MUST be rendered in ONLY the {style.upper()} style — NOT a generic style. Apply the specific characteristics strongly.\n"
        "\n"
        "PART 1 — SUBJECT (upper, LARGE & BEAUTIFUL): Convert this image's subject into a LARGE, BOLD, BEAUTIFUL, ARTISTIC tattoo linework in the {style} style. "
        "HEAVY ink density — lines must be PROMINENT, CLEARLY VISIBLE, DOMINATE the space, and be BEAUTIFUL. "
        "Include full beautiful artistic detail — fur texture with VISIBLE elegant ARTISTIC LINE WORK, eye definition with BEAUTIFUL ARTISTIC DEPTH and LIFE, mouth expression with REFINED PERSONALITY, whiskers with PROMINENT BEAUTIFUL ARTISTIC LINES. "
        "Make it BEAUTIFUL, ARTISTIC, EXPRESSIVE, and IMPACTFUL with REFINED elegance. "
        "NOT a bare outline. BOLD beautiful artistic shading and texture with HIGH CONTRAST and BEAUTIFUL ARTISTIC PRESENCE.\n"
        "\n"
        "PART 2 — ORNAMENT (lower, LARGE & BEAUTIFUL): Create a LARGE, ELABORATE, BOLD, BEAUTIFUL ornamental design below the subject with THICK BEAUTIFUL ARTISTIC LINES in the {style} style. "
        "Baroque scrollwork, intricate beautiful filigree patterns, elegant teardrop elements, symmetrical elegant flourishes, bead/chain details, refined decorative geometry. "
        "PROMINENT, VISIBLE, SUBSTANTIAL, BEAUTIFUL, and ARTISTIC — ornament is as LARGE, BOLD, BEAUTIFUL, and SUBSTANTIAL as the subject itself. HIGH CONTRAST and BEAUTIFUL ARTISTIC PRESENCE. "
        "Every flourish must be REFINED, ELEGANT, BEAUTIFUL, and CONSISTENT with the {style} style.\n"
        "\n"
        f"MANDATORY STYLE: {style_note}\n"
        "This style MUST be applied prominently to BOTH the subject AND the ornament. Every line must reflect this style's characteristics. This is NOT negotiable.\n"
        "\n"
        "OUTPUT: THICK black and dark grey lines ONLY on flat white background. "
        "HIGH CONTRAST and VISIBLE — lines must STAND OUT and be READABLE from a distance. BEAUTIFUL contrast. "
        "No photo, skin, body, room, shadow, color, or texture. "
        "Keep the exact same subject, pose, and distinctive features but ENLARGE IT, make it PROMINENT, and make it BEAUTIFUL. "
        "BEAUTIFUL ARTISTIC hand-drawn quality — THICK confident elegant line strokes, strong beautiful artistic presence, organic wobble, refined handmade artistic feel. "
        "Add beautiful artistic flair: subtle variations in line weight, confident elegant curves, beautiful artistic shading touches, refined details. "
        "Center the complete LARGE BEAUTIFUL design. This will be applied to human skin as a PROMINENT BEAUTIFUL ARTISTIC professional tattoo MASTERPIECE in the {style} style."
    )


def _build_photo_convert_with_reference_prompt(
    style: str,
    region_key: str,
    user_subject_desc: str,
    coverage: str = "medium",
    strength: str = "",
) -> str:
    """
    photo_convert with a reference image. The model commonly fails this in
    two ways:
      (a) returns the reference image unchanged (forgets the body photo);
      (b) pastes the reference flat onto the body (sticker effect).
    Plus a third complaint: every variant looks identical even with
    different seeds, because the prompt over-specifies.

    Per-variant angle + composition pulls force the three variants to
    actually be three different tattoo interpretations of the same subject.
    """
    style_descriptor = STYLE_DESCRIPTORS.get(style, STYLE_DESCRIPTORS["fine_line"])
    style_lock = _PHOTO_CONVERT_STYLE_LOCK.get(style, _PHOTO_CONVERT_STYLE_LOCK["auto"])
    region_text = REGION_ANATOMY.get(region_key, REGION_ANATOMY["from_photo"])
    if _is_small_path(coverage, strength):
        region_text = _NARROW_PLACEMENT.get(region_key, _NARROW_PLACEMENT["from_photo"])
    size_block, _ = _size_block(style, coverage, strength)

    subj_hint = f" The client describes it as: {user_subject_desc}." if user_subject_desc.strip() else ""

    # Per-variant variation — render/framing only, never pose/angle.
    var_offset = (_variant_index_global + _variant_run_salt) % len(_PHOTO_CONVERT_VARIATIONS)
    variation = _PHOTO_CONVERT_VARIATIONS[var_offset]

    # Blackwork sometimes turns the entire image black because the style
    # descriptor talks about "packed solid black masses". Lock it down.
    bg_lock = ""
    if style == "blackwork":
        bg_lock = (
            "BACKGROUND LOCK: black ink is applied ONLY inside the tattoo silhouette on the skin. "
            "The background, clothing and surrounding skin in image 1 keep their original colours and brightness. "
            "Do NOT extend the black mass beyond the tattoo edges. Do NOT darken the photograph overall."
        )

    # Short prompt is intentional — long prompts cause p-image-edit to
    # regenerate the body from the description instead of editing image 1.
    # Every line earns its place. Body preservation is line 1.
    bg_line = ""
    if style == "blackwork":
        bg_line = "Black ink stays inside the tattoo silhouette only; do not darken the background.\n"

    return f"""TASK: Add a LARGE, BOLD, PROMINENT, BEAUTIFUL professional tattoo to image 1 (the body photo). Image 2 is the subject reference.

CRITICAL — READ FIRST:
- Return image 1 UNCHANGED except for tattoo ink added to skin.
- Do NOT paste image 2. Do NOT generate a body. Do NOT change background/lighting/clothing.
- Output ONLY image 1 with LARGE, BOLD tattoo ink added on the skin surface.

TATTOO DESIGN — LARGE, BOLD, ARTISTIC & BEAUTIFUL:
- THIS IS A LARGE, PROMINENT, GALLERY-QUALITY, BEAUTIFUL TATTOO MASTERPIECE — not a small design.
- MAIN SUBJECT (upper portion): Render the subject from image 2 as a LARGE, BOLD, BEAUTIFUL professional tattoo ink in the {style} style. THICK LINES. HEAVY INK DENSITY. HIGH CONTRAST. Make it BEAUTIFUL, ELEGANT, and REFINED. NOT delicate or thin. MAKE IT PROMINENT AND DOMINATE THE CANVAS.
- ORNAMENTAL FLOURISH (lower portion): Add LARGE, BOLD, ELABORATE, BEAUTIFUL ornamental design below: intricate baroque scrollwork, delicate filigree, elegant swirls, refined decorative geometry, elegant bead/chain details. PROMINENT, VISIBLE, SUBSTANTIAL, and EXQUISITELY BEAUTIFUL. ARTISTIC, ORNATE, and REFINED.
- The ornament should be as large, BOLD, BEAUTIFUL, and SUBSTANTIAL as the subject — not a small accent. MAKE IT EXQUISITE and STAND OUT.
- LINES MUST BE THICK AND VERY VISIBLE — this is BOLD tattoo art with PRESENCE and IMPACT and ARTISTIC BEAUTY.

SUBJECT RENDERING — ARTISTIC, BEAUTIFUL & BOLD:
- LARGE SIZE — the subject should take up a significant portion of the design space.
- BOLD, THICK LINES with HEAVY ink density and HIGH CONTRAST.
- BEAUTIFUL ARTISTIC DETAIL: If animal, include fine fur texture with VISIBLE ELEGANT LINE WORK, eye definition with BEAUTIFUL DEPTH and LIFE, mouth expression with PERSONALITY, whiskers with PROMINENT DELICATE LINES. Make it ARTISTIC, EXPRESSIVE, and BEAUTIFUL.
- ELEGANT SHADING with artistic sophistication — DARK INK on skin with CLEAR, BOLD, BEAUTIFUL definition.
- Match the pose and expression from image 2 exactly but render it LARGER, MORE PROMINENT, and MORE BEAUTIFUL.
- NOT thin linework. NOT delicate. BOLD, ARTISTIC, BEAUTIFUL, STRONG, and IMPACTFUL.

ORNAMENTAL DESIGN — ARTISTIC, ELABORATE & BEAUTIFUL:
- LARGE SCALE baroque scrollwork with bold flowing ELEGANT curved lines.
- PROMINENT, INTRICATE BEAUTIFUL filigree patterns and elegant teardrop elements with REFINED artistic detail.
- BOLD, ELEGANT symmetrical flourishes and refined decorative geometry.
- HEAVY ink density with BEAUTIFUL ARTISTIC shading — professional tattoo ornament with VISIBLE, PROMINENT, BOLD, ELEGANT lines.
- EXQUISITE DETAIL: Every curve, every flourish, every element should be BEAUTIFUL and REFINED. This is HIGH-END tattoo art.
- Make it STAND OUT, be VISIBLE, have ARTISTIC PRESENCE, and be STUNNINGLY BEAUTIFUL.
- ARTISTIC TOUCHES: Add subtle variations in line weight with REFINED confidence, organic flowing curves, handmade elegant feel — make it look like a MASTER TATTOO ARTIST'S BEAUTIFUL MASTERPIECE.

PLACEMENT: {region_text.rstrip('.')}
{size_block}

ARTISTIC QUALITY & BEAUTY:
- This should look like a PROFESSIONAL TATTOO ARTIST'S BEAUTIFUL MASTERPIECE — bold, confident, artistic, and BEAUTIFUL.
- STRONG line weight variation with ARTISTIC confidence and REFINED elegance.
- DRAMATIC shading and BOLD contrast with BEAUTIFUL balance.
- Hand-crafted BEAUTIFUL artistic quality — NOT computer-generated or uniform. REFINED and ELEGANT.
- Every line should have PURPOSE and BEAUTY — this is luxury tattoo art.

INK APPEARANCE:
- Real healed tattoo (6+ months old) — matte, not glossy.
- BOLD, THICK lines that are CLEARLY VISIBLE and PROMINENT from any distance.
- Natural edges with slight hand-applied wobble for organic BEAUTY.
- Skin texture (pores, hair) visible around and through ink.
- Skin tone EXACTLY the same everywhere — no colored halo or glow.
- Design wraps naturally with body curves.
- HIGH CONTRAST between ink and skin — LINES STAND OUT PROMINENTLY.

FORBIDDEN:
- Thin, delicate, or faint linework. LINES MUST BE BOLD.
- Small or timid design. MAKE IT LARGE AND PROMINENT.
- Pasting image 2 as photo or sticker.
- Bare outline without shading.
- Changing the body, background, or anything except adding ink.
- Generic/simplistic/ugly design. MAKE IT BEAUTIFUL and ARTISTIC.
- Glossy, fresh, or sticker-like appearance.
- LOW CONTRAST or hard-to-see lines — MAKE IT PROMINENT AND VISIBLE.
- Computer-generated look. MAKE IT BEAUTIFUL, ARTISTIC, and HANDMADE.
- Clumsy or inelegant ornament. MAKE IT REFINED and BEAUTIFUL.

{bg_line}{variation}
{NO_TEXT_RULE}

Render this as a LARGE, BOLD, PROMINENT, BEAUTIFUL, ARTISTIC professional healed tattoo on real skin with STRONG presence, REFINED beauty, and ARTISTIC IMPACT. This is a MASTERPIECE."""


# ===========================================================================
# 10b. SCAR COVER-UP TATTOOS — geometry-aware, three strategies
# ===========================================================================
#
# v3 prompt design notes:
#   * The previous prompt was contradictory: it told the model to use the
#     "minimalist" style descriptor ("design occupies under 12 percent of
#     skin") AND that the tattoo should be "93 percent of the photo long".
#     The model averaged the two and produced tiny floating squiggles.
#   * The TRANSFORM motifs assumed every scar is vertical and could be
#     framed by "two halves with a blank middle". Real scars are diagonal,
#     curved, branching. SAM-2 now gives us the scar's actual orientation
#     (angle_deg) and shape ("linear" / "round" / "irregular"), so motifs
#     can adapt to the real geometry.
#   * Style is now a *rendering* descriptor only — line weight, finish,
#     shading texture. Size and coverage come from a single source of
#     truth (the SCAR FOOTPRINT block), not the style descriptor.
#   * The CAMOUFLAGE / OVERSHADOW prompts no longer carry the
#     "split into left/right halves" leak from TRANSFORM.

# Per-strategy rendering brief — short, focused, no internal contradictions.
_SCAR_STRATEGY_BRIEFS: dict[str, str] = {
    "camouflage": (
        "CAMOUFLAGE: paint a single dense, richly textured tattoo that "
        "absorbs the scar into the design. Use varied line weights, layered "
        "shading and busy interior texture so the scar tissue reads as one "
        "more line in the artwork. The viewer cannot tell where ink ends "
        "and scar begins. One unified piece — not two halves, not a frame."
    ),
    "transform": (
        "TRANSFORM: paint a tattoo that follows the scar's exact path and "
        "shape, treating the scar as the central spine of the design. The "
        "scar tissue stays visible as bare skin and is the focal feature of "
        "the artwork. The tattoo grows ALONG the scar (paralleling its "
        "actual orientation) and feeds into it — never crosses straight "
        "over it, never erases it. This is reclamation: the scar is the "
        "story the design is built around."
    ),
    "overshadow": (
        "OVERSHADOW: paint one bold high-contrast tattoo that visually "
        "dominates the area through sheer presence — heavy black masses, "
        "strong silhouette, dense ink. The scar disappears not because it "
        "is hidden but because the eye is captured by the tattoo's "
        "artistic impact first. Single committed composition, not a busy "
        "pattern."
    ),
}

# Motif pools per strategy × shape category. These are PHRASES that get
# interpolated into the prompt — they describe the subject, not the
# rendering style. Shape category comes from SAM geometry analysis.
_SCAR_MOTIFS: dict[str, dict[str, list[str]]] = {
    "camouflage": {
        "linear": [
            "a snake coiled along the scar's path with detailed scale shading absorbing every irregularity",
            "a flowing dragon body with dense scale texture wrapping the scar line into its spine",
            "a botanical branch heavy with leaves and small blossoms, shading thickest where the scar runs",
            "an ornamental dagger with engraved hilt and rich blade shading aligned to the scar",
            "a feather with detailed barbs, dense black-and-grey shading, oriented along the scar",
        ],
        "round": [
            "a layered rose with deep interior shading centered exactly on the scar",
            "a dense mandala with concentric ornamental rings absorbing the scar into its core",
            "a moth with detailed wing patterns, body centered on the scar",
            "a sun face with rich rays of varied weight radiating from the scar",
            "a peony bloom with packed petal shading covering the scar",
        ],
        "irregular": [
            "a dense floral cluster of three or four blooms with rich varied shading",
            "an organic blackwork pattern with intentional negative-space windows woven through the scar",
            "a wolf or fox face in black-and-grey realism with thick fur texture absorbing the scar",
            "a textured ornamental piece with filigree, dotwork and shading layered over the scar area",
        ],
    },
    "transform": {
        "linear": [
            "a slim botanical vine that grows ALONG the scar — small leaves and one or two blossoms branching off the scar line, the scar itself stays as bare-skin stem",
            "two thin parallel ornamental lines running ALONG the scar with small filigree accents, the scar as the centerline",
            "a fine arrow or feather quill aligned ALONG the scar, with the scar reading as the shaft",
            "delicate cherry-blossom branch following the scar's direction, blossoms drifting off to one side",
            "a fine line snake or eel whose body runs ALONG the scar, with the scar tissue as its spine",
        ],
        "round": [
            "a botanical wreath circling the scar — leaves and tiny blooms forming a ring around bare-skin scar in the center",
            "a thin ornamental ring or sun-burst radiating OUTWARD from the scar, scar tissue at the exact center",
            "a delicate moth or butterfly whose body floats just BESIDE the scar, with the scar visible as a celestial element nearby",
            "a fine geometric medallion framing the scar, scar visible as the central jewel",
        ],
        "irregular": [
            "small constellation of fine line botanicals scattered AROUND the scar, scar visible as the negative-space focal point",
            "delicate ornamental flourishes radiating outward FROM the scar's edges, scar itself untouched",
            "a flock of three small birds taking flight FROM the scar's edge, scar visible as their starting point",
            "fine sprigs of wildflowers growing OUT from the scar's natural shape, scar as bare-skin ground",
        ],
    },
    "overshadow": {
        "linear": [
            "a bold blackwork dagger placed dramatically across the area, scar fully covered by the blade",
            "a strong silhouetted raven or eagle with wings spread across the area",
            "a bold panther head in solid black-and-grey realism dominating the frame",
            "a dense japanese-style koi or dragon swimming across the area with bold outline",
        ],
        "round": [
            "a bold solid-black sun or moon disc with engraved internal patterns dominating the area",
            "a strong mandala in bold blackwork covering the area",
            "a heavy ornamental medallion with dense interior detail",
            "a bold roaring lion or wolf head in black-and-grey realism filling the area",
        ],
        "irregular": [
            "a bold blackwork floral burst with thick petals and dense shading dominating the area",
            "a dramatic phoenix in flames with bold silhouette filling the area",
            "a heavy ornamental piece with packed black masses across the entire area",
            "a strong kraken tentacle or serpent in dense blackwork across the area",
        ],
    },
}

# Sensitive (self-harm) motifs — gentle, life-affirming, never weapons,
# never sharp imagery, never anything that could re-traumatize.
_SCAR_SENSITIVE_MOTIFS: dict[str, list[str]] = {
    "camouflage": [
        "a soft botanical with layered blossoms and warm shading absorbing the scar line",
        "a phoenix with elegant flowing feathers and gentle shading covering the area",
        "a peony bloom with packed petal shading centered on the scar",
        "a flowing wave-and-flowers piece in soft black-and-grey",
    ],
    "transform": [
        "wildflowers growing ALONG the scar, scar visible as bare-skin stem of the bouquet",
        "a delicate moth resting BESIDE the scar, scar visible as a slender quiet element",
        "a fine semicolon worked elegantly into a botanical sprig that follows the scar",
        "small birds in flight FROM the scar's edge, scar visible as the place they leave",
        "a soft sunrise with rays radiating FROM the scar, scar visible as the horizon line",
    ],
    "overshadow": [
        "a bold phoenix rising with strong feather work covering the area",
        "a strong botanical bouquet with bold blooms and packed shading dominating the area",
        "a bold sun with radiating rays and packed interior detail",
    ],
}


# Style here is a RENDERING brief only — finish quality, line character.
# Crucially, no size or coverage % language. Size is owned by SCAR FOOTPRINT.
_SCAR_STYLE_RENDER: dict[str, str] = {
    "fine_line": "hair-thin single-needle linework, single weight, minimal or no shading, healed dark ink that has settled into the dermis",
    "minimalist": "clean confident linework with restrained interior shading — minimal does NOT mean tiny here, it means uncluttered",
    "blackwork": "packed solid matte black masses, bold confident contour, intentional negative-space windows, no grey gradients",
    "traditional": "bold confident outline, thinner interior lines, classic flat tonal blocks and B&G whip shading",
    "japanese": "bold outer contour with varying interior weight, soft controlled grey shading, structured negative space",
    "realism": "no outlines, form defined by soft controlled grey gradients and deep blacks, edges fading organically into bare skin",
    "geometric": "precise straight edges, ruler-quality arcs, consistent line weight, optional measured dotwork at vertices",
    "ornamental": "jewelry-quality filigree, fine teardrops, bead-chain accents, delicate interior with slightly stronger outer rim",
    "script": "hand-lettered script with proper weight rhythm and kerning",
    "auto": "professional shop-quality tattoo, single committed style appropriate to the subject",
    "stencil": "bold clean confident outline only, hollow interiors",
}


def _scar_geom_block(geom: Optional[dict]) -> str:
    """
    Translate SAM geometry into a precise instruction block. When SAM
    didn't run or didn't find a mask, returns a generic fallback.
    """
    if not geom:
        return ""
    cx = geom.get("cx_pct", 50.0)
    cy = geom.get("cy_pct", 50.0)
    length = geom.get("length_pct", 0.0)
    width = geom.get("width_pct", 0.0)
    angle = geom.get("angle_deg", 0.0)
    shape = geom.get("shape", "irregular")
    desc = geom.get("description", "scar")

    # Direction phrase the model will actually use to align the design.
    a = abs(float(angle))
    if shape != "linear":
        direction = "no dominant direction (scar is not strongly elongated)"
    elif a < 15:
        direction = "horizontal (left-to-right)"
    elif a < 35:
        direction = "shallow diagonal"
    elif a < 55:
        direction = (
            f"diagonal at ~{int(a)}° (rising to the right)"
            if angle > 0
            else f"diagonal at ~{int(a)}° (falling to the right)"
        )
    elif a < 75:
        direction = "steep diagonal (almost vertical)"
    else:
        direction = "vertical (top-to-bottom)"

    return (
        f"SCAR FOOTPRINT (measured from the photo):\n"
        f"- {desc}\n"
        f"- centered at {cx:.0f}% across, {cy:.0f}% down\n"
        f"- runs {direction}\n"
        f"- length ~{length:.0f}% of the photo's short side, width ~{width:.0f}%\n"
        f"- THE DESIGN MUST FOLLOW THIS FOOTPRINT — its main axis aligned to "
        f"the scar's direction, its size matched to the scar's length, its "
        f"placement centered on the scar."
    )


def _scar_location_block_from_mark(scar_mark: Optional[Tuple[float, float, float]]) -> str:
    """Coarser fallback when SAM didn't run — uses the user's tap directly."""
    if not scar_mark:
        return ""
    cx, cy, r = scar_mark
    length_pct = r * 200.0
    return (
        f"SCAR LOCATION (from user marker — exact shape unknown):\n"
        f"- centered at {cx * 100:.0f}% across, {cy * 100:.0f}% down\n"
        f"- approximately {length_pct:.0f}% of the photo's short side wide\n"
        f"- center the design on this point and infer the scar's true shape "
        f"from the photo (look for skin discoloration / line of differing texture)."
    )


def _pick_scar_motif(
    strategy_key: str,
    shape_category: str,
    is_sensitive: bool,
    rng: Optional[random.Random],
) -> str:
    if is_sensitive:
        pool = _SCAR_SENSITIVE_MOTIFS.get(strategy_key) or _SCAR_SENSITIVE_MOTIFS["camouflage"]
    else:
        per_shape = _SCAR_MOTIFS.get(strategy_key) or _SCAR_MOTIFS["camouflage"]
        pool = per_shape.get(shape_category) or per_shape["irregular"]
    return rng.choice(pool) if rng is not None else pool[0]


def get_scar_transform_components(
    style: str,
    scar_type: str,
    scar_shape: str,
    scar_geometry: Optional[dict],
    variant_index: int,
    *,
    run_salt: int = 0,
) -> tuple[str, str, bool, dict]:
    """
    Produce the per-variant motif and rendering descriptor needed by the
    Flux Fill Pro scar `transform` path.

    Returns
    -------
    (style_render, motif_phrase, is_sensitive, geometry_used)

    The motif is drawn deterministically from the same pools as the
    normal scar prompt builder (so options stay coherent across UI
    descriptions and generated output) but uses a per-variant rng so
    the n concepts in one request don't all pick the same motif.
    """
    style_key = (style or "auto").lower().strip()
    if style_key not in _SCAR_STYLE_RENDER:
        style_key = "auto"
    style_render = _SCAR_STYLE_RENDER[style_key]

    if scar_geometry and scar_geometry.get("shape"):
        shape_category = scar_geometry["shape"]
    else:
        sh = (scar_shape or "").lower()
        if "linear" in sh or "line" in sh or "incision" in sh or "surgical" in sh:
            shape_category = "linear"
        elif "round" in sh or "circular" in sh or "spot" in sh:
            shape_category = "round"
        else:
            shape_category = "irregular"

    is_sensitive = (scar_type or "").lower().strip() in {
        "self_harm",
        "self-harm",
        "selfharm",
    }

    rng = random.Random(f"scar_transform|{variant_index}|{run_salt}|{shape_category}|{int(is_sensitive)}")
    motif = _pick_scar_motif("transform", shape_category, is_sensitive, rng)

    return style_render, motif, is_sensitive, (scar_geometry or {})


def _scar_size_block(
    geom: Optional[dict], scar_mark: Optional[Tuple[float, float, float]], strategy_key: str
) -> str:
    """
    Single source of truth for scar tattoo size. Overrides whatever the
    style descriptor would have suggested — no more 'minimalist tiny mark
    on a 93%-long region' contradictions.
    """
    if geom and geom.get("length_pct", 0.0) > 0:
        length = float(geom["length_pct"])
        width = float(geom.get("width_pct", length * 0.3))
    elif scar_mark:
        length = float(scar_mark[2]) * 200.0
        width = length * 0.5
    else:
        length = 35.0
        width = 18.0

    if strategy_key == "transform":
        return (
            f"SIZE: the design's longest dimension is roughly {length:.0f}% of "
            f"the photo's short side (matched to the scar's length). The design "
            f"hugs the scar — only {max(width * 1.6, 10.0):.0f}% wide overall — "
            f"never a wide circle, never a giant frame around the whole area."
        )
    if strategy_key == "camouflage":
        # Camouflage needs to fully cover the scar plus a small margin so
        # the eye can't track the scar past the tattoo's edge.
        cover = max(length * 1.15, length + 6.0)
        return (
            f"SIZE: the tattoo's longest dimension is roughly {cover:.0f}% of "
            f"the photo's short side — large enough to FULLY cover the scar "
            f"with a small margin of ink past every edge so the scar cannot "
            f"be seen poking out of the design."
        )
    # overshadow
    cover = max(length * 1.4, length + 12.0)
    return (
        f"SIZE: the tattoo's longest dimension is roughly {cover:.0f}% of "
        f"the photo's short side — substantially LARGER than the scar so "
        f"the design clearly dominates the visual field. Bold confident "
        f"composition, not a tight little piece."
    )


def _build_scar_coverup_prompt(
    style: str,
    region_key: str,
    strategy: str,
    scar_type: str,
    scar_shape: str,
    scar_description: str,
    coverage: str = "medium",
    strength: str = "",
    scar_mark: Optional[Tuple[float, float, float]] = None,
    scar_geometry: Optional[dict] = None,
) -> str:
    """
    Geometry-aware scar cover-up prompt. v3.

    `scar_geometry` (when present) comes from `scar_segment.ScarSegmentation`
    and contains the SAM-2-derived shape, orientation and size. When absent,
    we fall back to the user's tap (less precise but still positional).
    """
    region_text = REGION_ANATOMY.get(region_key, REGION_ANATOMY["other"])

    strategy_key = (strategy or "camouflage").lower().strip()
    if strategy_key not in _SCAR_STRATEGY_BRIEFS:
        strategy_key = "camouflage"
    strategy_brief = _SCAR_STRATEGY_BRIEFS[strategy_key]

    style_key = (style or "auto").lower().strip()
    if style_key not in _SCAR_STYLE_RENDER:
        style_key = "auto"
    style_render = _SCAR_STYLE_RENDER[style_key]

    # Shape category — prefer SAM, fall back to the user's free-text answer.
    if scar_geometry and scar_geometry.get("shape"):
        shape_category = scar_geometry["shape"]
    else:
        sh = (scar_shape or "").lower()
        if "linear" in sh or "line" in sh or "incision" in sh or "surgical" in sh:
            shape_category = "linear"
        elif "round" in sh or "circular" in sh or "spot" in sh:
            shape_category = "round"
        else:
            shape_category = "irregular"

    is_sensitive = (scar_type or "").lower().strip() in {
        "self_harm",
        "self-harm",
        "selfharm",
    }

    motif = _pick_scar_motif(strategy_key, shape_category, is_sensitive, _variant_rng)

    geom_block = (
        _scar_geom_block(scar_geometry)
        if scar_geometry
        else _scar_location_block_from_mark(scar_mark)
    )
    size_block = _scar_size_block(scar_geometry, scar_mark, strategy_key)

    desc_clean = _strip_size_hints((scar_description or "").strip()[:240])
    user_note = f"Client adds: {desc_clean}." if desc_clean else ""

    sensitive_note = (
        "TONE: the user is healing — gentle, life-affirming imagery only. "
        "No weapons, no sharp blades, no aggressive symbolism."
        if is_sensitive
        else ""
    )

    # Strategy-specific final-line directives. These are tight and only
    # appear once per strategy — no more conflicting "do this" / "don't
    # do this" pairs from the v2 prompt.
    if strategy_key == "transform":
        directive = (
            "DO: align the design's main axis to the scar's direction. "
            "Let the scar tissue itself remain bare skin and read as part "
            "of the composition (a stem, a centerline, a quiet element).\n"
            "DON'T: paint solid ink across the scar's footprint. Don't "
            "cover the scar with the tattoo. Don't add text or letters."
        )
    elif strategy_key == "camouflage":
        directive = (
            "DO: paint one unified detailed piece that fully covers the "
            "scar's footprint. Use dense varied shading and layered line "
            "weights so the scar dissolves into the artwork.\n"
            "DON'T: leave the scar visible. Don't split into two halves. "
            "Don't draw a frame around the area. No text or letters."
        )
    else:  # overshadow
        directive = (
            "DO: paint one bold high-contrast piece that visually "
            "dominates the area with strong silhouette and packed ink.\n"
            "DON'T: produce a busy fragmented pattern. Don't draw a frame. "
            "No text or letters."
        )

    return f"""TASK: Add a real healed tattoo to this body photo so the scar is handled with intention. Output the EXACT same photograph with ink added — same person, same skin, same lighting, same pose, same background.

REGION: {region_text}

{geom_block}

STRATEGY — {strategy_key.upper()}: {strategy_brief}

{sensitive_note}

DESIGN
- Subject: {motif}
- Rendering: {style_render}
- {user_note}

{size_block}

{directive}

INK REALISM: real healed tattoo ink that has settled into the dermis on the actual skin in the photo. Matte finish, natural lighting matching the photo. NOT a sticker, NOT a decal, NOT a digital overlay, NOT a sketch on top. Edges are clean but slightly organic where ink has spread into the dermis.
"""


# ===========================================================================
# 11. PUBLIC API — single p-image-edit call per concept
# (HiDream 2-step pipeline removed)
# ===========================================================================

def build_tattoo_edit_prompt(
    flow_id: str,
    answers: dict[str, Any],
    variant_index: int,
    *,
    reference_image_attached: bool = False,
    run_salt: int = 0,
) -> str:
    """
    Public API consumed by replicate_tattoo.py.

    Always returns a fully formed prompt for one Replicate request, regardless
    of which combination of inputs the user picked. Every style alias is
    normalised; every coverage value is bounded; every flow has a real path.

    `run_salt` is a per-request random integer that the caller generates
    once and passes to all variants in the same request. It rotates the
    subject pool's starting offset so two separate generations with the
    exact same user answers don't land on the exact same motifs.
    """
    global _variant_rng, _variant_index_global, _variant_pick_count, _variant_run_salt

    try:
        answer_key = repr(sorted((k, str(v)) for k, v in (answers or {}).items()))
    except Exception:
        answer_key = ""
    _variant_rng = random.Random(f"{variant_index}|{flow_id}|{answer_key}|{run_salt}")
    _variant_index_global = int(variant_index)
    _variant_run_salt = int(run_salt)
    _variant_pick_count = 0

    try:
        region_key = str(answers.get("body_region") or "other").lower()
        if region_key not in REGION_ANATOMY:
            region_key = "other"

        style = _normalize_style(resolve_style(flow_id, answers))
        if style not in STYLE_DESCRIPTORS:
            style = "auto"

        coverage = str(answers.get("coverage") or "")
        strength = str(answers.get("strength") or "")
        intensity_note = intensity_modifier(coverage, strength)

        if flow_id == "photo_convert" and reference_image_attached:
            user_subject_desc = _clip(str(answers.get("photo_subject") or ""), 300)
            return _build_photo_convert_with_reference_prompt(
                style=style,
                region_key=region_key,
                user_subject_desc=user_subject_desc,
                coverage=coverage,
                strength=strength,
            )

        if flow_id == "scar_coverup":
            from .scar_preserve import parse_mark_string

            strategy = str(answers.get("scar_strategy") or "camouflage")
            scar_type = _clip(str(answers.get("scar_type") or ""), 80)
            scar_shape = _clip(str(answers.get("scar_shape") or ""), 80)
            scar_description = _clip(str(answers.get("scar_description") or ""), 300)
            scar_mark = parse_mark_string(str(answers.get("scar_mark") or ""))
            scar_geometry = answers.get("scar_geometry")
            if not isinstance(scar_geometry, dict):
                scar_geometry = None
            return _build_scar_coverup_prompt(
                style=style,
                region_key=region_key,
                strategy=strategy,
                scar_type=scar_type,
                scar_shape=scar_shape,
                scar_description=scar_description,
                coverage=coverage,
                strength=strength,
                scar_mark=scar_mark,
                scar_geometry=scar_geometry,
            )

        # Allow text in design only when the flow explicitly asked for lettering.
        allow_text = False
        if flow_id == "deep_meaning":
            form = str(answers.get("form") or "").lower()
            if form in ("script", "symbol_script") and str(answers.get("script_quote") or "").strip():
                allow_text = True

        focal_subject, extra_note = _focal_for_flow(flow_id, answers, style)
        return _build_subject_prompt(
            style=style,
            region_key=region_key,
            flow_id=flow_id,
            focal_subject=focal_subject,
            extra_note=extra_note,
            intensity_note=intensity_note,
            coverage=coverage,
            strength=strength,
            allow_text_in_design=allow_text,
        )
    finally:
        _variant_rng = None
        _variant_pick_count = 0
