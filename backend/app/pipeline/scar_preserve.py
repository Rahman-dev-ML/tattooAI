"""
scar_preserve: post-processing for the scar_coverup TRANSFORM strategy.

Prompt engineering alone cannot reliably make `prunaai/p-image-edit` leave a
specific patch of skin un-inked — the model paints across the whole tattoo
region. For the TRANSFORM strategy (where the scar must remain VISIBLE as the
focal point of the design), we therefore guarantee the result with a local
post-process: blend the original photo's scar region back over the generated
image with feathered edges, so the bare-skin scar shows through whatever the
AI rendered.

Inputs are JPEG byte blobs and the user's tap mark (cx, cy, radius) expressed
as fractions 0..1 of the photo's smaller dimension (so the mark scales with
any aspect ratio). The output is another JPEG.
"""
from __future__ import annotations

import io
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter

# How aggressively the original is pulled back over the generated image
# inside the marked region. 1.0 = full restore, 0.0 = no effect.
# We use 1.0 so the scar is unambiguously visible — the whole point of
# TRANSFORM is for the user to see their scar as the design's focal point.
_RESTORE_STRENGTH = 1.0

# Outer feather as a multiplier of the user's marked radius.
# 1.25 means the blend transitions over the outermost 25% of the marked
# circle (sharp inside, soft on the edges). Keeps the boundary natural.
_FEATHER_MULT = 1.25


def _read(blob: bytes) -> Image.Image:
    return Image.open(io.BytesIO(blob)).convert("RGB")


