"""
Replicate prunaai/p-image-edit — body photo required; optional second image
for the photo_convert reference flow.

DEFAULT for photo_convert + reference image: STENCIL + LOCAL COMPOSITE.
  1) Edit the reference alone into a black/grey tattoo stencil on white.
  2) Composite that stencil onto the user's body JPEG with a dermal-style
     ink blend (placement + scale from body_region & coverage).
This is the path that reliably converts the reference photo INTO ink — the
single two-image p-image-edit call frequently pastes the reference as a
flat photographic sticker (the "real photo glued onto the arm" failure).

Opt OUT (use the single two-image edit instead) by setting
TATTOO_PHOTO_CONVERT_STENCIL=0 in the env.
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import random
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image

from .photo_convert_composite import composite_stencil_on_body
from .prompts import (
    NO_TEXT_RULE,
    REALISM_BLOCK,
    STYLE_DESCRIPTORS,
    _normalize_style,
    _size_block,
    build_photo_convert_stencil_prompt,
    build_tattoo_edit_prompt,
    intensity_modifier,
    resolve_style,
)
from .tattoo_postprocess import composite_scar_tattoo, heal_if_pair

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
if not REPLICATE_API_TOKEN:
    _env = Path(__file__).resolve().parent.parent.parent / ".env"
    if _env.exists():
        try:
            for line in _env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("REPLICATE_API_TOKEN="):
                    REPLICATE_API_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
                    break
        except OSError:
            pass

PREDICTIONS_URL = "https://api.replicate.com/v1/models/prunaai/p-image-edit/predictions"
POLL_INTERVAL_SEC = 1.0
POLL_MAX_ATTEMPTS = 150
HTTP_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=40)

_COUPLE_BASE_MOTIFS = [
    "two cranes in mirrored graceful motion",
    "paired serpents flowing in complementary curves",
    "sun and moon orbit composition",
    "interlocking botanical vines with shared stem language",
    "two wolves in complementary stance",
    "celestial constellation pair linked by subtle line rhythm",
    "wave and mountain dual motif with shared contour DNA",
]

_COUPLE_MATCHING_VARIANTS = [
    ("left-facing silhouette with rising flow", "right-facing silhouette with rising flow"),
    ("vertical elegant composition with tapering tail", "vertical elegant composition with tapering tail"),
    ("compact centered composition with open negative space", "compact centered composition with open negative space"),
]


# Curated theme → (Partner A motif, Partner B motif) pairs.
#
# Why a library + complete-tattoo generation, not literal halves:
# image-edit models reliably draw FULL tattoos and reliably ignore "draw
# only half" instructions (training data is full designs). After multiple
# attempts at literal half-splitting we kept getting two complete birds
# with both wings on each arm — the model just renders a complete piece
# and we can't argue it out of that habit. Real-world couple tattoos
# follow this same pattern: each person gets a complete, beautiful piece,
# and the COMPLEMENTARY relationship is conceptual (lock/key, sun/moon,
# wolf/moon) not pixel-level.
#
# Matching is keyword-based: we lowercase the user's shared_theme and look
# for any token in the pair keys. Multiple tokens may match → first wins.
# Unknown themes fall back to a "facing-each-other" mirror pair so the
# tattoos still feel intentionally paired.
_COMPLEMENTARY_PAIRS: dict[str, tuple[str, str]] = {
    # Romantic / connection
    "lock": ("an ornate antique padlock with intricate filigree details on its body", "an elegant skeleton key with ornamental bow and detailed teeth, mirroring the lock's filigree"),
    "key": ("an elegant skeleton key with ornamental bow and detailed teeth", "an ornate antique padlock with matching filigree, the key fits this lock"),
    "love": ("an ornate antique padlock with filigree heart accents", "an elegant skeleton key with a heart-shaped bow and matching filigree"),
    "heart": ("the LEFT half of an anatomical heart with ornate flourishes flowing rightward off the design", "the RIGHT half of the same anatomical heart, flourishes flowing leftward, the two pieces clearly meant to be joined"),
    "puzzle": ("a single jigsaw puzzle piece with rich interior pattern, its right edge a clean puzzle-piece tab", "the matching jigsaw puzzle piece with the corresponding socket on its left edge, interior pattern continues the partner's"),
    "infinity": ("the LEFT loop of an infinity symbol with intricate ornamental detailing inside the loop", "the RIGHT loop of the same infinity symbol with mirrored ornamental detailing"),

    # Celestial pair
    "sun": ("a radiant sun with detailed flame-like rays and an ornate face", "a serene crescent moon with stars and constellations around it"),
    "moon": ("a serene crescent moon with stars and detailed lunar surface", "a radiant sun with detailed flame-like rays and an ornate face"),
    "star": ("a single bright north star with rays radiating outward", "a small constellation of paired stars connected by faint lines"),
    "celestial": ("a sun with detailed rays and ornamental flourishes", "a moon with stars woven through ornamental flourishes"),
    "yin": ("the YIN side: dark organic flowing shape with a single bright dot, soft botanical accents", "the YANG side: light organic flowing shape with a single dark dot, soft botanical accents matching the yin"),
    "yang": ("the YANG side: light organic flowing shape with a single dark dot, soft botanical accents", "the YIN side: dark organic flowing shape with a single bright dot, soft botanical accents matching the yang"),

    # Natural pair
    "wolf": ("a male wolf in profile facing right, head raised, detailed fur shading", "a female wolf in profile facing left, head raised, the two clearly meant as a pair"),
    "lion": ("a male lion's head with full mane facing right, fierce expression", "a lioness's head facing left, sleek and noble, the two as a pair"),
    "tiger": ("a tiger's head facing right with detailed stripes", "a tigress's head facing left with detailed stripes, mirroring the tiger"),
    "fox": ("a fox curled in repose with bushy tail wrapped around itself, facing right", "a fox curled in repose facing left, mirror pose, tail-tip touching the partner's"),
    "deer": ("a stag with antlers facing right, alert posture", "a doe facing left, gentle posture, the two as a forest pair"),
    "bird": ("a bird in flight with wings spread, oriented to fly toward the right edge", "a matching bird in flight oriented toward the left edge, the two converging in midair"),
    "phoenix": ("a phoenix rising with wings unfurled and flames flowing rightward, gaze toward the right", "a phoenix descending in landing pose with wings folding inward and flames flowing leftward, gaze toward the left"),
    "dragon": ("an Eastern dragon in profile coiling rightward with detailed scales and fierce features", "a matching Eastern dragon coiling leftward, the pair forming an interlocking yin-yang silhouette"),
    "snake": ("a serpent with detailed scales facing right with tongue flicked outward", "a serpent with detailed scales facing left, the two appearing to circle a shared center"),
    "koi": ("a koi fish swimming upward with detailed scales, oriented rightward", "a koi fish swimming downward, oriented leftward, the two forming a yin-yang composition"),
    "butterfly": ("a butterfly with intricate wing patterns at rest with wings open, oriented to face right", "a matching butterfly with mirrored wing patterns oriented to face left"),
    "swan": ("a swan with elegant neck curved gracefully to the right, detailed feather work", "a swan with elegant neck curved gracefully to the left, the pair forming a heart silhouette in negative space between them"),
    "crane": ("a crane in mid-flight with neck extended to the right, detailed feather barbs", "a crane in mid-flight with neck extended to the left, the two appearing to fly toward each other"),

    # Botanical pair
    "tree": ("a tree showing its detailed root system spreading downward and outward", "a tree showing its branches and leaves spreading upward and outward — together with the partner the full tree is implied"),
    "rose": ("a rose with the bloom fully open and detailed petals, stem trailing rightward", "a rose still in bud with detailed leaves, stem trailing leftward, the two stems suggesting they grew from one plant"),
    "flower": ("a single open flower with detailed stamen and petals", "the same flower in bud form with leaves, the pair representing growth and bloom"),
    "vine": ("the LEFT portion of a continuous botanical vine with leaves and small blossoms, ending where it would continue to the right", "the RIGHT portion of the same vine, picking up where the partner's left off, the two forming one continuous plant"),
    "leaf": ("a detailed leaf with intricate vein patterns, stem oriented rightward", "a matching leaf with mirrored vein patterns, stem oriented leftward, the two from the same branch"),
    "feather": ("an ornate feather with intricate barb detail, quill oriented downward and slightly right", "a matching feather with mirrored barbs, quill oriented downward and slightly left, the pair like a fallen wingspan"),

    # Geographical / nautical
    "wave": ("a Hokusai-style ocean wave cresting toward the right with detailed foam patterns", "a matching wave cresting toward the left, the two forming a symmetrical sea storm"),
    "mountain": ("a detailed mountain range silhouette with one prominent peak rising toward the right", "a detailed mountain range silhouette with one prominent peak rising toward the left, the two ranges meeting at a valley between them"),
    "ocean": ("ocean waves with a small lighthouse, oriented rightward", "ocean waves with a small sailing ship, oriented leftward, the ship sailing toward the lighthouse"),
    "anchor": ("a detailed nautical anchor with rope coiled around its shaft", "a sailing ship with detailed rigging, the ship's anchor matching the partner's anchor"),
    "ship": ("a sailing ship with detailed rigging on a wave, oriented rightward", "a lighthouse on a rocky shore, oriented leftward, the ship sailing toward the lighthouse"),
    "compass": ("a detailed antique compass rose with cardinal points and ornate face", "an unfurled antique map fragment with a winding path leading toward where the compass points"),
    "map": ("an unfurled antique map fragment with a winding path", "a detailed antique compass rose with the needle pointing toward the partner's path"),

    # Symbolic / abstract
    "music": ("a treble clef with flowing notes streaming off to the right edge", "a bass clef with flowing notes streaming off to the left edge, the notes appearing to converge between them"),
    "fire": ("dancing flames flowing upward and rightward with sharp tongues", "flowing water with rippling waves moving leftward and upward, the elements meeting"),
    "water": ("flowing water with rippling waves moving rightward and upward", "dancing flames flowing leftward and upward with sharp tongues, the elements meeting"),
    "north": ("a north-pointing arrow with ornamental fletching and the letter-free phrase 'north' implied by an N-style mark", "a south-pointing arrow with mirrored ornamentation"),
    "alpha": ("an alpha-symbol-shaped ornamental design without using actual letterforms — abstract A-shape with filigree", "an omega-symbol-shaped ornamental design without using actual letterforms — abstract Ω-shape with matching filigree"),
}

# Ordered keyword search: longer keywords first so "phoenix flame" matches
# "phoenix" before any single-word tokens. Built once at import time.
_COMPLEMENTARY_KEYS_SORTED: list[str] = sorted(
    _COMPLEMENTARY_PAIRS.keys(), key=lambda k: -len(k)
)


def _resolve_complementary_pair(theme: str) -> tuple[tuple[str, str], str]:
    """
    Pick a (motif_a, motif_b) pair for the user's theme.

    Returns (pair, source) where source is "library" if a curated pair
    matched the theme, or "fallback" if we synthesized a generic
    facing-each-other pair from the user's raw theme.

    Keyword match is case-insensitive substring; longer keys win so
    "phoenix in flames" matches the phoenix entry, not a generic word.
    """
    t = (theme or "").strip().lower()
    if t:
        for key in _COMPLEMENTARY_KEYS_SORTED:
            if key in t:
                return _COMPLEMENTARY_PAIRS[key], "library"

    # No keyword match → synthesize a paired-orientation fallback so the
    # tattoos still read as a deliberate couple set. Each side gets the
    # SAME user concept but oriented toward the partner.
    base = theme.strip() if theme else "shared connection symbol"
    return (
        (
            f"a complete tattoo of {base}, composed so the design's visual flow "
            "leads toward the right side, as if facing or reaching toward a partner",
            f"a complete tattoo of {base}, composed so the design's visual flow "
            "leads toward the left side, as if facing or reaching toward a partner; "
            "match the line weight and stylistic DNA of the partner piece",
        ),
        "fallback",
    )


def _use_photo_convert_stencil() -> bool:
    """
    Default ON. The two-image p-image-edit call commonly pastes the reference
    as a flat photographic sticker on the body (failure mode users hate). The
    stencil + local dermal composite reliably converts the reference INTO
    real-looking ink. Opt out by setting TATTOO_PHOTO_CONVERT_STENCIL=0.
    """
    raw = os.environ.get("TATTOO_PHOTO_CONVERT_STENCIL", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def _log_prompt_bodies() -> bool:
    """Never log full prompt text unless explicitly enabled."""
    raw = os.environ.get("LOG_PROMPT_BODIES", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _b64_image(image_bytes: bytes) -> str:
    return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"


# ---------------------------------------------------------------------------
# Couple complementary_split — asymmetric stencil + deterministic midline split
# ---------------------------------------------------------------------------
#
# User picked option A: "literal halves of ONE design — left half on Partner
# A's arm, right half of the SAME eagle on Partner B's arm". For both halves
# to come from one source we MUST generate one complete stencil and split it.
# Two independent inpaint calls cannot produce halves of the same eagle.
#
# Why this attempt is different from the prior failed stencil-split:
#   - Earlier prompts said "couple tattoo" and the model rendered bilaterally
#     symmetric designs (full phoenix with both wings centered). Splitting at
#     midline left a near-complete bird in each half.
#   - This prompt FORCES a profile/asymmetric pose: subject in side-view,
#     head pointing one direction, asymmetric weight distribution. When you
#     bisect a profile-pose subject vertically, the two halves are GENUINELY
#     different (head + chest vs body + tail). That's the only way the split
#     reads as "halves" rather than "duplicates".


def _build_white_seed_jpeg(size: int = 1024) -> bytes:
    """Plain white JPEG used as a blank canvas for stencil-only generation."""
    im = Image.new("RGB", (size, size), (255, 255, 255))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def _build_couple_asymmetric_stencil_prompt(theme: str, style: str) -> str:
    """
    ONE complete tattoo design as a black-on-white stencil, drawn in a
    strictly ASYMMETRIC profile / side-view composition so it splits
    cleanly at the vertical midline into two visually distinct halves.

    Used as an image-edit instruction over a blank white seed JPEG via
    prunaai/p-image-edit. The model treats white-seed-edit as
    "draw on this canvas", which is why we hammer the "no skin / no
    body" lock and the explicit asymmetric-pose taxonomy — symmetric
    subjects are the default failure mode and this prompt is built
    around aggressively suppressing them.
    """
    style_descriptor = STYLE_DESCRIPTORS.get(style, STYLE_DESCRIPTORS["auto"])
    return (
        f"TASK: On this blank white canvas, draw ONE professional tattoo "
        f"flash design of {theme}, in pure black ink on white. NOTHING "
        f"ELSE may appear in the image — no skin, no body, no hand, no "
        f"forearm, no anatomy, no photograph, no color, no shadows, no "
        f"scenery, no texture, no noise, no border. Just clean crisp "
        f"black ink linework on a flat white background, like a "
        f"print-ready tattoo stencil sheet.\n"
        f"\n"
        f"COMPOSITION (HARD REQUIREMENT): subject rendered in PURE "
        f"SIDE-VIEW PROFILE, oriented HORIZONTALLY across the canvas. "
        f"The left half of the canvas must show ONE distinct portion of "
        f"the subject (head, chest, front, leading edge) and the right "
        f"half must show a DIFFERENT portion (rear, tail, back, "
        f"trailing edge). The two halves must be visually different. "
        f"DO NOT draw a front-facing, bilaterally symmetric or "
        f"mirror-symmetric subject. DO NOT center the subject's spine "
        f"on the canvas vertical midline. DO NOT draw two wings spread, "
        f"two arms outstretched, or any pose where the left and right "
        f"halves are near mirrors of each other.\n"
        f"\n"
        f"For bilateral subjects use these canonical asymmetric poses: "
        f"birds and winged creatures in profile flight with ONE visible "
        f"wing (NEVER two wings spread); snakes and dragons with head "
        f"on one side and body coiling to the other; quadrupeds (wolf, "
        f"tiger, lion, horse, deer) standing or running in profile with "
        f"head one way and tail the other; fish swimming in profile; "
        f"trees leaning with roots weighted one side and branches "
        f"reaching the other; floral compositions arcing diagonally.\n"
        f"\n"
        f"Style: {style_descriptor}. ONE single coherent subject filling "
        f"the frame width. Absolutely no letters, words, numbers, "
        f"watermarks, logos, captions or pseudo-text glyphs."
    )


def _split_stencil_at_midline(stencil_jpeg: bytes) -> tuple[bytes, bytes]:
    """
    Deterministically split a black-on-white stencil into LEFT and RIGHT
    halves at the vertical midline of its dark-pixel bounding box. Each
    half is tightly cropped around its remaining ink so the downstream
    composite places it cleanly on the partner's body.

    Returns (left_jpeg, right_jpeg).
    """
    try:
        im = Image.open(io.BytesIO(stencil_jpeg)).convert("RGB")
    except Exception:
        return stencil_jpeg, stencil_jpeg

    grey = im.convert("L")
    ink = grey.point(lambda v: 255 if v < 200 else 0)
    bbox = ink.getbbox()
    if bbox is None:
        # Stencil came back blank — fall back to canvas vertical center.
        mid_x = im.width // 2
    else:
        x0_ink, _, x1_ink, _ = bbox
        mid_x = (x0_ink + x1_ink) // 2

    left_canvas = Image.new("RGB", im.size, (255, 255, 255))
    left_canvas.paste(im.crop((0, 0, mid_x, im.height)), (0, 0))
    right_canvas = Image.new("RGB", im.size, (255, 255, 255))
    right_canvas.paste(im.crop((mid_x, 0, im.width, im.height)), (mid_x, 0))

    def _tight_crop(canvas: Image.Image) -> Image.Image:
        g = canvas.convert("L").point(lambda v: 255 if v < 200 else 0)
        bb = g.getbbox()
        if bb is None:
            return canvas
        cx0, cy0, cx1, cy1 = bb
        pad = max(8, int(min(canvas.size) * 0.025))
        cx0 = max(0, cx0 - pad)
        cy0 = max(0, cy0 - pad)
        cx1 = min(canvas.width, cx1 + pad)
        cy1 = min(canvas.height, cy1 + pad)
        return canvas.crop((cx0, cy0, cx1, cy1))

    left_final = _tight_crop(left_canvas)
    right_final = _tight_crop(right_canvas)

    def _to_jpeg(im_: Image.Image) -> bytes:
        buf = io.BytesIO()
        im_.save(buf, format="JPEG", quality=94, optimize=True)
        return buf.getvalue()

    return _to_jpeg(left_final), _to_jpeg(right_final)


def _stencil_asymmetry_score(stencil_jpeg: bytes) -> float:
    """
    Cheap structural-asymmetry score in [0..1]. We grayscale the stencil,
    threshold to ink mask, then compare the LEFT half against a horizontal
    mirror of the RIGHT half (both centered on the ink bbox midline).

    score = pixels-that-disagree / pixels-in-either
    1.0 = totally asymmetric, 0.0 = perfectly mirror-symmetric.

    We use this to flag stencils that came back bilaterally symmetric
    despite the prompt — a signal to either retry with a different seed
    or fall back to a different generation strategy. Threshold of ~0.18
    catches the obvious "phoenix with two centered wings" failure mode.
    """
    try:
        im = Image.open(io.BytesIO(stencil_jpeg)).convert("L")
    except Exception:
        return 1.0
    ink = im.point(lambda v: 255 if v < 200 else 0)
    bbox = ink.getbbox()
    if bbox is None:
        return 1.0
    x0, y0, x1, y1 = bbox
    crop = ink.crop((x0, y0, x1, y1))
    w, h = crop.size
    if w < 16 or h < 16:
        return 1.0
    half_w = w // 2
    if half_w < 4:
        return 1.0
    left = crop.crop((0, 0, half_w, h))
    right = crop.crop((w - half_w, 0, w, h))
    right_mirrored = right.transpose(Image.FLIP_LEFT_RIGHT)
    a = bytes(left.tobytes())
    b = bytes(right_mirrored.tobytes())
    diff = sum(1 for ax, bx in zip(a, b) if ax != bx)
    union = sum(1 for ax, bx in zip(a, b) if ax or bx)
    if union == 0:
        return 1.0
    return diff / float(union)


def _render_half_on_skin_canvas(half_jpeg: bytes, side: str) -> bytes:
    """
    Place a half-stencil (black ink on white) onto a warm neutral skin-tone
    canvas so it reads like a real tattoo design card.

    The cut edge is flush to the inner side (right edge for the left half,
    left edge for the right half) so the two cards appear continuous when
    the side-by-side preview composes them with a small gap.
    """
    try:
        stencil = Image.open(io.BytesIO(half_jpeg)).convert("RGBA")
    except Exception:
        return half_jpeg

    data = stencil.load()
    assert data is not None
    sw, sh = stencil.size
    for y in range(sh):
        for x in range(sw):
            r, g, b, a = data[x, y]  # type: ignore[index]
            if r > 210 and g > 210 and b > 210:
                data[x, y] = (r, g, b, 0)  # type: ignore[index]

    pad = max(30, int(min(sw, sh) * 0.10))
    canvas_w = sw + pad * 2
    canvas_h = sh + pad * 2
    skin = (212, 168, 130)
    canvas = Image.new("RGB", (canvas_w, canvas_h), skin)

    if side == "left":
        paste_x = canvas_w - sw - pad
    else:
        paste_x = pad
    paste_y = pad
    canvas.paste(stencil, (paste_x, paste_y), stencil)

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=94, optimize=True)
    return buf.getvalue()


def _compose_side_by_side(left_jpeg: bytes, right_jpeg: bytes) -> bytes:
    left = Image.open(io.BytesIO(left_jpeg)).convert("RGB")
    right = Image.open(io.BytesIO(right_jpeg)).convert("RGB")

    target_h = max(left.height, right.height)
    if left.height != target_h:
        left = left.resize((max(1, int(left.width * (target_h / left.height))), target_h), Image.LANCZOS)
    if right.height != target_h:
        right = right.resize((max(1, int(right.width * (target_h / right.height))), target_h), Image.LANCZOS)

    gap = max(18, target_h // 35)
    out_w = left.width + gap + right.width
    canvas = Image.new("RGB", (out_w, target_h), color=(14, 14, 18))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + gap, 0))

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


def _build_couple_pair_spec(answers: dict) -> dict:
    mode = str(answers.get("couple_mode") or "matching_pair").strip().lower()
    if mode not in ("matching_pair", "complementary_split"):
        mode = "matching_pair"

    shared_theme = str(answers.get("shared_theme") or "love and connection").strip()
    style_family = str(answers.get("shared_style") or "auto").strip().lower()
    provided_pair_id = str(answers.get("couple_pair_id") or "").strip()
    if provided_pair_id:
        pair_id = provided_pair_id
    else:
        pair_id = f"{abs(hash((shared_theme.lower(), mode, style_family))) % 1_000_000:06d}"

    rng = random.Random(f"pair|{pair_id}|{shared_theme.lower()}|{mode}")
    # Theme lock: when user gives explicit text, use that as the motif DNA.
    # Only fallback to a library motif if user text is empty/too short.
    motif = shared_theme if len(shared_theme) >= 3 else rng.choice(_COUPLE_BASE_MOTIFS)

    pair_source = "matching"
    if mode == "complementary_split":
        # NEW: complementary mode now uses curated paired motifs, not the
        # half-stencil approach. Each partner gets a distinct complete
        # motif (lock+key, sun+moon, wolf+wolf-mate, etc.) that pairs
        # conceptually with the partner's piece. Real couple tattoos work
        # this way; trying to draw "half a phoenix" on each arm doesn't.
        (left_role, right_role), pair_source = _resolve_complementary_pair(shared_theme)
    else:
        left_role, right_role = rng.choice(_COUPLE_MATCHING_VARIANTS)

    return {
        "mode": mode,
        "shared_theme": shared_theme,
        "style_family": style_family,
        "base_motif": motif,
        "left_role": left_role,
        "right_role": right_role,
        "pair_id": pair_id,
        "pair_source": pair_source,
    }


def _build_couple_prompt(
    person_label: str,
    side_tag: str,
    role_line: str,
    region_key: str,
    style_raw: str,
    coverage: str,
    strength: str,
    pair_spec: dict,
) -> str:
    style = _normalize_style(style_raw or pair_spec.get("style_family", "auto"))
    style_descriptor = STYLE_DESCRIPTORS.get(style, STYLE_DESCRIPTORS["auto"])
    size_block, _ = _size_block(style, coverage, strength)
    intensity = intensity_modifier(coverage, strength)
    region_text = (
        "skin in the photo — infer placement, scale and angle from anatomy, and wrap with body curvature."
        if region_key == "from_photo"
        else f"{region_key.replace('_', ' ')} placement with realistic anatomical wrap."
    )

    if pair_spec["mode"] == "complementary_split":
        pair_together_line = (
            "- This is COMPLEMENTARY mode: both partners get a COMPLETE, beautiful, "
            "standalone tattoo — but the two designs are DIFFERENT MOTIFS that pair together "
            "as a couple set (e.g. lock + key, sun + moon, wolf + wolf-mate). "
            "Render only YOUR partner's motif on YOUR photo. Do NOT also draw the partner's motif here. "
            "Do NOT draw the partner's body or hand here."
        )
        originality_pair = (
            "- Your motif is YOUR side of the couple set. The partner has the matching counterpart.\n"
            "- Treat this as ONE complete tattoo, fully resolved on its own. The pairing is conceptual."
        )
    else:
        pair_together_line = (
            "- The two partner tattoos must clearly belong together while remaining visually complete on their own."
        )
        originality_pair = (
            "- Preserve pair relationship to the partner output while keeping this side artistically complete."
        )

    return f"""TASK: Edit this photograph and add ONE professional healed tattoo for {person_label}.
