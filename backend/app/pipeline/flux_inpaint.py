"""
Flux Fill Pro inpaint client + scar-transform mask builder.

`prunaai/p-image-edit` is great for "edit this photo" instructions but it
cannot be told to physically NOT paint inside a region. For the scar
`transform` strategy we need exactly that: paint a tattoo AROUND the scar
so the scar becomes the focal element of the design while remaining bare
skin. Flux Fill Pro is the right tool — black mask pixels are guaranteed
to stay untouched.

The mask we hand it has TWO regions:
  * WHITE = inpaint zone (an oriented ellipse around the scar where the
    tattoo grows along the scar's axis).
  * BLACK = preserve everything else, INCLUDING the scar tissue itself,
    so the model literally cannot paint over the scar.

This guarantees "tattoo built around the scar" without any prompt
gymnastics.
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
from typing import Optional

import httpx
import numpy as np
from PIL import Image, ImageFilter

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
# `black-forest-labs/flux-fill-pro` is an official Replicate model so the
# `/v1/models/{owner}/{name}/predictions` shortcut works (no version id needed).
FLUX_FILL_PREDICTIONS_URL = (
    "https://api.replicate.com/v1/models/black-forest-labs/flux-fill-pro/predictions"
)
FLUX_POLL_INTERVAL_SEC = 1.0
FLUX_POLL_MAX_ATTEMPTS = 120


def _b64_data_url(blob: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64,{base64.b64encode(blob).decode('ascii')}"


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _max_filter_odd(img: Image.Image, radius_px: int) -> Image.Image:
    """
    PIL's MaxFilter caps the kernel at ~9 px on most builds; for the large
    dilations we need (a tattoo zone hugging the scar's silhouette out to
    several body-percent), iterate small max-filters instead. Returns L mode.
    """
    if radius_px <= 0:
        return img
    if img.mode != "L":
        img = img.convert("L")
    step = 4  # keep MaxFilter happy across PIL versions
    n = max(1, radius_px // step)
    rem = radius_px - n * step
    out = img
    for _ in range(n):
        out = out.filter(ImageFilter.MaxFilter(step * 2 + 1))
    if rem > 0:
        out = out.filter(ImageFilter.MaxFilter(rem * 2 + 1))
    return out


def build_scar_transform_mask(
    scar_mask_png: bytes,
    geometry: dict,
    full_w: int,
    full_h: int,
    *,
    grow_factor: float = 0.55,
    grow_floor_pct: float = 0.04,
    grow_ceiling_pct: float = 0.10,
    inner_buffer_pct: float = 0.005,
) -> bytes:
    """
    Build the Flux Fill Pro inpaint mask for scar `transform`.

    Geometry: dilate the scar mask outward by a distance derived from
    the SCAR's own size (not the photo's size). This auto-adapts to any
    body part the user uploads — a small scar on a forearm gets a small
    tight ring, a long scar on a back gets a proportionally bigger ring.
    The previous approach (% of photo short-side) gave the same-size
    scar wildly different ring widths depending on photo crop.

    Math:
      grow_px = scar_long_dim * grow_factor
      clamped to [grow_floor_pct, grow_ceiling_pct] of the photo's short
      side as a sanity rail (so a SAM mask one-pixel-thin doesn't yield
      a degenerate ring, and a near-full-photo scar doesn't yield a
      ring that overflows the body part).

    Result: a ring that scales WITH the scar, framing it like a jewel
    setting. The tattoo physically can't sprawl beyond this ring.

    Parameters
    ----------
    scar_mask_png : bytes
        Binary PNG mask from `scar_segment.ScarSegmentation.mask_png`.
        White = scar tissue.
    geometry : dict
        SAM-derived geometry. Length/width drive the dilation amount.
    full_w, full_h : int
        Body photo dimensions.
    grow_factor : float
        Multiplier on the scar's longest dimension that sets the ring's
        thickness. 0.55 reads as "design width ≈ scar length" — tight,
        focused, jewel-in-setting feel.
    grow_floor_pct, grow_ceiling_pct : float
        Sanity rails as fractions of photo short side.
    inner_buffer_pct : float
        Tiny dilation of the scar before subtraction so the seam between
        bare-skin scar and tattoo ink isn't a ragged single-pixel line.

    Returns
    -------
    bytes
        PNG mask. White = paint, black = preserve (scar + skin elsewhere).
    """
    try:
        scar_img = Image.open(io.BytesIO(scar_mask_png))
    except Exception:
        return _png_bytes(Image.new("L", (full_w, full_h), 0))
    if scar_img.mode != "L":
        scar_img = scar_img.convert("L")
    if scar_img.size != (full_w, full_h):
        scar_img = scar_img.resize((full_w, full_h), Image.NEAREST)

    scar_bool = np.asarray(scar_img, dtype=np.uint8) > 127
    if not scar_bool.any():
        return _png_bytes(Image.new("L", (full_w, full_h), 0))

    short_side = float(min(full_w, full_h))
    floor_px = max(16, int(round(short_side * grow_floor_pct)))
    ceiling_px = max(floor_px + 1, int(round(short_side * grow_ceiling_pct)))

    # Drive the ring thickness from the SAM-measured scar length first
    # (most accurate), and fall back to the bbox if length_pct wasn't
    # populated for some reason.
    length_pct = float((geometry or {}).get("length_pct", 0.0))
    if length_pct > 0:
        scar_long_px = (length_pct / 100.0) * short_side
    else:
        ys, xs = np.where(scar_bool)
        scar_long_px = float(max(xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))

    grow_px = int(round(scar_long_px * grow_factor))
    grow_px = max(floor_px, min(ceiling_px, grow_px))

    inner_pad_px = max(2, int(round(short_side * inner_buffer_pct)))

    scar_pil = Image.fromarray((scar_bool.astype(np.uint8) * 255), mode="L")
    grown_pil = _max_filter_odd(scar_pil, grow_px)
    inner_pil = _max_filter_odd(scar_pil, inner_pad_px)

    grown = np.asarray(grown_pil, dtype=np.uint8) > 127
    inner = np.asarray(inner_pil, dtype=np.uint8) > 127

    ring = grown & ~inner
    mask_img = Image.fromarray((ring.astype(np.uint8) * 255), mode="L")

    # Soft feather on the OUTER edge of the ring so ink fades into bare
    # skin instead of stopping at a hard contour. Re-cut the scar so its
    # boundary stays sharp (we want the silhouette readable).
    feathered = mask_img.filter(
        ImageFilter.GaussianBlur(radius=max(1.5, short_side * 0.004))
    )
    feathered_arr = np.asarray(feathered, dtype=np.uint8)
    feathered_arr = np.where(inner, 0, feathered_arr).astype(np.uint8)
    print(
        f"[SCAR_TRANSFORM] mask: scar_long_px={scar_long_px:.0f} grow_px={grow_px} "
        f"floor={floor_px} ceiling={ceiling_px} inner_buf={inner_pad_px}"
    )
    return _png_bytes(Image.fromarray(feathered_arr, mode="L"))


async def replicate_flux_fill_pro(
    body_jpeg: bytes,
    mask_png: bytes,
    prompt: str,
    *,
    seed: Optional[int] = None,
    steps: int = 30,
    guidance: float = 30.0,
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Call `black-forest-labs/flux-fill-pro` with the given image, mask and
    prompt. Returns the generated JPEG/WEBP bytes or an error string.

    The model strictly preserves pixels under black mask regions and only
    paints inside the white region. That guarantee is what makes it the
    right pick for the scar `transform` strategy.

    Parameters chosen for tattoo work:
      * steps=30: well past the quality plateau for inpainting; the
        difference vs 25 is visible on fine line tattoos.
      * guidance=30: Flux Fill Pro's recommended high-guidance setting
        when prompt fidelity matters more than photographic realism.
    """
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return None, "REPLICATE_API_TOKEN not configured"

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    inputs: dict = {
        "image": _b64_data_url(body_jpeg, "image/jpeg"),
        "mask": _b64_data_url(mask_png, "image/png"),
        "prompt": prompt,
        "steps": int(steps),
        "guidance": float(guidance),
        "output_format": "jpg",
        "output_quality": 92,
        "safety_tolerance": 2,
        "prompt_upsampling": False,
    }
    if seed is not None:
        inputs["seed"] = int(seed)

    payload = {"input": inputs}

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                FLUX_FILL_PREDICTIONS_URL,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(180.0),
            )
            if r.status_code not in (200, 201):
                return None, f"Flux Fill API error {r.status_code}: {r.text[:400]}"

            data = r.json()
            out = data.get("output")
            if isinstance(out, str) and out.startswith("http"):
                img_r = await client.get(out, timeout=httpx.Timeout(60.0))
                if img_r.status_code == 200:
                    return img_r.content, None

            pred_id = data.get("id")
            if not pred_id:
                return None, "Flux Fill: no prediction id"
            get_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
            for _ in range(FLUX_POLL_MAX_ATTEMPTS):
                await asyncio.sleep(FLUX_POLL_INTERVAL_SEC)
                pr = await client.get(
                    get_url, headers=headers, timeout=httpx.Timeout(60.0)
                )
                if pr.status_code != 200:
                    continue
                d = pr.json()
                status = d.get("status")
                if status == "succeeded":
                    output = d.get("output")
                    if isinstance(output, str) and output.startswith("http"):
                        img_r = await client.get(output, timeout=httpx.Timeout(60.0))
                        if img_r.status_code == 200:
                            return img_r.content, None
                    return None, "Flux Fill: empty output"
                if status == "failed":
                    return None, f"Flux Fill failed: {d.get('error', 'unknown')}"
                if status == "canceled":
                    return None, "Flux Fill canceled"
            return None, "Flux Fill: timeout"
    except httpx.RequestError as e:
        return (
            None,
            f"Network error reaching Replicate (Flux Fill): "
            f"{type(e).__name__}: {e}",
        )


