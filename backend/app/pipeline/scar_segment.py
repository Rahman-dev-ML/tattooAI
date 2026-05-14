"""
SAM-2 scar segmentation (Tier B).

`prunaai/p-image-edit` is a text-instruction model — it has no spatial
grounding. To paint AROUND a scar we need the scar's true silhouette.

Replicate's `meta/sam-2` is automatic-only (no point prompts), so:

    1. Crop the body photo to a tight window around the user's tap. SAM
       has a fixed sampling budget (`points_per_side` = 64 by default), so
       sampling that budget over a small crop instead of the full photo
       gives ~10-20x denser coverage of the scar area — critical for
       picking up low-contrast / faded scars that SAM ignores at
       full-image resolution.
    2. Run SAM-2 on the crop → ~10-50 candidate masks.
    3. Pick the smallest mask that overlaps the tap region and has a
       plausible scar size.
    4. Re-paste the mask onto a full-image black canvas at the crop's
       offset so downstream code can treat it like a full-image mask.
    5. Compute geometry (orientation, length, shape category) via PCA.

Results are cached in memory by hash(body_jpeg) + tap. If SAM finds
nothing, return None — the caller will skip pixel restore and let the
AI handle the scar based on the prompt's location hint alone.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import math
import os
from collections import OrderedDict
from typing import Optional

import httpx
import numpy as np
from PIL import Image, ImageOps

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
# `meta/sam-2` is a community model on Replicate (is_official=false), so the
# `/v1/models/{owner}/{name}/predictions` shortcut returns 404. Community
# models must be invoked via `/v1/predictions` with an explicit `version`.
SAM_PREDICTIONS_URL = "https://api.replicate.com/v1/predictions"
SAM_VERSION_ID = "fe97b453a6455861e3bac769b441ca1f1086110da7466dbb65cf1eecfd60dc83"
SAM_POLL_INTERVAL_SEC = 1.0
SAM_POLL_MAX_ATTEMPTS = 60  # SAM-2 typically completes in 9-25s

# Cache size — small footprint, plenty for one user's regen workflow.
_CACHE_MAX = 32
_cache: "OrderedDict[str, ScarSegmentation]" = OrderedDict()


class ScarSegmentation:
    """In-memory representation of a SAM-segmented scar.

    Only real SAM masks are returned by `segment_scar_async`. There is
    no synthetic / text-inferred mask path — if SAM finds nothing the
    function returns None and the caller skips pixel restore.
    """

    __slots__ = ("mask_png", "width", "height", "geometry", "mask_source")

    def __init__(
        self,
        mask_png: bytes,
        width: int,
        height: int,
        geometry: dict,
        mask_source: str = "sam",
    ):
        self.mask_png = mask_png
        self.width = width
        self.height = height
        self.geometry = geometry
        self.mask_source = mask_source


def _cache_key(body_jpeg: bytes, cx: float, cy: float, radius: float) -> str:
    h = hashlib.sha256(body_jpeg).hexdigest()[:16]
    return f"{h}|{cx:.4f}|{cy:.4f}|{radius:.4f}"


def _cache_get(key: str) -> Optional[ScarSegmentation]:
    seg = _cache.get(key)
    if seg is not None:
        _cache.move_to_end(key)
    return seg


def _cache_put(key: str, seg: ScarSegmentation) -> None:
    _cache[key] = seg
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


def _open_rgb(jpeg: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(jpeg))
    im = ImageOps.exif_transpose(im)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im


def _b64_data_url(jpeg: bytes) -> str:
    return f"data:image/jpeg;base64,{base64.b64encode(jpeg).decode('ascii')}"


def _binarize_mask(mask_img: Image.Image) -> np.ndarray:
    """SAM masks ship as RGBA or L PNGs; threshold to bool."""
    if mask_img.mode != "L":
        mask_img = mask_img.convert("L")
    arr = np.asarray(mask_img, dtype=np.uint8)
    return arr > 127


def _analyze_geometry(mask: np.ndarray, image_w: int, image_h: int) -> dict:
    """
    PCA-based shape analysis on the binary mask.

    Returns:
        bbox: [x0, y0, x1, y1] in pixels
        area_pct: area as % of image area
        cx_pct, cy_pct: centroid as fraction of image
        length_pct: long-axis length as % of image short side
        width_pct: short-axis length as % of image short side
        aspect: long/short axis ratio (>=1.0)
        angle_deg: orientation of long axis from horizontal, [-90, 90)
        shape: one of "linear", "round", "irregular"
        description: short human-readable phrase for the prompt
    """
    ys, xs = np.where(mask)
    if xs.size < 8:
        return {
            "bbox": [0, 0, image_w, image_h],
            "area_pct": 0.0,
            "cx_pct": 0.5,
            "cy_pct": 0.5,
            "length_pct": 0.0,
            "width_pct": 0.0,
            "aspect": 1.0,
            "angle_deg": 0.0,
            "shape": "irregular",
            "description": "small irregular scar",
        }

    short_side = float(min(image_w, image_h))
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())

    cx = float(xs.mean())
    cy = float(ys.mean())
    area_px = float(xs.size)
    area_pct = 100.0 * area_px / float(image_w * image_h)

    # PCA on (x, y) coordinates → eigenvectors give principal axes.
    pts = np.column_stack([xs.astype(np.float64) - cx, ys.astype(np.float64) - cy])
    cov = np.cov(pts, rowvar=False)
    # Guard against degenerate covariance
    if not np.all(np.isfinite(cov)) or cov.shape != (2, 2):
        cov = np.array([[1.0, 0.0], [0.0, 1.0]])
    eigvals, eigvecs = np.linalg.eigh(cov)
    # eigh returns ascending eigenvalues; long axis = larger eigenvalue
    long_eigval = max(eigvals[1], 1e-6)
    short_eigval = max(eigvals[0], 1e-6)
    long_vec = eigvecs[:, 1]

    # 4*sqrt(eigval) is the standard 2-sigma length estimate of the principal axis.
    long_len = 4.0 * math.sqrt(long_eigval)
    short_len = 4.0 * math.sqrt(short_eigval)
    aspect = long_len / max(short_len, 1.0)

    # angle of long axis vs horizontal, normalized to [-90, 90)
    angle_rad = math.atan2(float(long_vec[1]), float(long_vec[0]))
    angle_deg = math.degrees(angle_rad)
    while angle_deg >= 90.0:
        angle_deg -= 180.0
    while angle_deg < -90.0:
        angle_deg += 180.0

    length_pct = 100.0 * long_len / short_side
    width_pct = 100.0 * short_len / short_side

    # Categorize shape
    if aspect >= 3.0:
        shape = "linear"
    elif aspect <= 1.6:
        shape = "round"
    else:
        shape = "irregular"

    description = _describe_shape(shape, length_pct, angle_deg, aspect)

    return {
        "bbox": [x0, y0, x1, y1],
        "area_pct": round(area_pct, 2),
        "cx_pct": round(100.0 * cx / image_w, 2),
        "cy_pct": round(100.0 * cy / image_h, 2),
        "length_pct": round(length_pct, 1),
        "width_pct": round(width_pct, 1),
        "aspect": round(aspect, 2),
        "angle_deg": round(angle_deg, 1),
        "shape": shape,
        "description": description,
    }


def _describe_shape(shape: str, length_pct: float, angle_deg: float, aspect: float) -> str:
    """Plain English geometry description for the prompt."""
    if shape == "linear":
        # Angle naming: 0° is horizontal, 90° is vertical
        a = abs(angle_deg)
        if a < 15:
            orient = "horizontal"
        elif a < 35:
            orient = "shallow diagonal"
        elif a < 55:
            orient = "diagonal"
        elif a < 75:
            orient = "steep diagonal"
        else:
            orient = "vertical"
        return (
            f"a {orient} linear scar, roughly {length_pct:.0f}% of the photo's short side long, "
            f"about {aspect:.0f}x as long as it is wide"
        )
    if shape == "round":
        return f"a roughly round scar patch, about {length_pct:.0f}% of the photo's short side across"
    return (
        f"an irregular scar shape, roughly {length_pct:.0f}% of the photo's short side across, "
        f"about {aspect:.1f}x more long than wide"
    )


def _pick_best_mask(
    masks: list[tuple[bytes, np.ndarray]],
    tap_x_px: int,
    tap_y_px: int,
    tap_radius_px: int,
    image_w: int,
    image_h: int,
) -> Optional[tuple[bytes, np.ndarray]]:
    """
    Score and pick the best candidate mask.

    The previous "must contain the exact tap pixel" rule was too strict —
    a 1-pixel offset (or a low-contrast scar SAM didn't segment) caused
    every candidate to be rejected. Updated rules:

      1. Mask must overlap the user's tap REGION (the marker circle), not
         just the single tap pixel. We allow a small search radius so a
         scar mask that sits next to the tap point still counts.
      2. Area between 0.05% and 50% of the image. Upper bound raised
         because a "long spine scar" mask is genuinely large.
      3. Among remaining, prefer SMALLER area (most specific to the
         scar) but secondarily prefer masks whose centroid is closer
         to the tap. A small mask 100px away is worse than a slightly
         larger one centered on the tap.
    """
    img_area = float(image_w * image_h)
    # Allow the mask to be considered "near" the tap if it touches a
    # circle of this radius around the tap. We use the FULL tap radius
    # the user marked (clamped to half the image to avoid pathological
    # values) — earlier we capped at 5% of width which rejected every
    # mask when the user had marked a long scar with a big circle.
    search_radius = int(max(8, min(min(image_w, image_h) // 2, tap_radius_px)))

    candidates: list[tuple[float, bytes, np.ndarray]] = []
    for png_bytes, mask in masks:
        if mask.shape != (image_h, image_w):
            try:
                m_img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
                m_img = m_img.resize((image_w, image_h), Image.NEAREST)
                mask = np.asarray(m_img, dtype=np.uint8) > 127
            except Exception:
                continue

        # Crop a window around the tap and check overlap there
        x0 = max(0, tap_x_px - search_radius)
        y0 = max(0, tap_y_px - search_radius)
        x1 = min(image_w, tap_x_px + search_radius + 1)
        y1 = min(image_h, tap_y_px + search_radius + 1)
        if not bool(mask[y0:y1, x0:x1].any()):
            continue

        area = float(mask.sum())
        area_frac = area / img_area
        if area_frac < 0.0005 or area_frac > 0.50:
            continue

        # Distance from tap to mask centroid (used as tie-breaker)
        ys, xs = np.where(mask)
        cx_m = float(xs.mean())
        cy_m = float(ys.mean())
        d = math.hypot(cx_m - tap_x_px, cy_m - tap_y_px)

        # Composite score: smaller is better. Area dominates so we still
        # pick specific masks over the whole-back blob, but distance
        # breaks ties when areas are close.
        score = area + d * 50.0
        candidates.append((score, png_bytes, mask))

    if not candidates:
        return None

    candidates.sort(key=lambda t: t[0])
    _, png_bytes, mask = candidates[0]
    return png_bytes, mask


async def _run_sam(client: httpx.AsyncClient, body_jpeg: bytes) -> Optional[list[str]]:
    """Call meta/sam-2 → list of individual_masks URLs, or None on failure."""
    if not REPLICATE_API_TOKEN:
        return None
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    # Defaults (32 / 0.86 / 0.92) are tuned for distinct objects (cars, dogs).
    # A faded scar on skin is low contrast and SAM skips it at default
    # sensitivity. Bump points_per_side and lower thresholds so weaker
    # mask candidates make it through.
    payload = {
        "version": SAM_VERSION_ID,
        "input": {
            "image": _b64_data_url(body_jpeg),
            "use_m2m": True,
            "points_per_side": 64,
            "pred_iou_thresh": 0.70,
            "stability_score_thresh": 0.85,
        },
    }
    try:
        r = await client.post(
            SAM_PREDICTIONS_URL,
            headers=headers,
            json=payload,
            timeout=httpx.Timeout(60.0),
        )
        if r.status_code not in (200, 201):
            print(f"[SAM] API error {r.status_code}: {r.text[:300]}")
            return None
        data = r.json()
        pred_id = data.get("id")
        out = data.get("output")
        if out and isinstance(out, dict):
            urls = out.get("individual_masks") or []
            if urls:
                return list(urls)
        if not pred_id:
            return None
        get_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
        for _ in range(SAM_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(SAM_POLL_INTERVAL_SEC)
            pr = await client.get(get_url, headers=headers, timeout=httpx.Timeout(30.0))
            if pr.status_code != 200:
                continue
            d = pr.json()
            status = d.get("status")
            if status == "succeeded":
                out = d.get("output") or {}
                urls = out.get("individual_masks") or []
                return list(urls) if urls else None
            if status in ("failed", "canceled"):
                print(f"[SAM] prediction {status}: {d.get('error')!r}")
                return None
        print("[SAM] timed out waiting for prediction")
        return None
    except httpx.RequestError as e:
        print(f"[SAM] network error: {type(e).__name__}: {e}")
        return None


async def _download_masks(
    client: httpx.AsyncClient, urls: list[str], cap: int = 60
) -> list[tuple[bytes, np.ndarray]]:
    """Fetch mask PNGs in parallel and binarize."""

    async def _one(url: str) -> Optional[tuple[bytes, np.ndarray]]:
        try:
            r = await client.get(url, timeout=httpx.Timeout(30.0))
            if r.status_code != 200 or not r.content:
                return None
            png = r.content
            try:
                im = Image.open(io.BytesIO(png))
            except Exception:
                return None
            mask = _binarize_mask(im)
            if mask.sum() == 0:
                return None
            return png, mask
        except httpx.RequestError:
            return None

    tasks = [_one(u) for u in urls[:cap]]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def _crop_around_tap(
    body: Image.Image, tap_x: int, tap_y: int, tap_radius_px: int
) -> tuple[bytes, int, int, int, int]:
    """
    Crop a square window around the user's tap with margin.

    Returns (jpeg_bytes, crop_x0, crop_y0, crop_w, crop_h) so we can
    map any mask SAM finds in the crop back to the original full-image
    coordinate system.

    The crop side is `2.6 * tap_radius_px` clamped to the image bounds.
    SAM's points_per_side budget then samples this smaller window
    densely, which is the trick that catches faded / low-contrast scars.
    """
    w, h = body.size
    side = max(96, int(round(tap_radius_px * 2.6)))
    side = min(side, min(w, h))

    half = side // 2
    x0 = max(0, min(w - side, tap_x - half))
    y0 = max(0, min(h - side, tap_y - half))
    x1 = x0 + side
    y1 = y0 + side

    crop = body.crop((x0, y0, x1, y1))
    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue(), x0, y0, side, side


def _paste_crop_mask_to_full(
    crop_mask: np.ndarray,
    full_w: int,
    full_h: int,
    crop_x0: int,
    crop_y0: int,
) -> tuple[bytes, np.ndarray]:
    """Paste a crop-space binary mask onto a full-image black canvas."""
    canvas = np.zeros((full_h, full_w), dtype=np.uint8)
    ch, cw = crop_mask.shape
    canvas[crop_y0 : crop_y0 + ch, crop_x0 : crop_x0 + cw] = (
        crop_mask.astype(np.uint8) * 255
    )
    full_mask_bool = canvas > 127
    img = Image.fromarray(canvas, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), full_mask_bool


class BodyAnchor:
    """Result of automatic body-part segmentation for placement."""

    __slots__ = ("cx", "cy", "bbox_frac", "area_frac", "source")

    def __init__(
        self,
        cx: float,
        cy: float,
        bbox_frac: tuple[float, float, float, float],
        area_frac: float,
        source: str = "sam",
    ):
        self.cx = cx
        self.cy = cy
        # (x0, y0, x1, y1) in image-fraction coordinates
        self.bbox_frac = bbox_frac
        self.area_frac = area_frac
        self.source = source


# Cache for body-anchor results so a regen on the same upload doesn't pay
# for SAM twice.
_body_cache_max = 32
_body_cache: "OrderedDict[str, BodyAnchor]" = OrderedDict()


def _body_cache_key(body_jpeg: bytes) -> str:
    return hashlib.sha256(body_jpeg).hexdigest()[:16]


def _body_cache_get(key: str) -> Optional[BodyAnchor]:
    seg = _body_cache.get(key)
    if seg is not None:
        _body_cache.move_to_end(key)
    return seg


def _body_cache_put(key: str, val: BodyAnchor) -> None:
    _body_cache[key] = val
    _body_cache.move_to_end(key)
    while len(_body_cache) > _body_cache_max:
        _body_cache.popitem(last=False)


def _pick_body_mask(
    masks: list[tuple[bytes, np.ndarray]],
    image_w: int,
    image_h: int,
) -> Optional[np.ndarray]:
    """
    Score auto-mode SAM masks and pick the one most likely to be the body
    part the user is showing.

    Heuristics:
      1. Reject background-like masks: cover >65% of the frame OR touch
         all four image edges (those are the "everything else" masks).
      2. Reject tiny masks: area < 1% of image (background speckles, jewelry).
      3. Among the rest, score = area * centrality_bonus, where
         centrality_bonus is higher when the mask's centroid sits closer to
         the image center. People tend to frame their body part roughly
         centered, so this beats picking a small sleeve fold near the edge.
    """
    img_area = float(image_w * image_h)
    img_cx = image_w / 2.0
    img_cy = image_h / 2.0
    diag = math.hypot(image_w, image_h)

    candidates: list[tuple[float, np.ndarray]] = []
    for _png, mask in masks:
        if mask.shape != (image_h, image_w):
            try:
                m_img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
                m_img = m_img.resize((image_w, image_h), Image.NEAREST)
                mask = np.asarray(m_img, dtype=np.uint8) > 127
            except Exception:
                continue

        area = float(mask.sum())
        if area <= 0:
            continue
        area_frac = area / img_area
        if area_frac < 0.01 or area_frac > 0.65:
            continue

        # Background masks usually touch all four edges with substantial
        # coverage; skip them.
        edge_top = bool(mask[0, :].any())
        edge_bot = bool(mask[-1, :].any())
        edge_lft = bool(mask[:, 0].any())
        edge_rgt = bool(mask[:, -1].any())
        edges_touched = int(edge_top) + int(edge_bot) + int(edge_lft) + int(edge_rgt)
        if edges_touched >= 4:
            continue

        ys, xs = np.where(mask)
        cx = float(xs.mean())
        cy = float(ys.mean())
        d = math.hypot(cx - img_cx, cy - img_cy)
        # Centrality in [0..1], 1 = exact center.
        centrality = max(0.0, 1.0 - (d / (diag * 0.5)))

        score = area_frac * (0.6 + 0.8 * centrality)
        candidates.append((score, mask))

    if not candidates:
        return None

    candidates.sort(key=lambda t: -t[0])
    return candidates[0][1]


async def _run_sam_auto(
    client: httpx.AsyncClient,
    body_jpeg: bytes,
) -> Optional[list[str]]:
    """
    Auto-mode SAM-2 on the full body image. Lower density + lower thresholds
    than the scar path because we want decent-sized object masks (the body
    part) rather than dense sub-region segmentation.
    """
    if not REPLICATE_API_TOKEN:
        return None
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": SAM_VERSION_ID,
        "input": {
            "image": _b64_data_url(body_jpeg),
            "use_m2m": True,
            "points_per_side": 32,
            "pred_iou_thresh": 0.86,
            "stability_score_thresh": 0.92,
        },
    }
    try:
        r = await client.post(
            SAM_PREDICTIONS_URL,
            headers=headers,
            json=payload,
            timeout=httpx.Timeout(60.0),
        )
        if r.status_code not in (200, 201):
            print(f"[SAM-BODY] API error {r.status_code}: {r.text[:300]}")
            return None
        data = r.json()
        pred_id = data.get("id")
        out = data.get("output")
        if out and isinstance(out, dict):
            urls = out.get("individual_masks") or []
            if urls:
                return list(urls)
        if not pred_id:
            return None
        get_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
        for _ in range(SAM_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(SAM_POLL_INTERVAL_SEC)
            pr = await client.get(get_url, headers=headers, timeout=httpx.Timeout(30.0))
            if pr.status_code != 200:
                continue
            d = pr.json()
            status = d.get("status")
            if status == "succeeded":
                out = d.get("output") or {}
                urls = out.get("individual_masks") or []
                return list(urls) if urls else None
            if status in ("failed", "canceled"):
                print(f"[SAM-BODY] prediction {status}: {d.get('error')!r}")
                return None
        print("[SAM-BODY] timed out waiting for prediction")
        return None
    except httpx.RequestError as e:
        print(f"[SAM-BODY] network error: {type(e).__name__}: {e}")
        return None


def _downsize_for_sam(body: Image.Image, max_side: int = 768) -> bytes:
    """SAM's compute scales with input pixels; placement only needs ~1% accuracy."""
    w, h = body.size
    s = max(w, h)
    if s > max_side:
        scale = max_side / float(s)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        body = body.resize((nw, nh), Image.LANCZOS)
    buf = io.BytesIO()
    body.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


async def segment_body_anchor_async(body_jpeg: bytes) -> Optional[BodyAnchor]:
    """
    Auto-mode body-part detection. Returns the centroid + bbox of the most
    plausible body-part region in the upload, or None if SAM finds nothing
    we trust.

    The caller (couple split) should fall back to its own heuristic
    placement when this returns None — never block the request on SAM.
    """
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        return None

    key = _body_cache_key(body_jpeg)
    cached = _body_cache_get(key)
    if cached is not None:
        return cached

    try:
        body = _open_rgb(body_jpeg)
    except Exception as e:
        print(f"[SAM-BODY] cannot open body jpeg: {e}")
        return None
    full_w, full_h = body.size
    sam_jpeg = _downsize_for_sam(body)

    print(f"[SAM-BODY] running auto SAM-2 on {full_w}x{full_h} (downsized for speed)")
    async with httpx.AsyncClient() as client:
        urls = await _run_sam_auto(client, sam_jpeg)
        if not urls:
            print("[SAM-BODY] no masks returned")
            return None
        print(f"[SAM-BODY] got {len(urls)} candidate masks; downloading...")
        masks = await _download_masks(client, urls)

    if not masks:
        print("[SAM-BODY] mask downloads failed")
        return None

    # _pick_body_mask works in pixel space relative to the masks SAM produced
    # (which match the downsized image), not the original.
    sample_h, sample_w = masks[0][1].shape
    pick = _pick_body_mask(masks, sample_w, sample_h)
    if pick is None:
        print("[SAM-BODY] no plausible body mask found in candidates")
        return None

    ys, xs = np.where(pick)
    if xs.size < 16:
        return None
    cx_px = float(xs.mean())
    cy_px = float(ys.mean())
    x0 = float(xs.min()) / float(sample_w)
    y0 = float(ys.min()) / float(sample_h)
    x1 = float(xs.max() + 1) / float(sample_w)
    y1 = float(ys.max() + 1) / float(sample_h)
    cx = float(np.clip(cx_px / float(sample_w), 0.0, 1.0))
    cy = float(np.clip(cy_px / float(sample_h), 0.0, 1.0))
    area_frac = float(pick.sum()) / float(sample_w * sample_h)

    anchor = BodyAnchor(
        cx=cx,
        cy=cy,
        bbox_frac=(x0, y0, x1, y1),
        area_frac=round(area_frac, 4),
        source="sam",
    )
    _body_cache_put(key, anchor)
    print(
        f"[SAM-BODY] picked body anchor cx={cx:.3f} cy={cy:.3f} "
        f"bbox={anchor.bbox_frac} area={anchor.area_frac}"
    )
    return anchor


async def segment_scar_async(
    body_jpeg: bytes,
    tap_cx: float,
    tap_cy: float,
    tap_radius: float,
    *,
    user_description: str = "",
) -> Optional[ScarSegmentation]:
    """
    Try to segment the scar at the user's tap.

    Returns None if SAM doesn't find anything plausible — caller MUST
    treat None as "no preserve, trust the AI". We do NOT build synthetic
    fallback masks here: the prior approach of guessing scar shape from
    the user's optional description was incorrect because the description
    is for tattoo preferences, not scar metadata.

    `user_description` is accepted for forward-compat but currently unused.
    """
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        print("[SAM] no REPLICATE_API_TOKEN — skipping segmentation")
        return None

    key = _cache_key(body_jpeg, tap_cx, tap_cy, tap_radius)
    cached = _cache_get(key)
    if cached is not None:
        print("[SAM] cache hit — skipping Replicate call")
        return cached

    try:
        body = _open_rgb(body_jpeg)
    except Exception as e:
        print(f"[SAM] cannot open body jpeg: {e}")
        return None
    w, h = body.size
    tap_x = int(round(tap_cx * w))
    tap_y = int(round(tap_cy * h))
    tap_radius_px = int(round(tap_radius * min(w, h)))

    crop_jpeg, cx0, cy0, cw, ch = _crop_around_tap(body, tap_x, tap_y, tap_radius_px)
    # Tap coordinates inside the crop
    crop_tap_x = tap_x - cx0
    crop_tap_y = tap_y - cy0

    print(
        f"[SAM] running meta/sam-2 on cropped {cw}x{ch} window of {w}x{h} "
        f"image (tap=({tap_x},{tap_y}), tap_radius_px={tap_radius_px})"
    )
    async with httpx.AsyncClient() as client:
        urls = await _run_sam(client, crop_jpeg)
        if not urls:
            print("[SAM] no masks returned")
            return None
        print(f"[SAM] got {len(urls)} candidate masks; downloading...")
        masks = await _download_masks(client, urls)

    if not masks:
        print("[SAM] all mask downloads failed")
        return None

    pick = _pick_best_mask(masks, crop_tap_x, crop_tap_y, tap_radius_px, cw, ch)
    if pick is None:
        print(
            f"[SAM] no usable mask near tap ({crop_tap_x},{crop_tap_y}) in "
            f"crop — returning None (caller will skip restore)"
        )
        return None

    _, crop_mask = pick
    full_png, full_mask = _paste_crop_mask_to_full(crop_mask, w, h, cx0, cy0)
    geom = _analyze_geometry(full_mask, w, h)
    seg = ScarSegmentation(
        mask_png=full_png,
        width=w,
        height=h,
        geometry=geom,
        mask_source="sam",
    )
    _cache_put(key, seg)
    print(
        f"[SAM] picked mask: shape={geom['shape']} length={geom['length_pct']}% "
        f"angle={geom['angle_deg']}° aspect={geom['aspect']} area={geom['area_pct']}%"
    )
    return seg