Keep everything else in the image identical.

ZERO TEXT / MARKS (CRITICAL): no letters, numbers, words, captions, watermarks, logos, UI chrome, symbols that look like lettering, or random pseudo-text/gibberish anywhere in the frame. Tattoo ink only — if any readable or garbled text appears, the render has failed.
If the photo contains watermark or stock markings, do NOT reproduce them; leave that area unchanged skin/background.

COUPLE BLUEPRINT (MUST FOLLOW):
- Pair ID: {pair_spec['pair_id']}
- Mode: {pair_spec['mode']}
- Shared theme: {pair_spec['shared_theme']}
- This partner's specific motif: {role_line}
{pair_together_line}
- STRICT MOTIF LOCK: render ONLY this partner's specific motif (above). Do NOT add the partner's counterpart motif. Do NOT swap to unrelated motifs.

PLACEMENT: {region_text}
{size_block}

SUBJECT:
- This partner's tattoo IS: {role_line}
- It is a complete, finished, standalone tattoo on this body — gorgeous on its own.
- The COUPLE relationship comes from the partner having the matching counterpart on their photo, not from leaving this design incomplete.
- Make the composition eye-catching and beautiful: elegant silhouette, intentional focal point, refined line hierarchy.

STYLE:
{style_descriptor}
{intensity if intensity else ""}