def build_scar_transform_prompt(
    style_render: str,
    motif_phrase: str,
    geometry: dict,
    is_sensitive: bool,
) -> str:
    """
    Descriptive prompt for Flux Fill Pro. Flux is a diffusion model — it
    responds to "what to paint" descriptions, not "edit this photo to do X"
    commands.

    Critical: the mask we feed Flux already hugs the scar's silhouette
    (ring shape that traces the scar). The prompt's job is to make the
    model understand that the BARE-SKIN NEGATIVE SPACE between the ring
    is the artistic focal element of the piece, not an accident.

    Without this framing, models default to "tattoo near a hole" which
    reads as "generic tattoo with a gap in it". With it, they treat the
    bare-skin region like meaningful negative space the design is built
    around — which is what `transform` actually means.
    """
    shape = (geometry or {}).get("shape", "irregular")
    angle_deg = float((geometry or {}).get("angle_deg", 0.0))

    if shape == "linear":
        if abs(angle_deg) < 15:
            orient = "horizontal"
        elif abs(angle_deg) > 75:
            orient = "vertical"
        else:
            orient = "diagonal"
        focal_role = (
            f"a {orient} BARE-SKIN LINE that is the spine of the design. "
            "The ink hugs that bare line tightly on both sides, never crossing "
            "it. The whole piece is shaped like a slim ornamental setting "
            "around that bare-skin spine"
        )
    elif shape == "round":
        focal_role = (
            "a small BARE-SKIN focal disc at the heart of the design — like a "
            "gemstone in a tight ornamental setting. The ink hugs the disc's "
            "edges closely, framing it like a fine jewelry mount"
        )
    else:
        focal_role = (
            "a small BARE-SKIN organic focal shape at the heart of the design. "
            "The ink hugs that shape's edges closely like a tight ornamental "
            "setting around a stone"
        )

    sensitive = (
        "Tone: soft and life-affirming. Gentle linework. No weapons, no sharp "
        "edges, no aggressive symbolism. "
        if is_sensitive
        else ""
    )

    return (
        f"A small, focused, professional healed tattoo built tightly around "
        f"{focal_role}. "
        f"The ink takes the form of {motif_phrase}, sized to read as a "
        "single intentional jewel-in-a-setting piece — NOT a sprawling "
        "decorative panel across the body. The bare-skin focal area is "
        "unambiguously the most important visual element of the whole piece "
        "— without that exposed skin shape, the design would be incomplete "
        "and meaningless. "
        f"{sensitive}"
        f"{style_render}. "
        "Crisp dark ink absorbed into real skin, dermal saturation, no glow, "
        "no halo, no sticker effect. Photographic realism, natural lighting "
        "matching the surrounding skin. Tight composition with confident "
        "silhouette and intentional negative space. Premium fine-art tattoo "
        "aesthetic, scar-scaled — the design's footprint is roughly the size "
        "of the scar plus a slim margin, never wider than that. "
        "Absolutely no letters, words, numbers, captions, watermarks, logos, "
        "or pseudo-text glyphs anywhere in the artwork."
    )
