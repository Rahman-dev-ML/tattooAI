"""
photo_convert: stencil + multiply composite.

The single two-image p-image-edit call often pastes a flat sticker or redraws
the body. We instead:
  1) Edit the reference alone into black/grey linework on white (tattoo stencil).
  2) Multiply-composite that stencil onto the user's body JPEG (same pixels
     as the upload except under the ink), with placement from body_region.

This matches how real preview tools fake "tattoo on skin" without trusting the
model to edit the photograph in one shot. Compositing uses a dermal-style
luminance blend (not raw multiply) so ink sits *into* the skin a little, with
high-frequency skin texture in ink areas.
"""
from __future__ import annotations

import io
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # graceful fallback if OpenCV not installed

# Normalized anchor (cx, cy) and max design span as fraction of min(body w, h)
# cy ~0.36–0.38 centers a sternum/upper chest piece on typical torso photos.
# INCREASED base_frac values to allow larger tattoos on body parts
_PLACEMENT: dict[str, Tuple[float, float, float]] = {
    "from_photo": (0.50, 0.37, 0.48),
    "chest": (0.50, 0.36, 0.50),
    "ribs": (0.48, 0.42, 0.42),
    "forearm": (0.50, 0.48, 0.44),
    "upper_arm": (0.48, 0.44, 0.42),
    "shoulder": (0.42, 0.36, 0.40),
    "wrist": (0.52, 0.55, 0.28),
    "hand_back": (0.50, 0.50, 0.32),
    "calf": (0.50, 0.46, 0.42),
    "thigh": (0.50, 0.44, 0.48),
    "ankle": (0.50, 0.58, 0.30),
    "upper_back": (0.50, 0.38, 0.46),
    "neck": (0.50, 0.28, 0.24),
    "other": (0.50, 0.40, 0.40),
}

_COVERAGE_TO_FRAC = {
    "small": 0.40,
    "medium": 0.55,
    "large": 0.70,
}

# max_ink in _ink_blend_dermal — INCREASED HEAVILY for BOLD, PROMINENT, ARTISTIC lines.
# Maximum saturation for strong presence and artistic impact on skin.
_INK_MAX_BY_STYLE: dict[str, float] = {
    "fine_line": 0.88,
    "minimalist": 0.80,
    "blackwork": 0.94,
    "traditional": 0.92,
    "japanese": 0.90,
    "realism": 0.90,
    "geometric": 0.88,
    "ornamental": 0.88,
    "script": 0.86,
    "stencil": 0.90,
    "auto": 0.88,
}


def _coverage_frac(coverage: str) -> float:
    c = (coverage or "medium").lower().strip()
    return _COVERAGE_TO_FRAC.get(c, 0.30)


def _open_rgb(jpeg: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(jpeg))
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im


def _ink_blend_dermal(body: Image.Image, layer: Image.Image, *, max_ink: float) -> Image.Image:
    """
    Luminance-based 'ink' mask from white stencil; blend cool black-grey ink
    with skin and mix in high-frequency skin detail where ink is present
    (reads less like a screen sticker than plain multiply).
    """
    b = np.asarray(body, dtype=np.float32)
    # Convert layer to luminance for ink mask
    layer_arr = np.asarray(layer, dtype=np.float32)
    gl = (
        0.299 * layer_arr[:, :, 0]
        + 0.587 * layer_arr[:, :, 1]
        + 0.114 * layer_arr[:, :, 2]
    ) / 255.0
    # 1 = full ink, 0 = clean skin
    t = np.clip(1.0 - gl, 0.0, 1.0) ** 0.85
    t3 = t[:, :, np.newaxis]

    ink = np.array([20.0, 20.0, 28.0], dtype=np.float32)  # cool black
    a = float(max(0.40, min(1.0, max_ink)))
    mixed = b * (1.0 - a * t3) + ink * (a * t3)

    low = np.asarray(
        body.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32
    )
    hf = b - low
    mixed = mixed + hf * 0.14 * t3
    # Tiny pull toward original skin everywhere so pores remain believable
    mixed = 0.03 * b + 0.97 * np.clip(mixed, 0, 255)
    return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8), mode="RGB")


