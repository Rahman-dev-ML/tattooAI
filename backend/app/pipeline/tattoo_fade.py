"""
Deterministic tattoo-fade pipeline — pure OpenCV + NumPy + Pillow.

Why local, not AI:
  Image-edit models (prunaai/p-image-edit, flux-kontext, etc.) interpret
  "age this tattoo a few years" as "don't change much" and ship back a
  near-identical photo. Real fade is a deterministic optical phenomenon,
  so we model it directly.

Pipeline (everything is applied ONLY inside the detected ink area, with
a 1–2 px feather so anti-aliasing reads naturally and the surrounding
skin stays 100 % untouched):

  1. Detect ink in HSV (saturation OR very low value OR non-skin hue).
  2. Compute a HARD binary ink mask, clean it morphologically, feather
     by ~0.2 % of the image's short side. (Previously this feather was
     ~1.2 % — wide enough to drag a halo of skin INTO the fade, which
     is the bug you saw where the whole arm went pale.)
  3. Build a faded version of the photo:
        - Gaussian blur for line bloom / detail loss
        - Lower HSV saturation (same hue family, duller — not a new palette)
        - Blue-grey patina ONLY on originally *neutral/black* ink (carbon)
        - Ink “thinning” via Lab lightness + mild ab pull toward neutral — never
          full RGB blend into skin (that was shifting yellow→peach, blue→mud)
  4. Composite the faded version over the original via the tight mask.

Strength buckets map to deterministic numeric parameters; same input +
same strength always returns the same JPEG.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class _FadeParams:
    blur: float    # gaussian sigma factor for line bloom (px @ 1024 short side)
    # HSV S-channel multiplier is (1 - chroma_loss): keeps *hue*, unlike RGB→grey mix
    chroma_loss: float  # 0..1 — how much less vivid the ink reads (not B&W)
    blue: float    # patina on *neutral* ink only (blacks → blue-grey), not on color ink
    # Lab: L moves toward skin L; ab scaled toward neutral (same hue angle, less chroma)
    fade: float    # ink thinning strength (lightness + mild chroma collapse)


# Tuned conservatively. "Heavy" represents a 10-15 year old tattoo that
# is clearly aged but still recognisable — it should NOT obliterate the
# design or wash the surrounding arm to grey.
_PARAMS: dict[str, _FadeParams] = {
    "subtle":   _FadeParams(blur=0.7, chroma_loss=0.11, blue=0.12, fade=0.07),
    "moderate": _FadeParams(blur=1.6, chroma_loss=0.20, blue=0.20, fade=0.14),
    "heavy":    _FadeParams(blur=2.8, chroma_loss=0.30, blue=0.24, fade=0.22),
}


def _detect_ink_mask_hard(rgb: np.ndarray) -> np.ndarray:
    """Binary uint8 mask {0, 255}; 255 = ink, 0 = bare skin / background."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h = hsv[..., 0].astype(np.int32)
    s = hsv[..., 1].astype(np.int32)
    v = hsv[..., 2].astype(np.int32)

    # Skin usually sits in warm-red/orange hue, medium/high V. Build a broad
    # "likely skin" prior first; then detect ink as off-skin pigment + dark lines.
    skin_like = ((h <= 28) | (h >= 170)) & (s >= 20) & (s <= 190) & (v >= 45)
    shadowy_skin = skin_like & (v < 125) & (s < 125)

    # Colored ink: chromatic and not skin-like.
    colored_ink = (~skin_like) & (s > 42)
    # Dark blackwork lines: very low value, but reject soft skin shadows.
    blackwork_ink = (v < 72) & (~shadowy_skin)
    # Dark chromatic ink (blue/green/purple etc.) with enough saturation.
    dark_chromatic_ink = (v < 92) & (s > 34) & (~shadowy_skin) & (~skin_like)

    raw = (colored_ink | blackwork_ink | dark_chromatic_ink).astype(np.uint8) * 255

    k = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, k, iterations=2)
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, k, iterations=1)

    # If mask explodes (covers too much), force structure by requiring edges.
    coverage = float(cleaned.mean()) / 255.0
    if coverage > 0.38:
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, threshold1=42, threshold2=128)
        edges = cv2.dilate(edges, k, iterations=1)
        strict = ((cleaned > 0) & (edges > 0)).astype(np.uint8) * 255
        strict = cv2.morphologyEx(strict, cv2.MORPH_CLOSE, k, iterations=2)
        cleaned = cv2.morphologyEx(strict, cv2.MORPH_OPEN, k, iterations=1)

    # Keep medium-sized connected components only; rejects giant global regions.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, 8)
    area = cleaned.shape[0] * cleaned.shape[1]
    keep = np.zeros_like(cleaned)
    min_a = max(24, int(area * 0.00008))
    max_a = int(area * 0.35)
    for lbl in range(1, num_labels):
        a = int(stats[lbl, cv2.CC_STAT_AREA])
        if min_a <= a <= max_a:
            keep[labels == lbl] = 255

    # Pull the mask off surrounding skin edge slightly (prevents halo bleed).
    return cv2.erode(keep, k, iterations=1)