ORIGINALITY LOCK:
- Make this composition custom, not stock.
{originality_pair}
- Use confident visual hierarchy and readable silhouette.
- Prioritize high-end beauty: graceful flow, polished detailing, and premium tattoo aesthetics.

{NO_TEXT_RULE}
{REALISM_BLOCK}
ABSOLUTE TYPOGRAPHY LOCK: no letters, no words, no numeric glyphs, no script-like marks.
"""


async def generate_couple_preview(
    image_a_jpeg: bytes,
    image_b_jpeg: bytes,
    answers: dict,
) -> tuple[Optional[dict], Optional[str]]:
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return None, "REPLICATE_API_TOKEN not configured"

    pair_spec = _build_couple_pair_spec(answers)

    coverage = str(answers.get("shared_coverage") or "medium").lower().strip()
    strength = str(answers.get("shared_strength") or "balanced").lower().strip()

    region_a = str(answers.get("person_a_body_region") or "from_photo").lower().strip()
    region_b = str(answers.get("person_b_body_region") or "from_photo").lower().strip()
    style_a = str(answers.get("person_a_style") or answers.get("shared_style") or "auto")
    style_b = str(answers.get("person_b_style") or answers.get("shared_style") or "auto")

    prompt_a = _build_couple_prompt(
        "Partner A",
        "left",
        pair_spec["left_role"],
        region_a,
        style_a,
        coverage,
        strength,
        pair_spec,
    )
    prompt_b = _build_couple_prompt(
        "Partner B",
        "right",
        pair_spec["right_role"],
        region_b,
        style_b,
        coverage,
        strength,
        pair_spec,
    )

    seed_base = random.randint(1, 999_999_999)
    seed_a = seed_base
    seed_b = max(1, (seed_base + 17_371) % 999_999_999)

    print(
        f"[COUPLE] mode={pair_spec['mode']} pair_id={pair_spec['pair_id']} "
        f"theme={pair_spec['shared_theme']!r} coverage={coverage} strength={strength} "
        f"pair_source={pair_spec.get('pair_source','matching')}"
    )
    print(f"[COUPLE] motif A: {pair_spec['left_role']}")
    print(f"[COUPLE] motif B: {pair_spec['right_role']}")

    async with httpx.AsyncClient(limits=HTTP_LIMITS, http2=False) as client:
        if pair_spec["mode"] == "complementary_split":
            # "Purani" approach (the only one that reliably ships two halves):
            #
            #   1. ONE prunaai/p-image-edit call on a blank white seed →
            #      a single asymmetric tattoo stencil for the shared theme.
            #   2. Geometric split at the ink-bbox vertical midline →
            #      left_half_stencil, right_half_stencil.
            #   3. Each half is rendered on a clean warm skin-tone card so
            #      the cards read as a continuous design when displayed
            #      side-by-side. (No body-photo compositing — every model
            #      we tested hallucinated a complete design back onto the
            #      body. Skin-tone card preview is honest, deterministic
            #      and never misplaces ink.)
            #
            # If the model returns a bilaterally symmetric stencil (score
            # below 0.18), we retry once with a different seed before
            # accepting it — this catches the "phoenix wings spread" case.
            #
            # Cost: ≤ 2× prunaai/p-image-edit (~$0.02 per couple split).
            style_for_stencil = _normalize_style(
                str(answers.get("shared_style") or "auto")
            )
            theme_text = pair_spec["shared_theme"]

            stencil_prompt = _build_couple_asymmetric_stencil_prompt(
                theme_text, style_for_stencil
            )
            white_seed = _build_white_seed_jpeg(1024)

            ASYM_THRESHOLD = 0.18
            stencil_blob: Optional[bytes] = None
            stencil_err: Optional[str] = None
            for attempt in range(2):
                attempt_seed = random.randint(1, 999_999_999)
                print(
                    f"[COUPLE-SPLIT] prunaai stencil attempt {attempt + 1} "
                    f"theme={theme_text!r} seed={attempt_seed}"
                )
                blob, err = await _replicate_p_image_edit(
                    client, [white_seed], stencil_prompt, attempt_seed
                )
                if not blob:
                    stencil_err = err or "Stencil generation failed"
                    continue
                score = _stencil_asymmetry_score(blob)
                print(
                    f"[COUPLE-SPLIT] stencil attempt {attempt + 1} "
                    f"asymmetry={score:.3f} (threshold={ASYM_THRESHOLD})"
                )
                stencil_blob = blob
                stencil_err = None
                if score >= ASYM_THRESHOLD:
                    break
                if attempt == 0:
                    print(
                        "[COUPLE-SPLIT] stencil came back near-symmetric, "
                        "retrying with new seed"
                    )

            if not stencil_blob:
                return None, (stencil_err or "Stencil generation failed")

            left_stencil_jpeg, right_stencil_jpeg = _split_stencil_at_midline(
                stencil_blob
            )
            try:
                healed_a = _render_half_on_skin_canvas(left_stencil_jpeg, "left")
                healed_b = _render_half_on_skin_canvas(right_stencil_jpeg, "right")
                print("[COUPLE-SPLIT] split + skin-canvas render complete")
            except Exception as ex:  # pragma: no cover
                return None, f"Couple half render failed: {ex}"
        else:
            # matching_pair: parallel two-body edits, two complete designs.
            a_task = _run_single_edit(image_a_jpeg, prompt_a, seed_a, client)
            b_task = _run_single_edit(image_b_jpeg, prompt_b, seed_b, client)
            (blob_a, err_a), (blob_b, err_b) = await asyncio.gather(a_task, b_task)
            if not blob_a or not blob_b:
                msg = err_a or err_b or "Couple generation failed"
                return None, msg
            healed_a = heal_if_pair(image_a_jpeg, blob_a, lock_canvas=True)
            healed_b = heal_if_pair(image_b_jpeg, blob_b, lock_canvas=True)

    pair_jpeg = _compose_side_by_side(healed_a, healed_b)

    return (
        {
            "pair_image_base64": base64.b64encode(pair_jpeg).decode("ascii"),
            "left_image_base64": base64.b64encode(healed_a).decode("ascii"),
            "right_image_base64": base64.b64encode(healed_b).decode("ascii"),
            "media_type": "image/jpeg",
            "pair_spec": pair_spec,
            "seed_a": seed_a,
            "seed_b": seed_b,
        },
        None,
    )


KONTEXT_MULTI_PREDICTIONS_URL = (
    "https://api.replicate.com/v1/models/flux-kontext-apps/"
    "multi-image-kontext-max/predictions"
)
KONTEXT_POLL_INTERVAL_SEC = 1.0
KONTEXT_POLL_MAX_ATTEMPTS = 90  # Kontext Max usually completes in 15-40s

# Prompt for the Kontext multi-image placement call. Image 1 = body photo,
# image 2 = the half-stencil we want planted on the body.
#
# We are extremely defensive here: the half-stencil looks like an
# incomplete picture (left half of a phoenix etc.) and image-edit models'
# instinct is to "fix" it into a complete bilateral subject. The prompt
# repeatedly forbids that and locks the design's shape to the second
# image's exact silhouette.
KONTEXT_HALF_PLACEMENT_PROMPT = (
    "Apply the tattoo design from the second image to the visible body "
    "part of the person in the first image, as a realistic professional "
    "healed tattoo. The ink must sit ON the skin with proper dermal "
    "absorption, natural lighting matching the surrounding skin, and "
    "follow the body's curvature. The tattoo MUST be placed on bare skin "
    "of the body part — NEVER on background, clothing, jewelry, or "
    "outside the body. Center it on the body part with comfortable margin "
    "from the edges. The design's shape, silhouette, proportions and "
    "orientation must match the second image EXACTLY — DO NOT add any "
    "elements that are not in the second image, DO NOT complete missing "
    "halves, DO NOT mirror, DO NOT redraw it as a complete bilateral "
    "subject. Treat the second image as a fixed sticker shape. Keep every "
    "other pixel of the first image identical (face, clothing, background, "
    "lighting). No text, letters, watermarks, logos or pseudo-glyphs."
)


async def _replicate_kontext_multi(
    client: httpx.AsyncClient,
    image_1: bytes,
    image_2: bytes,
    prompt: str,
    seed: int,
) -> tuple[Optional[bytes], Optional[str]]:
    """flux-kontext-apps/multi-image-kontext-max — combines two images.

    Pricing: ~$0.08 per output (Replicate). Returns the rendered PNG bytes
    or (None, error_msg) on any failure. Polls up to 90s.
    """
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return None, "REPLICATE_API_TOKEN not configured"
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "input_image_1": _b64_image(image_1),
            "input_image_2": _b64_image(image_2),
            "prompt": prompt,
            "aspect_ratio": "match_input_image",
            "seed": seed,
            "output_format": "png",
            "safety_tolerance": 2,
        }
    }
    try:
        r = await client.post(
            KONTEXT_MULTI_PREDICTIONS_URL,
            headers=headers,
            json=payload,
            timeout=httpx.Timeout(180.0),
        )
        if r.status_code not in (200, 201):
            return None, f"kontext start error {r.status_code}: {r.text[:300]}"

        pred = r.json()
        output = pred.get("output")
        status = pred.get("status")
        poll_url = (pred.get("urls") or {}).get("get")
        pred_id = pred.get("id")
        if not poll_url and pred_id:
            poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"

        if output is None and poll_url:
            for _ in range(KONTEXT_POLL_MAX_ATTEMPTS):
                await asyncio.sleep(KONTEXT_POLL_INTERVAL_SEC)
                pr = await client.get(
                    poll_url, headers=headers, timeout=httpx.Timeout(60.0)
                )
                if pr.status_code != 200:
                    continue
                pj = pr.json()
                status = pj.get("status")
                if status == "succeeded":
                    output = pj.get("output")
                    break
                if status in ("failed", "canceled"):
                    return None, f"kontext {status}: {str(pj.get('error', ''))[:300]}"
            if output is None:
                return None, f"kontext poll timed out (status={status})"

        if not output:
            return None, f"kontext returned no output (status={status})"
        url = output if isinstance(output, str) else output[0]
        img = await client.get(url, timeout=httpx.Timeout(60.0))
        if img.status_code != 200:
            return None, f"kontext download failed: {img.status_code}"
        return img.content, None
    except httpx.RequestError as e:
        return (
            None,
            f"kontext network error: {type(e).__name__}: {e!s}",
        )


async def _replicate_p_image_edit(
    client: httpx.AsyncClient,
    image_jpegs: list[bytes],
    prompt: str,
    seed: int,
) -> tuple[Optional[bytes], Optional[str]]:
    """
    prunaai/p-image-edit with one or more images. First image sets aspect
    ratio when using match_input_image.
    """
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    if not image_jpegs:
        return None, "no images"
    images = [_b64_image(b) for b in image_jpegs]

    payload = {
        "input": {
            "images": images,
            "prompt": prompt,
            "aspect_ratio": "match_input_image",
            "seed": seed,
            "turbo": True,
        }
    }

    try:
        r = await client.post(
            PREDICTIONS_URL, headers=headers, json=payload, timeout=httpx.Timeout(180.0)
        )
        if r.status_code not in (200, 201):
            return None, f"API error {r.status_code}: {r.text[:400]}"

        result = r.json()
        out = result.get("output")
        if out:
            url = out if isinstance(out, str) else out[0]
            img_r = await client.get(url, timeout=httpx.Timeout(60.0))
            if img_r.status_code == 200:
                return img_r.content, None

        pred_id = result.get("id")
        if not pred_id:
            return None, "No prediction id"

        get_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
        for _ in range(POLL_MAX_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SEC)
            pr = await client.get(get_url, headers=headers, timeout=httpx.Timeout(60.0))
            if pr.status_code != 200:
                continue
            data = pr.json()
            status = data.get("status")
            if status == "succeeded":
                output = data.get("output")
                if output:
                    url = output if isinstance(output, str) else output[0]
                    img_r = await client.get(url, timeout=httpx.Timeout(60.0))
                    if img_r.status_code == 200:
                        return img_r.content, None
                return None, "Empty output"
            if status == "failed":
                return None, str(data.get("error", "failed"))
            if status == "canceled":
                return None, "canceled"

        return None, "timeout"
    except httpx.RequestError as e:
        # DNS failure, no route, reset — browser often misreports as CORS if
        # the handler crashes with no JSON body.
        return (
            None,
            f"Network error: cannot reach Replicate. Check internet, VPN, and DNS. "
            f"Details: {type(e).__name__}: {e!s}",
        )


async def _run_single_edit(
    body_jpeg: bytes,
    prompt: str,
    seed: int,
    client: httpx.AsyncClient,
    reference_jpeg: Optional[bytes] = None,
) -> tuple[Optional[bytes], Optional[str]]:
    jpegs = [body_jpeg] + ([reference_jpeg] if reference_jpeg else [])
    return await _replicate_p_image_edit(client, jpegs, prompt, seed)


# ---------------------------------------------------------------------------
# Faded-tattoo flow — age an existing tattoo photograph
# ---------------------------------------------------------------------------
#
# Strategy: Flux Kontext Pro for the realistic aging look (texture
# breakdown, ink absorption into skin, fine-detail loss) with the
# deterministic local CV pipeline as a guaranteed fallback / amplifier.
#
# Why Flux Kontext Pro:
#   - prunaai/p-image-edit interprets "age this tattoo" as "don't
#     change much" and ships back a near-identical photo (we tried
#     this — user complained "no difference").
#   - Local CV pipeline only does color / blur / dermal blend; it
#     cannot simulate the texture changes of real long-term ink wear.
#   - flux-kontext-pro is BFL's instruction-following image editor;
#     pricing ~$0.04/image, holds composition while making strong
#     visible changes.
#
# Pricing: 1 × flux-kontext-pro per variant (~$0.04).

FLUX_KONTEXT_PRO_URL = (
    "https://api.replicate.com/v1/models/black-forest-labs/"
    "flux-kontext-pro/predictions"
)
FLUX_KONTEXT_PRO_POLL_INTERVAL_SEC = 1.0
FLUX_KONTEXT_PRO_POLL_MAX_ATTEMPTS = 120


_FADE_YEARS_BY_STRENGTH = {
    "subtle": "2 to 3",
    "moderate": "5 to 7",
    "heavy": "10 to 15",
}

_FADE_INTENSITY_DESC = {
    "subtle": (
        "early-stage wear. Tattoo lines have started to soften slightly "
        "at the edges; the ink density is a touch lower than fresh ink; "
        "very fine detail looks marginally less crisp."
    ),
    "moderate": (
        "mid-life wear. Tattoo lines are noticeably softer with a small "
        "bloom into the surrounding skin; the ink looks lighter and "
        "less dense; some fine detail is reduced; the blacks read as a "
        "softened blue-black instead of jet-black."
    ),
    "heavy": (
        "long-term wear. Tattoo lines have visibly bloomed and softened; "
        "the ink density is clearly reduced so skin texture (pores, "
        "fine hair, micro-wrinkles) shows through the ink; fine "
        "details have partially dropped out; the blacks read as a "
        "soft blue-grey patina rather than fresh black ink. The design "
        "is still recognisable but clearly aged."
    ),
}


def _use_kontext_for_fade() -> bool:
    """
    Default ON: AI provides richer aging texture/detail than pure CV.
    We still hard-lock global colors by compositing AI edits only inside
    detected tattoo ink regions.

    Set TATTOO_FADE_USE_KONTEXT=0 to force local-only mode.
    """
    raw = os.environ.get("TATTOO_FADE_USE_KONTEXT", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return True


def _build_kontext_fade_prompt(strength: str) -> str:
    s = (strength or "moderate").strip().lower()
    if s not in _FADE_YEARS_BY_STRENGTH:
        s = "moderate"
    years = _FADE_YEARS_BY_STRENGTH[s]
    intensity = _FADE_INTENSITY_DESC[s]

    return (
        f"Output a FULL-COLOUR photograph (not black-and-white, not "
        f"monochrome, not sepia, not desaturated). The output must be "
        f"the SAME photograph as the input, with exactly the same "
        f"composition, framing, body part, pose, lighting, background "
        f"and natural warm skin tones. The skin stays its real flesh "
        f"colour. The surrounding scene keeps every existing colour. "
        f"The ONLY thing that changes is the appearance of the tattoo "
        f"ink itself.\n"
        f"\n"
        f"Inside the tattoo's ink lines (and ONLY there), simulate "
        f"about {years} years of natural healing and skin turnover — "
        f"{intensity}\n"
        f"\n"
        f"Specific changes that apply ONLY to the ink lines (never to "
        f"skin or background):\n"
        f"- Soften the line edges so they bloom slightly into the "
        f"surrounding skin (no crisp stencil edges).\n"
        f"- Lower the ink density so the design reads visibly lighter "
        f"and skin texture shows through it more.\n"
        f"- Shift the BLACKS within the design toward a soft blue-grey "
        f"or blue-black patina (never warm grey, brown, sepia, green "
        f"or yellow).\n"
        f"- Make any coloured pigments inside the design read a touch "
        f"less vivid (warm reds and yellows lose vibrancy faster than "
        f"cool blues and greens) — but only inside the tattoo, not on "
        f"surrounding skin or scenery.\n"
        f"- Partially drop the smallest fine details; preserve the "
        f"overall silhouette, layout and subject of the design.\n"
        f"\n"
        f"DO NOT change the global colour of the photograph. DO NOT "
        f"convert to grayscale. DO NOT desaturate the skin, the arm, "
        f"the clothing, the wall, the background, or any pixel that "
        f"is not part of the tattoo ink. DO NOT add scars, redness, "
        f"peeling skin, blood, irritation, or healing artefacts. DO "
        f"NOT redraw, swap, or move the design.\n"
        f"\n"
        f"Result: a colour photograph of the same person and same "
        f"tattoo, aged by roughly {years} years, with skin and "
        f"environment colours UNTOUCHED. No text, watermark, logo, "
        f"border, caption or UI chrome anywhere in the frame."
    )


async def _replicate_flux_kontext_pro(
    client: httpx.AsyncClient,
    image_jpeg: bytes,
    prompt: str,
    seed: int,
) -> tuple[Optional[bytes], Optional[str]]:
    """black-forest-labs/flux-kontext-pro — single-image text-driven edit."""
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return None, "REPLICATE_API_TOKEN not configured"
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "input_image": _b64_image(image_jpeg),
            "aspect_ratio": "match_input_image",
            "seed": seed,
            "output_format": "jpg",
            "safety_tolerance": 2,
            "prompt_upsampling": False,
        }
    }
    try:
        r = await client.post(
            FLUX_KONTEXT_PRO_URL,
            headers=headers,
            json=payload,
            timeout=httpx.Timeout(180.0),
        )
        if r.status_code not in (200, 201):
            return None, f"kontext-pro start error {r.status_code}: {r.text[:300]}"

        pred = r.json()
        output = pred.get("output")
        status = pred.get("status")
        poll_url = (pred.get("urls") or {}).get("get")
        pred_id = pred.get("id")
        if not poll_url and pred_id:
            poll_url = f"https://api.replicate.com/v1/predictions/{pred_id}"

        if output is None and poll_url:
            for _ in range(FLUX_KONTEXT_PRO_POLL_MAX_ATTEMPTS):
                await asyncio.sleep(FLUX_KONTEXT_PRO_POLL_INTERVAL_SEC)
                pr = await client.get(
                    poll_url, headers=headers, timeout=httpx.Timeout(60.0)
                )
                if pr.status_code != 200:
                    continue
                pj = pr.json()
                status = pj.get("status")
                if status == "succeeded":
                    output = pj.get("output")
                    break
                if status in ("failed", "canceled"):
                    return None, f"kontext-pro {status}: {str(pj.get('error', ''))[:300]}"
            if output is None:
                return None, f"kontext-pro poll timed out (status={status})"

        if not output:
            return None, f"kontext-pro returned no output (status={status})"
        url = output if isinstance(output, str) else output[0]
        img = await client.get(url, timeout=httpx.Timeout(60.0))
        if img.status_code != 200:
            return None, f"kontext-pro download failed: {img.status_code}"
        return img.content, None
    except httpx.RequestError as e:
        return None, f"kontext-pro network error: {type(e).__name__}: {e!s}"


def _mean_pixel_diff(a_jpeg: bytes, b_jpeg: bytes) -> float:
    """Cheap perceptual delta — mean absolute pixel diff in [0..255].

    Used to detect "model returned almost the same photo" so we can
    amplify the result with the local CV fade as a safety net.
    """
    try:
        import numpy as np

        a = np.array(Image.open(io.BytesIO(a_jpeg)).convert("RGB"))
        b_img = Image.open(io.BytesIO(b_jpeg)).convert("RGB").resize(a.shape[:2][::-1])
        b = np.array(b_img)
        return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).mean())
    except Exception:
        return 0.0


def _saturation_drop_ratio(a_jpeg: bytes, b_jpeg: bytes) -> float:
    """Mean HSV-saturation of `b` divided by mean HSV-saturation of `a`.

    1.0 → identical saturation. <0.5 → b is heavily desaturated (B&W /
    monochrome / sepia). Used to detect Kontext globally killing colour.
    """
    try:
        import numpy as np

        a_pil = Image.open(io.BytesIO(a_jpeg)).convert("RGB")
        b_pil = Image.open(io.BytesIO(b_jpeg)).convert("RGB").resize(a_pil.size)
        a = np.array(a_pil)
        b = np.array(b_pil)
        a_hsv = cv_rgb2hsv(a)
        b_hsv = cv_rgb2hsv(b)
        sa = float(a_hsv[..., 1].mean()) + 1e-3
        sb = float(b_hsv[..., 1].mean())
        return sb / sa
    except Exception:
        return 1.0


def cv_rgb2hsv(rgb):  # pragma: no cover
    """Tiny shim so we don't import cv2 at module top-level."""
    import cv2

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)