def _write(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _radial_mask(
    width: int,
    height: int,
    cx_px: float,
    cy_px: float,
    inner_radius_px: float,
    outer_radius_px: float,
) -> np.ndarray:
    """
    Build a 0..1 alpha mask: 1.0 inside `inner_radius_px`, fading linearly to
    0.0 at `outer_radius_px`. Returns float32 array of shape (H, W).
    """
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    dist = np.sqrt((xx - cx_px) ** 2 + (yy - cy_px) ** 2)

    if outer_radius_px <= inner_radius_px:
        outer_radius_px = inner_radius_px + 1.0

    mask = np.clip(
        (outer_radius_px - dist) / (outer_radius_px - inner_radius_px),
        0.0,
        1.0,
    ).astype(np.float32)
    return mask


def restore_scar_region(
    original_jpeg: bytes,
    generated_jpeg: bytes,
    mark_cx: float,
    mark_cy: float,
    mark_radius: float,
    *,
    strength: float = _RESTORE_STRENGTH,
    feather_mult: float = _FEATHER_MULT,
) -> bytes:
    """
    Blend the original photo's scar region back over the generated image.

    Parameters
    ----------
    original_jpeg, generated_jpeg : bytes
        Body photo before/after the AI run. They may have different dimensions
        (the model often returns a slightly resized image); the original is
        resampled to match the generated frame so the mark coordinates land
        in the same place visually.
    mark_cx, mark_cy : float in [0, 1]
        Centre of the scar mark, as fractions of the GENERATED image width
        and height respectively. (i.e. mark_cx = pixel_x / width.)
    mark_radius : float in [0, 1]
        Radius of the scar mark, as a fraction of the smaller image
        dimension (min(width, height)).
    strength : float in [0, 1]
        Blend strength inside the inner mask. 1.0 = pure original.
    feather_mult : float >= 1
        Outer fade extent as a multiplier of the inner radius.

    Returns
    -------
    bytes
        JPEG-encoded result.
    """
    if mark_radius <= 0:
        return generated_jpeg

    gen = _read(generated_jpeg)
    orig = _read(original_jpeg)

    # Resample original to match the generated frame so the mark aligns visually.
    if orig.size != gen.size:
        orig = orig.resize(gen.size, Image.LANCZOS)

    w, h = gen.size
    short_side = float(min(w, h))

    cx_px = float(mark_cx) * w
    cy_px = float(mark_cy) * h
    inner_r = max(2.0, float(mark_radius) * short_side)
    outer_r = inner_r * max(1.0, feather_mult)

    mask = _radial_mask(w, h, cx_px, cy_px, inner_r, outer_r)
    mask *= float(np.clip(strength, 0.0, 1.0))

    # Soften the mask edge a touch so the join is invisible
    pil_mask = Image.fromarray((mask * 255.0).astype(np.uint8), mode="L")
    pil_mask = pil_mask.filter(ImageFilter.GaussianBlur(max(1.0, inner_r * 0.05)))
    mask = np.asarray(pil_mask, dtype=np.float32) / 255.0

    gen_arr = np.asarray(gen, dtype=np.float32)
    orig_arr = np.asarray(orig, dtype=np.float32)

    # Slight luminance match: blend the original's brightness toward the
    # generated frame's local brightness so the restored patch doesn't look
    # like a cut-out. Subtle — just enough to inherit the AI's lighting.
    gen_blur = np.asarray(
        gen.filter(ImageFilter.GaussianBlur(max(2.0, inner_r * 0.18))),
        dtype=np.float32,
    )
    orig_blur = np.asarray(
        orig.filter(ImageFilter.GaussianBlur(max(2.0, inner_r * 0.18))),
        dtype=np.float32,
    )
    delta = gen_blur - orig_blur
    relit = np.clip(orig_arr + delta * 0.35, 0.0, 255.0)

    m3 = mask[..., None]
    out = relit * m3 + gen_arr * (1.0 - m3)
    out = np.clip(out, 0.0, 255.0).astype(np.uint8)

    return _write(Image.fromarray(out))


def restore_scar_from_mask(
    original_jpeg: bytes,
    generated_jpeg: bytes,
    mask_png: bytes,
    *,
    feather_px: int = 6,
    strength: float = 1.0,
) -> bytes:
    """
    Mask-based scar preserve. Uses the SAM-2 binary mask of the actual scar
    (not the user's tap radius) so we restore *only* the scar tissue and the
    surrounding tattoo painted by the AI is left untouched.

    Parameters
    ----------
    original_jpeg, generated_jpeg : bytes
        Body photo before/after the AI run. Resampled to a common size.
    mask_png : bytes
        Binary PNG mask from `scar_segment.ScarSegmentation.mask_png`.
        White (>127 luminance) = scar pixels to preserve.
    feather_px : int
        Gaussian blur radius applied to the mask edge (in pixels) so the
        join between restored scar and AI-painted skin is invisible.
    strength : float in [0, 1]
        Blend strength. 1.0 = pure original inside the mask.

    Returns
    -------
    bytes
        JPEG-encoded result.
    """
    gen = _read(generated_jpeg)
    orig = _read(original_jpeg)

    if orig.size != gen.size:
        orig = orig.resize(gen.size, Image.LANCZOS)

    try:
        mask_img = Image.open(io.BytesIO(mask_png))
    except Exception:
        return generated_jpeg
    if mask_img.mode != "L":
        mask_img = mask_img.convert("L")
    if mask_img.size != gen.size:
        mask_img = mask_img.resize(gen.size, Image.NEAREST)

    if feather_px > 0:
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=float(feather_px)))

    alpha = np.asarray(mask_img, dtype=np.float32) / 255.0
    alpha = np.clip(alpha * float(np.clip(strength, 0.0, 1.0)), 0.0, 1.0)
    if not np.any(alpha > 0.01):
        return generated_jpeg

    gen_arr = np.asarray(gen, dtype=np.float32)
    orig_arr = np.asarray(orig, dtype=np.float32)

    # Subtle relight: pull original toward generated frame's local brightness
    # so the restored scar inherits the AI's lighting and doesn't read like
    # a cut-out. Same trick as the radial path.
    blur_radius = max(2.0, float(feather_px) * 1.5)
    gen_blur = np.asarray(
        gen.filter(ImageFilter.GaussianBlur(blur_radius)), dtype=np.float32
    )
    orig_blur = np.asarray(
        orig.filter(ImageFilter.GaussianBlur(blur_radius)), dtype=np.float32
    )
    delta = gen_blur - orig_blur
    relit = np.clip(orig_arr + delta * 0.35, 0.0, 255.0)

    a3 = alpha[..., None]
    out = relit * a3 + gen_arr * (1.0 - a3)
    out = np.clip(out, 0.0, 255.0).astype(np.uint8)

    return _write(Image.fromarray(out))


def parse_mark_string(s: Optional[str]) -> Optional[Tuple[float, float, float]]:
    """
    Parse a `cx,cy,radius` triple of floats in [0..1]. Returns None if the
    string is missing, malformed, or out of range.
    """
    if not s:
        return None
    try:
        parts = [float(x.strip()) for x in s.split(",")]
    except (ValueError, AttributeError):
        return None
    if len(parts) != 3:
        return None
    cx, cy, r = parts
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < r <= 1.0):
        return None
    return cx, cy, r