def _sample_skin_color(rgb: np.ndarray, ink_hard: np.ndarray) -> np.ndarray:
    """Per-channel median of pixels that are NOT ink — the local skin tone."""
    skin_pixels = rgb[ink_hard == 0]
    if skin_pixels.size == 0:
        return np.array([200, 165, 140], dtype=np.float32)
    pixels = skin_pixels.reshape(-1, 3).astype(np.float32)
    return np.median(pixels, axis=0)


def _lab_L_scalar(rgb_color: np.ndarray) -> float:
    """OpenCV L channel for one RGB triplet (0–255)."""
    patch = np.uint8([[np.clip(rgb_color, 0, 255).astype(np.uint8)]])
    lab = cv2.cvtColor(patch, cv2.COLOR_RGB2LAB)
    return float(lab[0, 0, 0])


def apply_local_fade(image_jpeg: bytes, strength: str) -> bytes:
    """Age the tattoo in `image_jpeg` according to the strength bucket.

    `strength` ∈ {"subtle", "moderate", "heavy"}; anything else → moderate.
    Returns a JPEG. Pure CPU, no network, deterministic.
    """
    p = _PARAMS.get((strength or "moderate").strip().lower(), _PARAMS["moderate"])

    pil = Image.open(io.BytesIO(image_jpeg)).convert("RGB")
    rgb = np.array(pil)
    h, w = rgb.shape[:2]
    short_side = min(h, w)

    ink_hard = _detect_ink_mask_hard(rgb)
    skin_color = _sample_skin_color(rgb, ink_hard)

    sigma_blur = p.blur * (max(h, w) / 1024.0)
    work = rgb.astype(np.float32)

    if sigma_blur > 0.3:
        work = cv2.GaussianBlur(work, (0, 0), sigmaX=sigma_blur)

    # --- Saturation down (per hue bucket): color ink keeps its family; reds fade faster ---
    w_u8 = np.clip(work, 0.0, 255.0).astype(np.uint8)
    w_hsv = cv2.cvtColor(w_u8, cv2.COLOR_RGB2HSV).astype(np.float32)
    oh = w_hsv[..., 0]  # 0..179 OpenCV
    sat_mul = max(0.0, 1.0 - p.chroma_loss)
    # Orange / warm yellow-red band: extra chroma loss (reference: red drops first)
    red_extra = 0.12
    is_warm_red = (oh < 28) | (oh > 158)
    sat_mul_eff = np.where(is_warm_red, sat_mul * (1.0 - red_extra), sat_mul)
    w_hsv[..., 1] = np.clip(w_hsv[..., 1] * sat_mul_eff, 0.0, 255.0)
    work = cv2.cvtColor(w_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

    # --- Patina: ONLY on ink that was already neutral / black (low original S) ---
    orig_hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    orig_s = orig_hsv[..., 1]
    # 1 at grey/black ink, ~0 on saturated Starry-Night yellows/blues
    neutral_gate = np.clip(1.0 - orig_s / 72.0, 0.0, 1.0) ** 1.35
    orig_luma = rgb.astype(np.float32).mean(axis=2)
    dark_gate = np.clip((125.0 - orig_luma) / 125.0, 0.0, 1.0)
    patina_w = np.clip(p.blue * neutral_gate * dark_gate, 0.0, 1.0)[..., None]
    cool_tint = np.array([0.93, 0.98, 1.08], dtype=np.float32)
    work = work * (1.0 - patina_w) + (work * cool_tint) * patina_w

    # --- Thinning: Lab L toward skin L + slight ab shrink (never RGB→skin blend) ---
    w_u8b = np.clip(work, 0.0, 255.0).astype(np.uint8)
    lab = cv2.cvtColor(w_u8b, cv2.COLOR_RGB2LAB).astype(np.float32)
    L_tgt = _lab_L_scalar(skin_color)
    fl = p.fade
    lab[..., 0] = lab[..., 0] * (1.0 - fl) + L_tgt * fl
    ab_scale = 1.0 - fl * 0.35
    lab[..., 1] = (lab[..., 1] - 128.0) * ab_scale + 128.0
    lab[..., 2] = (lab[..., 2] - 128.0) * ab_scale + 128.0
    lab[..., 0] = np.clip(lab[..., 0], 0.0, 255.0)
    work = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB).astype(np.float32)

    feather_sigma = max(0.8, short_side * 0.0025)
    mask_f = ink_hard.astype(np.float32) / 255.0
    mask_soft = cv2.GaussianBlur(mask_f, (0, 0), sigmaX=feather_sigma)
    mask_soft = np.clip(mask_soft, 0.0, 1.0)[..., None]

    final = rgb.astype(np.float32) * (1.0 - mask_soft) + work * mask_soft
    out = np.clip(final, 0.0, 255.0).astype(np.uint8)

    res = Image.fromarray(out)
    buf = io.BytesIO()
    res.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()