async def generate_faded_tattoo(
    image_jpeg: bytes,
    answers: dict,
    num_concepts: int = 1,
) -> tuple[list[dict], Optional[str]]:
    """
    Age an existing tattoo photograph using Flux Kontext Pro, with a
    deterministic local CV pipeline as fallback / amplifier when the
    model's output is too conservative.

    Same return shape as `generate_tattoo_concepts`.
    """
    from .tattoo_fade import apply_local_fade, composite_ai_fade_on_tattoo

    strength = str(answers.get("fade_strength") or "moderate").strip().lower()
    if strength not in ("subtle", "moderate", "heavy"):
        strength = "moderate"

    n = max(1, int(num_concepts or 1))
    prompt = _build_kontext_fade_prompt(strength)

    # Threshold below which we consider Kontext "barely changed the
    # photo" and apply a top-up local fade. Tuned per-strength: heavier
    # fade should produce a larger pixel delta in the AI output.
    AMPLIFY_THRESHOLD = {"subtle": 6.0, "moderate": 12.0, "heavy": 18.0}[strength]

    concepts: list[dict] = []
    err: Optional[str] = None

    use_kontext = _use_kontext_for_fade()
    if use_kontext and REPLICATE_API_TOKEN and len(REPLICATE_API_TOKEN) >= 10:
        seeds = [
            int.from_bytes(os.urandom(4), "big") % 999_999_999 for _ in range(n)
        ]
        print(
            f"[FADE] flux-kontext-pro strength={strength!r} variants={n} "
            f"seeds={seeds}"
        )
        async with httpx.AsyncClient(limits=HTTP_LIMITS, http2=False) as client:
            tasks = [
                _replicate_flux_kontext_pro(client, image_jpeg, prompt, seed)
                for seed in seeds
            ]
            results = await asyncio.gather(*tasks)

        for i, (blob, e) in enumerate(results):
            if not blob:
                if e and not err:
                    err = e
                print(f"[FADE] kontext-pro v{i} failed: {e!r}")
                continue
            diff = _mean_pixel_diff(image_jpeg, blob)
            sat_ratio = _saturation_drop_ratio(image_jpeg, blob)
            print(
                f"[FADE] kontext-pro v{i} mean_diff={diff:.2f} "
                f"sat_ratio={sat_ratio:.2f}"
            )

            # Saturation guard: if kontext globally killed colour
            # (B&W / sepia / monochrome) we reject its output and
            # fall back to local CV fade on the ORIGINAL image so
            # the photograph keeps its natural skin and scene colours.
            if sat_ratio < 0.55:
                print(
                    f"[FADE] kontext-pro v{i} desaturated photo globally "
                    f"(sat_ratio={sat_ratio:.2f}); using local CV pipeline"
                )
                try:
                    blob = apply_local_fade(image_jpeg, strength)
                except Exception as ex:  # pragma: no cover
                    print(f"[FADE] local fallback failed: {ex}")
                    continue
            elif diff < AMPLIFY_THRESHOLD:
                print(
                    f"[FADE] kontext-pro v{i} too conservative "
                    f"(<{AMPLIFY_THRESHOLD}), local fade from original (not stacked on AI)"
                )
                try:
                    blob = apply_local_fade(image_jpeg, strength)
                except Exception as ex:  # pragma: no cover
                    print(f"[FADE] local boost failed: {ex}")
            else:
                # Guardrail: even if AI color-grades the whole photo, we only
                # accept changes inside detected tattoo ink on the original.
                try:
                    blob = composite_ai_fade_on_tattoo(image_jpeg, blob, strength)
                except Exception as ex:  # pragma: no cover
                    print(f"[FADE] masked AI composite failed: {ex}")
                    blob = apply_local_fade(image_jpeg, strength)
            concepts.append(
                {
                    "variant_index": i,
                    "seed": seeds[i],
                    "image_base64": base64.b64encode(blob).decode("ascii"),
                    "media_type": "image/jpeg",
                }
            )

    if not concepts:
        # Either no token, all kontext calls failed, or zero successes —
        # fall back to the local CV pipeline so the user always gets a
        # result even if the API is down.
        if use_kontext:
            print(f"[FADE] falling back to local CV pipeline for {n} variant(s)")
        else:
            print(f"[FADE] using local CV pipeline for {n} variant(s) (kontext disabled)")
        for i in range(n):
            try:
                faded = apply_local_fade(image_jpeg, strength)
            except Exception as ex:  # pragma: no cover
                return [], f"Local fade fallback failed: {type(ex).__name__}: {ex}"
            concepts.append(
                {
                    "variant_index": i,
                    "seed": 0,
                    "image_base64": base64.b64encode(faded).decode("ascii"),
                    "media_type": "image/jpeg",
                }
            )

    return concepts, None


