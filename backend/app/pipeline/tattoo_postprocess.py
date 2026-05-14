"""
Post-process p-image-edit outputs: the model often paints a flat sticker,
coloured fringes, or pink halos. Mehndi did realism via hand landmarks +
overlay; here we only have the two JPEGs, so we blend the generated image
back toward the original body in controlled regions.

This does not replace a full segmentation pipeline, but it reliably fixes:
- red/pink/orange fringes and glow around linework
- slightly too-opaque line blocks (a hint of body texture in ink)
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def _rgb_open(jpeg: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(jpeg))
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im


def _to_jpeg_bytes(arr: np.ndarray, quality: int = 90) -> bytes:
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _luminance(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def lock_output_to_input_canvas(
    body_jpeg: bytes,
    model_jpeg: bytes,
    *,
    mean_diff_threshold: float = 6.0,
) -> bytes:
    """
    Force the final image to be the *given body photo* everywhere the model
    did not make a real edit. p-image-edit often tints the whole frame or
    slightly regenerates the background; this snaps almost-unchanged pixels
    back to the exact upload so the tattoo stays on the real photo, not a
    synthetic re-render. Tattoo pixels (large colour / luminance delta) stay
    from the model.
    """
    im_body = _rgb_open(body_jpeg)
    im_model = _rgb_open(model_jpeg)
    w0, h0 = im_body.size
    if (w0, h0) != im_model.size:
        im_model = im_model.resize((w0, h0), Image.LANCZOS)
    body = np.array(im_body, dtype=np.float32)
    m = np.array(im_model, dtype=np.float32)
    d = np.mean(np.abs(m - body), axis=2)
    Lb = _luminance(body)
    Lm = _luminance(m)
    # "Unchanged" = very close in RGB and in luminance (rejects false positives
    # where one channel wiggles but the spot is still clearly edited).
    lum_ok = np.abs(Lm - Lb) < 5.0
    unchanged = (d < float(mean_diff_threshold)) & lum_ok
    out = m.copy()
    out[unchanged] = body[unchanged]
    arr = np.clip(out, 0, 255).astype(np.uint8)
    p = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    p.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def heal_tattoo_against_body(
    body_jpeg: bytes,
    output_jpeg: bytes,
    *,
    max_dim: int = 2048,
) -> bytes:
    """
    Align sizes (model output is usually same as input), then blend in
    tattoo-like regions: suppress chromatic halos, soften opaque ink, mix
    skin texture from the body.

    Tuned to be safe on faces/backgrounds: only where output differs
    measurably from the body, with separate handling for very dark (ink) vs
    midtone fringes.
    """
    im_body = _rgb_open(body_jpeg)
    im_out = _rgb_open(output_jpeg)
    w0, h0 = im_body.size
    w1, h1 = im_out.size
    if (w0, h0) != (w1, h1):
        im_out = im_out.resize((w0, h0), Image.LANCZOS)
    # Process at up to max_dim for speed, then scale result back to (w0, h0) so
    # the client always gets the same resolution as the preprocessed body input.
    work_w, work_h = w0, h0
    if max(work_w, work_h) > max_dim:
        scale = max_dim / max(work_w, work_h)
        work_w, work_h = int(work_w * scale), int(work_h * scale)
        im_body2 = im_body.resize((work_w, work_h), Image.LANCZOS)
        im_out2 = im_out.resize((work_w, work_h), Image.LANCZOS)
    else:
        im_body2, im_out2 = im_body, im_out
    body = np.array(im_body2, dtype=np.float32)
    o = np.array(im_out2, dtype=np.float32)
    h, w = body.shape[:2]
    d = np.mean(np.abs(o - body), axis=2)
    L = _luminance(o)
    Lb = _luminance(body)
    r, g, bc = o[..., 0], o[..., 1], o[..., 2]
    # --- Where did the model change the photo? ---
    changed = d > 8.0
    # Core ink: clearly darker + changed
    dark = (L < 58) & (L + 5.0 < Lb) & changed
    # Mid "fringe" / halo: model added colour or glow, not a solid line
    mid = (L > 40) & (L < 215) & changed
    # Pink / salmon / fleshy fringes (common p-image-edit artifact)
    pink = mid & (r > g + 6.0) & (g >= bc) & (r > 80)
    # Orange / yellow tints
    warm = mid & (r > 150) & (g > 100) & (bc < r * 0.85)
    br, bg = body[..., 0], body[..., 1]
    # Light halos: strong delta from body but not core black line
    hue_shift = (r - g) - (br - bg)
    halo = (d > 18.0) & (L > 50) & (L < 230) & (~dark) & (np.abs(hue_shift) > 2.0)
    # Union fringe mask (halo heuristics; avoid over-selecting the whole image)
    fringe = (pink | warm | (halo & (d < 100))) & (~dark) & (d > 6.0)
    # Slightly grow fringe mask to eat 1px ring around halos
    m = (fringe.astype(np.uint8) * 255)
    mpil = Image.fromarray(m, mode="L")
    mpil = mpil.filter(ImageFilter.MaxFilter(size=3))
    fringe = np.array(mpil) > 0
    out = o.copy()
    # Ink: let skin show through a little (pores) — not a second model, but
    # kills perfect flat vector look.
    # Dark line core
    t_ink = 0.10
    out[dark] = (1.0 - t_ink) * o[dark] + t_ink * body[dark]
    # Strong halos: pull hard toward body skin colour
    t_halo = 0.56
    out[fringe] = (1.0 - t_halo) * o[fringe] + t_halo * body[fringe]
    # Very soft outer ring: if still pink-ish after, pull more
    still = fringe & (r > g) & (L > 45) & (L < 200)
    t2 = 0.22
    out[still] = (1.0 - t2) * out[still] + t2 * body[still]
    out_u8 = np.clip(out, 0, 255).astype(np.uint8)
    if (w, h) != (w0, h0):
        out_pil = Image.fromarray(out_u8, mode="RGB").resize((w0, h0), Image.LANCZOS)
    else:
        out_pil = Image.fromarray(out_u8, mode="RGB")
    buf = io.BytesIO()
    out_pil.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def enforce_complementary_split_half(
    body_jpeg: bytes,
    output_jpeg: bytes,
    *,
    keep: str,
    diff_thresh: float = 8.0,
    feather_px: int = 6,
) -> bytes:
    """
    Hard gate for couple complementary_split: image-edit models often ignore
    "draw only half" in text. We snap pixels on the wrong side of the tattoo
    bounding-box midline back to the original body so each partner photo only
    retains ~half of the edit. Feather softens the vertical seam.

    keep: \"left\" = keep edits with x < midline (Partner A); \"right\" = keep x > midline (Partner B).
    """
    side = keep.strip().lower()
    if side not in ("left", "right"):
        return output_jpeg
    try:
        im_body = _rgb_open(body_jpeg)
        im_out = _rgb_open(output_jpeg)
        w0, h0 = im_body.size
        if (w0, h0) != im_out.size:
            im_out = im_out.resize((w0, h0), Image.LANCZOS)

        body = np.array(im_body, dtype=np.float32)
        gen = np.array(im_out, dtype=np.float32)
        d = np.mean(np.abs(gen - body), axis=2)
        changed = d > float(diff_thresh)
        if not np.any(changed):
            return output_jpeg

        ys, xs_idx = np.where(changed)
        x0, x1 = int(xs_idx.min()), int(xs_idx.max())
        mid_x = 0.5 * (x0 + x1)

        w = w0
        cols = np.arange(w, dtype=np.float32)
        f = max(2.0, float(feather_px))
        # One-sided seam:
        # - Keep side remains at full model strength (no washout).
        # - Only the rejected side is reverted to body with a small feather band.
        if side == "left":
            # Reject right side: full revert for x >= mid_x, feather only on [mid_x - f, mid_x).
            revert_along_x = np.where(
                cols >= mid_x,
                1.0,
                np.where(cols >= (mid_x - f), (cols - (mid_x - f)) / f, 0.0),
            )
        else:
            # Reject left side: full revert for x <= mid_x, feather only on (mid_x, mid_x + f].
            revert_along_x = np.where(
                cols <= mid_x,
                1.0,
                np.where(cols <= (mid_x + f), ((mid_x + f) - cols) / f, 0.0),
            )

        revert_alpha = changed.astype(np.float32) * revert_along_x[None, :]
        revert_alpha = np.clip(revert_alpha, 0.0, 1.0)[..., None]
        out = gen * (1.0 - revert_alpha) + body * revert_alpha
        return _to_jpeg_bytes(out, quality=95)
    except Exception:  # pragma: no cover
        return output_jpeg


def heal_if_pair(
    body_jpeg: bytes,
    output_jpeg: bytes,
    *,
    lock_canvas: bool = False,
) -> bytes:
    """
    Post-process: optional canvas lock (user's body photo) then halo/ink blend.
    On any failure, return the original model output.
    """
    try:
        if not body_jpeg or not output_jpeg or len(output_jpeg) < 80:
            return output_jpeg
        work = output_jpeg
        if lock_canvas:
            work = lock_output_to_input_canvas(body_jpeg, work)
        return heal_tattoo_against_body(body_jpeg, work)
    except Exception:  # pragma: no cover
        return output_jpeg


def composite_scar_tattoo(
    body_jpeg: bytes,
    model_jpeg: bytes,
    *,
    ink_dark_delta: float = 30.0,
    body_min_l: float = 45.0,
    very_dark_l: float = 50.0,
    very_dark_delta: float = 15.0,
    feather: float = 2.0,
) -> bytes:
    """
    Scar-coverup specific compositor.

    The AI often hallucinates new body parts, changes the pose, or floods the
    frame with brownish tints. Generic heal cannot fix this because the diff is
    huge EVERYWHERE when the scene is fully regenerated.

    Strategy: take the original body photo as ground truth, then paste on top
    of it *only* the pixels where the model genuinely darkened the skin (real
    tattoo ink). Skin-tone swaps, extra hands, and background changes are all
    lighter-than-ink, so they get discarded.

    ink_dark_delta  – body_luminance - model_luminance must exceed this for a
                      pixel to be treated as ink (model made it darker).
    body_min_l      – the original body pixel must be at least this bright
                      (prevents false positives on already-dark skin shadows).
    very_dark_l     – model pixel luminance below this is considered "very dark
                      ink" and kept even if body was already somewhat dark.
    very_dark_delta – minimum darkening even for the very-dark path.
    feather         – gaussian blur radius applied to the ink mask for
                      anti-aliased edges (pixels, not percent).
    """
    try:
        if not body_jpeg or not model_jpeg or len(model_jpeg) < 80:
            return model_jpeg

        im_body = _rgb_open(body_jpeg)
        im_model = _rgb_open(model_jpeg)
        w0, h0 = im_body.size
        if (w0, h0) != im_model.size:
            im_model = im_model.resize((w0, h0), Image.LANCZOS)

        body = np.array(im_body, dtype=np.float32)
        m = np.array(im_model, dtype=np.float32)

        L_body = _luminance(body)
        L_model = _luminance(m)

        darkening = L_body - L_model

        # Primary ink: model significantly darkened a pixel that was light in body
        is_ink = (darkening > ink_dark_delta) & (L_body > body_min_l)

        # Very-dark ink safety: keep any pixel the model drove below very_dark_l
        # even if the body was already somewhat shaded (bold lines on tanned skin)
        is_very_dark = (L_model < very_dark_l) & (darkening > very_dark_delta)

        ink_mask = (is_ink | is_very_dark).astype(np.uint8) * 255

        if feather > 0:
            mpil = Image.fromarray(ink_mask, mode="L")
            mpil = mpil.filter(ImageFilter.GaussianBlur(radius=feather))
            alpha = np.array(mpil, dtype=np.float32) / 255.0
        else:
            alpha = ink_mask.astype(np.float32) / 255.0

        alpha = alpha[..., np.newaxis]

        # Composite: ink pixels from model, everything else from original body
        out = (1.0 - alpha) * body + alpha * m
        return _to_jpeg_bytes(out)
    except Exception:  # pragma: no cover
        return model_jpeg