def composite_ai_fade_on_tattoo(
    base_jpeg: bytes,
    ai_jpeg: bytes,
    strength: str,
) -> bytes:
    """
    Keep AI aging edits ONLY where tattoo ink exists on the base image.

    This prevents model-wide color grading from affecting skin/background.
    Inside colored tattoo pigments, preserve the original hue family so
    "faded" reads as lower density / lower contrast, not recolored art.
    """
    p = _PARAMS.get((strength or "moderate").strip().lower(), _PARAMS["moderate"])
    base = np.array(Image.open(io.BytesIO(base_jpeg)).convert("RGB"))
    ai = np.array(Image.open(io.BytesIO(ai_jpeg)).convert("RGB"))
    if ai.shape[:2] != base.shape[:2]:
        ai = cv2.resize(ai, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_LANCZOS4)

    ink_hard = _detect_ink_mask_hard(base)
    short_side = min(base.shape[0], base.shape[1])
    feather_sigma = max(0.8, short_side * 0.0025)
    mask_soft = cv2.GaussianBlur(
        (ink_hard.astype(np.float32) / 255.0), (0, 0), sigmaX=feather_sigma
    )
    mask_soft = np.clip(mask_soft, 0.0, 1.0)[..., None]

    # Hue protection for colored ink: keep pigment family from base.
    base_hsv = cv2.cvtColor(base, cv2.COLOR_RGB2HSV).astype(np.float32)
    ai_hsv = cv2.cvtColor(ai, cv2.COLOR_RGB2HSV).astype(np.float32)
    base_s = base_hsv[..., 1]
    color_gate = np.clip(base_s / 95.0, 0.0, 1.0)[..., None]
    hue_keep = 0.88  # strong lock for colored pigments
    ai_hsv[..., 0] = ai_hsv[..., 0] * (1.0 - hue_keep * color_gate[..., 0]) + base_hsv[
        ..., 0
    ] * (hue_keep * color_gate[..., 0])
    # Never let AI oversaturate; fading should reduce or keep saturation.
    sat_cap = base_hsv[..., 1] * (1.0 - p.chroma_loss * 0.35)
    ai_hsv[..., 1] = np.minimum(ai_hsv[..., 1], sat_cap)
    ai_hsv[..., 1] = np.clip(ai_hsv[..., 1], 0.0, 255.0)
    ai_adj = cv2.cvtColor(ai_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

    # Strength controls how much AI texture/detail shift we accept.
    ai_mix = {"subtle": 0.42, "moderate": 0.58, "heavy": 0.72}.get(
        (strength or "moderate").strip().lower(),
        0.58,
    )
    inside = base.astype(np.float32) * (1.0 - ai_mix) + ai_adj * ai_mix
    out = base.astype(np.float32) * (1.0 - mask_soft) + inside * mask_soft
    out_u8 = np.clip(out, 0.0, 255.0).astype(np.uint8)

    res = Image.fromarray(out_u8)
    buf = io.BytesIO()
    res.save(buf, format="JPEG", quality=93, optimize=True)
    return buf.getvalue()