async def generate_tattoo_concepts(
    body_jpeg: bytes,
    flow_id: str,
    answers: dict,
    num_concepts: int = 1,
    reference_jpeg: Optional[bytes] = None,
) -> tuple[list[dict], Optional[str]]:
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return [], "REPLICATE_API_TOKEN not configured"

    n = max(1, min(4, int(num_concepts)))
    seeds = [random.randint(1, 999_999_999) for _ in range(n)]
    # Fresh per-request salt so two identical user submissions don't pick
    # the exact same motifs (was the "always lion / always dragon / always
    # heart" complaint). Variants within the same request still see the
    # same salt — that's correct, what changes between them is variant_index.
    run_salt = random.randint(0, 1_000_000)

    style_label = answers.get("style") or answers.get("conversion_style") or "auto"
    print(
        f"[TATTOO] flow={flow_id} style={style_label} concepts={n} "
        f"ref_attached={reference_jpeg is not None} run_salt={run_salt} "
        f"photo_stencil={_use_photo_convert_stencil()!s}"
    )

    prompts = [
        build_tattoo_edit_prompt(
            flow_id,
            answers,
            variant_index=i,
            reference_image_attached=reference_jpeg is not None,
            run_salt=run_salt,
        )
        for i in range(n)
    ]
    for i, p in enumerate(prompts):
        print(f"[TATTOO] variant {i}, seed {seeds[i]}, flow={flow_id}")
        if _log_prompt_bodies():
            print(f"\n{'='*60}")
            print(p)
            print(f"{'='*60}\n")

    async with httpx.AsyncClient(limits=HTTP_LIMITS, http2=False) as client:
        # Optional: stencil (reference only) + local composite — not default; two-image
        # call matches the higher-quality "full piece on skin" look most users want.
        if (
            _use_photo_convert_stencil()
            and flow_id == "photo_convert"
            and reference_jpeg is not None
        ):
            style_key = resolve_style("photo_convert", answers)
            stencil_prompt = build_photo_convert_stencil_prompt(style_key)
            stencil_seed = random.randint(1, 999_999_999)
            print(
                f"[TATTOO] photo_convert STENCIL+COMPOSITE (style={style_key}, seed={stencil_seed})"
            )
            if _log_prompt_bodies():
                print(f"[TATTOO] stencil prompt (trunc): {stencil_prompt[:400]}...")
            st_blob, st_err = await _replicate_p_image_edit(
                client, [reference_jpeg], stencil_prompt, stencil_seed
            )
            if st_blob and len(st_blob) > 200:
                st_out: list[dict] = []
                _br = str(answers.get("body_region") or "from_photo")
                _co = str(answers.get("coverage") or "medium")
                for i in range(n):
                    try:
                        comp = composite_stencil_on_body(
                            body_jpeg,
                            st_blob,
                            _br,
                            _co,
                            variant_index=i,
                            style_key=style_key,
                        )
                    except Exception as ex:  # pragma: no cover
                        print(f"[TATTOO] composite failed v{i}: {ex}")
                        comp = b""
                    if comp and len(comp) > 200:
                        st_out.append(
                            {
                                "variant_index": i,
                                "seed": stencil_seed,
                                "image_base64": base64.b64encode(comp).decode("ascii"),
                                "media_type": "image/jpeg",
                            }
                        )
                if st_out:
                    return st_out, None
                print(
                    "[TATTOO] stencil+composite returned empty; "
                    "falling back to single two-image p-image-edit"
                )
            else:
                print(
                    f"[TATTOO] stencil step failed ({st_err}); "
                    f"falling back to two-image p-image-edit"
                )

        tasks = [
            _run_single_edit(
                body_jpeg,
                prompts[i],
                seeds[i],
                client,
                reference_jpeg=reference_jpeg,
            )
            for i in range(n)
        ]
        results = await asyncio.gather(*tasks)

    concepts = []
    errors: list[str] = []
    for i, (blob, err) in enumerate(results):
        if blob:
            if flow_id == "scar_coverup":
                healed = composite_scar_tattoo(body_jpeg, blob)
            else:
                # Two-image photo_convert: do NOT hard-lock to body pixels (that was
                # erasing the rich ink the model had drawn). Stencil path unchanged.
                lock = not (flow_id == "photo_convert" and reference_jpeg is not None)
                healed = heal_if_pair(body_jpeg, blob, lock_canvas=lock)
            concepts.append(
                {
                    "variant_index": i,
                    "seed": seeds[i],
                    "image_base64": base64.b64encode(healed).decode("ascii"),
                    "media_type": "image/jpeg",
                }
            )
        elif err:
            errors.append(err)

    if not concepts:
        return [], errors[0] if errors else "All generations failed"

    return concepts, None