def detect_body_anchor(image_jpeg: bytes) -> Tuple[float, float]:
    """
    Body-part-agnostic placement helper.

    Strategy:
      1) Detect skin pixels using HSV + Y'CbCr ranges (more robust than HSV
         alone — Y'CbCr handles backgrounds with skin-like hues much better).
      2) Clean the mask with morphology (drop scattered noise).
      3) Take the LARGEST connected skin region — usually the body part.
      4) Return its centroid pulled gently toward the image center, clamped
         into a safe central zone so weird crops don't push the tattoo onto
         the edge of the frame.

    Returns (cx, cy) normalized to [0.30, 0.70]. Falls back to (0.50, 0.50)
    if OpenCV is unavailable, the image is unreadable, or no skin region is
    detected (e.g., a heavily filtered or out-of-range photo).
    """
    if cv2 is None:
        return 0.5, 0.5
    try:
        arr = np.frombuffer(image_jpeg, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return 0.5, 0.5
    except Exception:
        return 0.5, 0.5

    h, w = bgr.shape[:2]
    if h == 0 or w == 0:
        return 0.5, 0.5

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    ycc = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

    h_ = hsv[..., 0]
    s_ = hsv[..., 1]
    v_ = hsv[..., 2]
    hsv_mask = ((h_ <= 20) | (h_ >= 160)) & (s_ >= 30) & (s_ <= 200) & (v_ >= 50)

    cr = ycc[..., 1]
    cb = ycc[..., 2]
    ycc_mask = (cr >= 135) & (cr <= 180) & (cb >= 85) & (cb <= 135)

    skin = (hsv_mask & ycc_mask).astype(np.uint8) * 255

    # Drop speckle and close small holes inside the body region.
    kernel = np.ones((5, 5), np.uint8)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, kernel)
    skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, kernel)

    if int(skin.sum()) < 200 * 255:  # too little skin to trust
        return 0.5, 0.5

    num, _labels, stats, centroids = cv2.connectedComponentsWithStats(skin, 8)
    if num <= 1:
        return 0.5, 0.5

    # Skip background (label 0); find the largest body blob by area.
    areas = stats[1:, cv2.CC_STAT_AREA]
    if areas.size == 0:
        return 0.5, 0.5
    largest = 1 + int(np.argmax(areas))
    cx_px, cy_px = centroids[largest]

    cx_skin = float(cx_px) / float(w)
    cy_skin = float(cy_px) / float(h)

    # Pull moderately toward the image center for stability across crops,
    # then clamp into a safe central zone so we never anchor at the edge.
    blend = 0.35  # 35% skin, 65% center
    cx = blend * cx_skin + (1.0 - blend) * 0.50
    cy = blend * cy_skin + (1.0 - blend) * 0.50
    return (
        float(np.clip(cx, 0.30, 0.70)),
        float(np.clip(cy, 0.30, 0.70)),
    )


# Backwards-compatible alias for any older imports.
detect_body_centroid = detect_body_anchor


def composite_stencil_on_body(
    body_jpeg: bytes,
    stencil_jpeg: bytes,
    body_region: str,
    coverage: str,
    variant_index: int = 0,
    *,
    style_key: str = "fine_line",
    placement_override: Optional[Tuple[float, float, float]] = None,
) -> bytes:
    """
    Place resized stencil on a white full-frame, then dermal-style ink blend
    (not raw multiply) so the piece reads as ink in skin, not a flat overlay.

    When ``placement_override`` is provided as ``(cx, cy, base_frac)`` it
    bypasses ``_PLACEMENT[body_region]`` — used by couple split mode to anchor
    each half to the detected body-part centroid instead of a fixed preset.
    """
    body = _open_rgb(body_jpeg)
    st = _open_rgb(stencil_jpeg)
    bw, bh = body.size
    sw, sh = st.size
    m = min(bw, bh)

    if placement_override is not None:
        cx, cy, base_frac = placement_override
    else:
        region = (body_region or "from_photo").lower().strip()
        if region not in _PLACEMENT:
            region = "from_photo"
        cx, cy, base_frac = _PLACEMENT[region]
    cov = _coverage_frac(coverage)
    max_side = m * min(base_frac, cov + 0.05)
    scale = max_side / float(max(sw, sh))
    tw = max(32, min(int(sw * scale), bw - 4))
    th = max(32, min(int(sh * scale), bh - 4))
    st = st.resize((tw, th), Image.LANCZOS)

    # Per-variant: small placement shifts; variant 0 stays closest to "ideal" center
    ox = (variant_index * 5 + variant_index * variant_index) % 3 - 1
    oy = (variant_index * 2) % 3 - 1
    cx += ox * 0.008
    cy += oy * 0.007

    x = int(bw * cx - tw / 2)
    y = int(bh * cy - th / 2)
    x = max(0, min(x, bw - tw))
    y = max(0, min(y, bh - th))

    layer = Image.new("RGB", (bw, bh), (255, 255, 255))
    # Paste stencil directly without pre-blur - blur happens in ink blend
    layer.paste(st, (x, y))

    k = (style_key or "fine_line").lower().strip()
    max_ink = _INK_MAX_BY_STYLE.get(k, 0.78)
    out = _ink_blend_dermal(body, layer, max_ink=max_ink)

    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=94, optimize=True)
    return buf.getvalue()
