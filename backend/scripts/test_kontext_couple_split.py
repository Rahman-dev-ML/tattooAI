"""
End-to-end test of Flux Kontext Multi-Image as the placement engine for
the couple "complementary split" feature.

Why this script exists
----------------------
We've burned several iterations on placing half-tattoos onto user photos
with `prunaai/p-image-edit` + SAM compositing. The single-image edit
models cannot reason about "the other half lives on a different photo",
and our deterministic compositing keeps breaking when body parts vary.

`flux-kontext-apps/multi-image-kontext-max` accepts TWO input images and
combines them, which is the model class designed for our exact problem
("apply this design to that body"). Before committing real code to it
we want concrete evidence on a real pair of photos.

What this script does
---------------------
  1. Generates ONE asymmetric profile-pose tattoo stencil using the
     same prompt the production pipeline uses.
  2. Splits it deterministically at the ink-bbox midline.
  3. Calls Flux Kontext Multi-Image Max twice:
       - Partner A: [photo_a, left_half_stencil] -> placement prompt
       - Partner B: [photo_b, right_half_stencil] -> placement prompt
  4. Saves every intermediate (stencil, halves, two placements) and a
     side-by-side preview into `backend/scripts/out/` so you can flip
     through them and judge.

Cost per run
------------
  - 1x prunaai/p-image-edit (stencil) ~ $0.01
  - 1x retry if stencil came back symmetric ~ $0.01 (worst case)
  - 2x flux-kontext-multi-image-max @ $0.08 each = $0.16
  Total worst-case: ~$0.18.

Run
---
  python -m scripts.test_kontext_couple_split <photo_a.jpg> <photo_b.jpg> [theme]

  Example:
    python -m scripts.test_kontext_couple_split test/a.jpg test/b.jpg "eagle in flight"

The script must be executed from `backend/` so the `app.*` imports resolve.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import random
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

# Re-use production prompt builders and helpers so the test exercises the
# real pipeline, not a duplicate.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.pipeline.replicate_tattoo import (  # noqa: E402
    PREDICTIONS_URL,
    _b64_image,
    _build_couple_asymmetric_stencil_prompt,
    _build_white_seed_jpeg,
    _compose_side_by_side,
    _split_stencil_at_midline,
    _stencil_asymmetry_score,
)
from app.pipeline.prompts import _normalize_style  # noqa: E402

KONTEXT_PREDICTIONS_URL = (
    "https://api.replicate.com/v1/models/flux-kontext-apps/"
    "multi-image-kontext-max/predictions"
)
KONTEXT_POLL_INTERVAL_SEC = 1.0
KONTEXT_POLL_MAX_ATTEMPTS = 90  # Kontext Max usually completes in 15-40s

OUT_DIR = Path(__file__).resolve().parent / "out"


def _load_token() -> str:
    tok = os.environ.get("REPLICATE_API_TOKEN", "")
    if tok:
        return tok
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("REPLICATE_API_TOKEN="):
                v = line.split("=", 1)[1].strip().strip("\"'")
                if v:
                    os.environ["REPLICATE_API_TOKEN"] = v
                    return v
    raise RuntimeError("REPLICATE_API_TOKEN missing — set it in backend/.env or env var")


def _read_jpeg(path: str) -> bytes:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{path} not found")
    raw = p.read_bytes()
    # Normalize to JPEG so Kontext gets a predictable mime type.
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    # Cap to a sane max side so we don't waste tokens / time on giant uploads.
    max_side = 1280
    if max(im.size) > max_side:
        scale = max_side / float(max(im.size))
        im = im.resize(
            (int(im.width * scale), int(im.height * scale)),
            Image.LANCZOS,
        )
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=92, optimize=True)
    return buf.getvalue()


async def _replicate_p_image_edit(
    client: httpx.AsyncClient,
    image_jpegs: list[bytes],
    prompt: str,
    seed: int,
    token: str,
) -> tuple[bytes | None, str | None]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "images": [_b64_image(b) for b in image_jpegs],
            "prompt": prompt,
            "aspect_ratio": "match_input_image",
            "seed": seed,
            "turbo": True,
        }
    }
    r = await client.post(
        PREDICTIONS_URL, headers=headers, json=payload, timeout=httpx.Timeout(180.0)
    )
    if r.status_code not in (200, 201):
        return None, f"p-image-edit error {r.status_code}: {r.text[:300]}"
    out = r.json().get("output")
    if not out:
        return None, "p-image-edit returned empty output"
    url = out if isinstance(out, str) else out[0]
    img = await client.get(url, timeout=httpx.Timeout(60.0))
    if img.status_code != 200:
        return None, f"download failed: {img.status_code}"
    return img.content, None


async def _replicate_kontext_multi(
    client: httpx.AsyncClient,
    image_1: bytes,
    image_2: bytes,
    prompt: str,
    seed: int,
    token: str,
) -> tuple[bytes | None, str | None]:
    """flux-kontext-apps/multi-image-kontext-max — combines two images."""
    headers = {
        "Authorization": f"Bearer {token}",
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
    r = await client.post(
        KONTEXT_PREDICTIONS_URL,
        headers=headers,
        json=payload,
        timeout=httpx.Timeout(180.0),
    )
    if r.status_code not in (200, 201):
        return None, f"kontext start error {r.status_code}: {r.text[:300]}"

    pred = r.json()
    poll_url = pred.get("urls", {}).get("get") or pred.get("urls", {}).get("stream")
    output = pred.get("output")
    status = pred.get("status")

    # Some endpoints return immediately with output populated; others need polling.
    if output is None and poll_url:
        for _ in range(KONTEXT_POLL_MAX_ATTEMPTS):
            await asyncio.sleep(KONTEXT_POLL_INTERVAL_SEC)
            pr = await client.get(poll_url, headers=headers, timeout=httpx.Timeout(60.0))
            if pr.status_code != 200:
                continue
            pj = pr.json()
            status = pj.get("status")
            if status == "succeeded":
                output = pj.get("output")
                break
            if status in ("failed", "canceled"):
                return None, f"kontext {status}: {pj.get('error', '')[:300]}"
        if output is None:
            return None, f"kontext poll timed out (status={status})"

    if not output:
        return None, f"kontext returned no output (status={status})"

    url = output if isinstance(output, str) else output[0]
    img = await client.get(url, timeout=httpx.Timeout(60.0))
    if img.status_code != 200:
        return None, f"kontext download failed: {img.status_code}"
    return img.content, None


def _save(name: str, blob: bytes) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_bytes(blob)
    return path


KONTEXT_PLACEMENT_PROMPT = (
    "Place the tattoo design shown in the second image onto the visible "
    "body part of the person in the first image, as a realistic professional "
    "healed tattoo. The tattoo's ink must sit ON the skin with proper dermal "
    "absorption, natural lighting matching the surrounding skin, and follow "
    "the body's curvature — NEVER painted onto the background, clothing, or "
    "outside the body. The design's shape, proportions and orientation "
    "must match the second image EXACTLY — do NOT add missing parts, do NOT "
    "draw a complete bilaterally-symmetric subject, do NOT mirror the "
    "design. Keep every other pixel of the first image identical. No text, "
    "letters, watermarks or pseudo-glyphs."
)


async def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python -m scripts.test_kontext_couple_split "
            "<photo_a.jpg> <photo_b.jpg> [theme]"
        )
        sys.exit(1)

    photo_a_path = sys.argv[1]
    photo_b_path = sys.argv[2]
    theme = sys.argv[3] if len(sys.argv) > 3 else "phoenix in flight"

    token = _load_token()
    print(f"[TEST] theme={theme!r}")
    print(f"[TEST] photo_a={photo_a_path} photo_b={photo_b_path}")

    photo_a = _read_jpeg(photo_a_path)
    photo_b = _read_jpeg(photo_b_path)
    _save("00_photo_a.jpg", photo_a)
    _save("00_photo_b.jpg", photo_b)

    style = _normalize_style("auto")
    stencil_prompt = _build_couple_asymmetric_stencil_prompt(theme, style)
    white_seed = _build_white_seed_jpeg()
    stencil_seed = random.randint(1, 999_999_999)

    async with httpx.AsyncClient(http2=False) as client:
        t0 = time.time()
        print(f"[TEST] generating stencil (seed={stencil_seed}) ...")
        stencil_blob, stencil_err = await _replicate_p_image_edit(
            client, [white_seed], stencil_prompt, stencil_seed, token
        )
        if not stencil_blob:
            print(f"[TEST] stencil failed: {stencil_err}")
            sys.exit(2)

        asym = _stencil_asymmetry_score(stencil_blob)
        print(f"[TEST] stencil ready in {time.time()-t0:.1f}s asym_score={asym:.3f}")
        if asym < 0.18:
            retry_seed = random.randint(1, 999_999_999)
            print(f"[TEST] stencil symmetric — retrying seed={retry_seed}")
            retry_blob, retry_err = await _replicate_p_image_edit(
                client,
                [white_seed],
                stencil_prompt
                + "\nCRITICAL OVERRIDE: previous attempt was symmetric. "
                "Pure profile/side view, all weight asymmetric.",
                retry_seed,
                token,
            )
            if retry_blob:
                rs = _stencil_asymmetry_score(retry_blob)
                print(f"[TEST] retry asym_score={rs:.3f}")
                if rs > asym:
                    stencil_blob = retry_blob
                    asym = rs

        _save("01_stencil_full.jpg", stencil_blob)

        left_half, right_half = _split_stencil_at_midline(stencil_blob)
        _save("02_left_half.jpg", left_half)
        _save("02_right_half.jpg", right_half)

        seed_a = random.randint(1, 999_999_999)
        seed_b = max(1, (seed_a + 17_371) % 999_999_999)

        print(f"[TEST] kontext A (seed={seed_a}) ...")
        a_blob, a_err = await _replicate_kontext_multi(
            client, photo_a, left_half, KONTEXT_PLACEMENT_PROMPT, seed_a, token
        )
        if not a_blob:
            print(f"[TEST] kontext A failed: {a_err}")
            sys.exit(3)
        _save("03_kontext_partner_a.png", a_blob)

        print(f"[TEST] kontext B (seed={seed_b}) ...")
        b_blob, b_err = await _replicate_kontext_multi(
            client, photo_b, right_half, KONTEXT_PLACEMENT_PROMPT, seed_b, token
        )
        if not b_blob:
            print(f"[TEST] kontext B failed: {b_err}")
            sys.exit(4)
        _save("03_kontext_partner_b.png", b_blob)

    pair_jpeg = _compose_side_by_side(a_blob, b_blob)
    _save("04_pair_side_by_side.jpg", pair_jpeg)

    print(f"\n[TEST] DONE. Outputs in: {OUT_DIR}")
    print("       Inspect 04_pair_side_by_side.jpg first, then the halves.")


if __name__ == "__main__":
    asyncio.run(main())
