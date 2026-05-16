"""
HTTP routes: validate input → call Replicate → attach advisory fit score (rule-based).

`POST /api/generate` is the hot path: bounded upload read, JSON size cap, optional API key,
and rate limit per client IP (in-process; use Redis-backed limiter at the edge for many nodes).
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

import base64 as _b64

from .config import get_settings
from .deps_auth import verify_service_key
from . import database as db
from .pipeline.fit_score import advisory_score_for_concept, compute_fit
from .pipeline.flux_inpaint import (
    build_scar_transform_mask,
    build_scar_transform_prompt,
    replicate_flux_fill_pro,
)
from .pipeline.prompts import get_scar_transform_components, resolve_style
from .pipeline.replicate_tattoo import (
    REPLICATE_API_TOKEN,
    generate_couple_preview,
    generate_faded_tattoo,
    generate_tattoo_concepts,
)
from .pipeline.scar_preserve import parse_mark_string, restore_scar_from_mask
from .pipeline.scar_segment import segment_scar_async
from .rate_limit import limiter
from .upload_io import preprocess_image_to_jpeg, read_upload_bytes

router = APIRouter()

VALID_FLOWS = frozenset(
    {
        "new_to_tattoos",
        "from_idea",
        "photo_convert",
        "deep_meaning",
        "scar_coverup",
        "tattoo_fade",
    }
)

_GEN_LIMIT = os.environ.get("GENERATE_RATE_LIMIT", "20/minute")
_STATUS_LIMIT = os.environ.get("STATUS_RATE_LIMIT", "120/minute")
_MAX_CONCURRENT_GENERATIONS = get_settings()["max_concurrent_generations"]
_GENERATION_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_GENERATIONS)


async def _run_with_generation_slot(awaitable):
    async with _GENERATION_SEMAPHORE:
        return await awaitable


def _resolved_style(flow_id: str, answers: dict[str, Any]) -> str:
    """Same style the prompt builder will use (so labels/fit match the actual prompt)."""
    return resolve_style(flow_id, answers)


def _short_explanation(flow_id: str, answers: dict[str, Any], index: int) -> str:
    if flow_id == "from_idea":
        base = f"Concept {index + 1} based on your idea, tuned for your placement."
    elif flow_id == "new_to_tattoos":
        base = f"Direction {index + 1} aligned with your goals and coverage choice."
    elif flow_id == "photo_convert":
        base = f"Interpretation {index + 1} translating your reference into tattoo-friendly linework."
    elif flow_id == "scar_coverup":
        base = f"Cover-up design {index + 1} crafted to camouflage and beautify the scar area."
    elif flow_id == "tattoo_fade":
        strength = str(answers.get("fade_strength") or "moderate").lower()
        years = {"subtle": "2-3", "moderate": "5-7", "heavy": "10-15"}.get(strength, "5-7")
        base = (
            f"Aging simulation — your tattoo at roughly {years} years of "
            f"natural skin wear and ink fade."
        )
    else:
        base = f"Symbolic direction {index + 1} reflecting your theme and expression."

    return base + " Refine with your artist before inking."


@limiter.limit(_GEN_LIMIT)
@router.post("/api/generate")
async def generate(
    request: Request,
    image: UploadFile = File(...),
    flow_id: str = Form(...),
    answers_json: str = Form(...),
    num_concepts: int = Form(1),
    reference_image: Optional[UploadFile] = File(None),
    _: bool = Depends(verify_service_key),
    x_device_id: Optional[str] = None,
):
    # Extract device ID from header manually (FastAPI Header() doesn't mix well with Depends)
    x_device_id = request.headers.get("X-Device-ID")

    # Credit check — deduct before running expensive AI call
    credits_remaining: Optional[int] = None
    if x_device_id:
        credits_remaining = await db.deduct_credit(x_device_id)
        if credits_remaining == -1:
            raise HTTPException(
                status_code=402,
                detail="No credits remaining. Purchase more to continue.",
                headers={"X-Credits-Remaining": "0"},
            )

    if flow_id not in VALID_FLOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid flow_id. Expected one of {sorted(VALID_FLOWS)}",
        )

    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        raise HTTPException(
            status_code=503,
            detail="AI generation not configured. Set REPLICATE_API_TOKEN in backend/.env",
        )

    settings = get_settings()
    max_json = settings["max_answers_json_bytes"]
    if len(answers_json.encode("utf-8")) > max_json:
        raise HTTPException(status_code=400, detail="answers_json too large")

    try:
        answers: dict[str, Any] = json.loads(answers_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid answers_json: {e}") from e

    if not isinstance(answers, dict):
        raise HTTPException(status_code=400, detail="answers_json must be an object")

    raw = await read_upload_bytes(image, settings["max_upload_bytes"])
    image_bytes = preprocess_image_to_jpeg(raw)

    reference_jpeg: Optional[bytes] = None
    if reference_image and reference_image.filename:
        ref_raw = await read_upload_bytes(reference_image, settings["max_upload_bytes"])
        reference_jpeg = preprocess_image_to_jpeg(ref_raw)

    # Faded-tattoo flow: fast path. Single prunaai/p-image-edit call
    # with a fade-specialised prompt. No SAM, no scar logic, no body-
    # region resolving, no fit-style tuning — just age the existing ink.
    if flow_id == "tattoo_fade":
        cap = settings["max_concepts_per_request"]
        n_fade = max(1, min(cap, int(num_concepts or 1)))
        fade_concepts, fade_err = await _run_with_generation_slot(
            generate_faded_tattoo(image_bytes, answers, num_concepts=n_fade)
        )
        if fade_err or not fade_concepts:
            msg = fade_err or "Fade generation failed"
            status = 500
            if isinstance(msg, str) and (
                "Network error" in msg
                or "cannot reach Replicate" in msg
                or "getaddrinfo" in msg.lower()
            ):
                status = 503
            raise HTTPException(status_code=status, detail=msg)

        strength = str(answers.get("fade_strength") or "moderate").lower()
        years_label = {
            "subtle": "~2-3 years",
            "moderate": "~5-7 years",
            "heavy": "~10-15 years",
        }.get(strength, "~5-7 years")

        concepts_out: list[dict[str, Any]] = []
        for i, c in enumerate(fade_concepts):
            concepts_out.append(
                {
                    "id": f"c{i + 1}",
                    "variant_index": c["variant_index"],
                    "image_base64": c["image_base64"],
                    "media_type": c.get("media_type", "image/jpeg"),
                    "style_label": f"Faded · {strength.title()}",
                    "coverage_label": years_label,
                    "explanation": _short_explanation(flow_id, answers, i),
                    "advisory_score": None,
                }
            )

        fade_headers = {}
        if credits_remaining is not None:
            fade_headers["X-Credits-Remaining"] = str(credits_remaining)
        return JSONResponse(
            {
                "flow_id": flow_id,
                "concepts": concepts_out,
                "fit": {
                    "score": 0,
                    "summary": (
                        "Aging simulation only — no placement / coverage scoring. "
                        "Use this as a long-term planning aid."
                    ),
                    "factors": [],
                },
                "disclaimer": (
                    "Visual simulation of long-term ink fade. Real-world fading "
                    "depends on placement, sun exposure, skin type and aftercare."
                ),
                "replicate_calls": len(concepts_out),
            },
            headers=fade_headers,
        )

    # Scar segmentation (Tier B): for the scar_coverup flow we run SAM-2
    # FIRST so the prompt builder has the real scar geometry. Without it
    # the model has to guess where the scar is from words alone, which is
    # the failure that ships "vertical halves" tattoos on diagonal scars.
    scar_segmentation = None
    if flow_id == "scar_coverup":
        mark = parse_mark_string(str(answers.get("scar_mark") or ""))
        if mark is not None:
            user_desc = str(answers.get("scar_description") or "")
            try:
                scar_segmentation = await segment_scar_async(
                    image_bytes, *mark, user_description=user_desc
                )
            except Exception as ex:  # pragma: no cover
                print(f"[SCAR_SEGMENT] failed: {type(ex).__name__}: {ex}")
                scar_segmentation = None
            if scar_segmentation is not None:
                answers["scar_geometry"] = scar_segmentation.geometry

    cap = settings["max_concepts_per_request"]
    default_n = settings["default_concepts"]
    n = int(num_concepts) if num_concepts else default_n
    n = max(1, min(cap, n))

    concepts_raw: list[dict[str, Any]] = []
    err: Optional[str] = None

    # Scar-coverup TRANSFORM (special path): instead of the instruction-style
    # prunaai/p-image-edit + radial pixel-restore (which produced "tattoo
    # painted across the whole area, then a bare circle punched through it"),
    # we use Flux Fill Pro inpaint with a precisely-shaped mask:
    #
    #   - WHITE region of the mask = oriented ellipse around the scar where
    #     the tattoo is allowed to be painted (the model literally cannot
    #     paint elsewhere).
    #   - BLACK region INCLUDES the scar itself, so the model physically
    #     cannot paint over the scar tissue.
    #
    # The result is a tattoo that grows AROUND the scar's true silhouette —
    # which is what "transform" was always supposed to mean.
    transform_handled = False
    if (
        flow_id == "scar_coverup"
        and str(answers.get("scar_strategy") or "").lower() == "transform"
        and scar_segmentation is not None
    ):
        try:
            mask_png = build_scar_transform_mask(
                scar_segmentation.mask_png,
                scar_segmentation.geometry,
                scar_segmentation.width,
                scar_segmentation.height,
            )
        except Exception as ex:  # pragma: no cover
            print(f"[SCAR_TRANSFORM] mask build failed: {type(ex).__name__}: {ex}")
            mask_png = None

        if mask_png:
            style_for_scar = resolve_style(flow_id, answers)
            scar_type = str(answers.get("scar_type") or "")
            scar_shape_hint = str(answers.get("scar_shape") or "")

            print(
                f"[SCAR_TRANSFORM] flux-fill-pro path: variants={n} style={style_for_scar} "
                f"scar_shape={scar_segmentation.geometry.get('shape')} "
                f"length={scar_segmentation.geometry.get('length_pct')}%"
            )

            run_salt = int.from_bytes(os.urandom(4), "big")
            tasks = []
            seeds: list[int] = []
            prompts: list[str] = []
            for i in range(n):
                style_render, motif, is_sensitive, geom_used = get_scar_transform_components(
                    style=style_for_scar,
                    scar_type=scar_type,
                    scar_shape=scar_shape_hint,
                    scar_geometry=scar_segmentation.geometry,
                    variant_index=i,
                    run_salt=run_salt,
                )
                fp = build_scar_transform_prompt(
                    style_render=style_render,
                    motif_phrase=motif,
                    geometry=geom_used,
                    is_sensitive=is_sensitive,
                )
                seed = int.from_bytes(os.urandom(4), "big") % 999_999_999
                seeds.append(seed)
                prompts.append(fp)
                print(f"[SCAR_TRANSFORM] v{i} seed={seed} motif={motif!r}")
                tasks.append(
                    replicate_flux_fill_pro(
                        image_bytes,
                        mask_png,
                        fp,
                        seed=seed,
                    )
                )

            results = await asyncio.gather(*tasks)
            for i, (img_bytes, ferr) in enumerate(results):
                if img_bytes:
                    concepts_raw.append(
                        {
                            "variant_index": i,
                            "seed": seeds[i],
                            "image_base64": _b64.b64encode(img_bytes).decode("ascii"),
                            "media_type": "image/jpeg",
                        }
                    )
                elif ferr:
                    print(f"[SCAR_TRANSFORM] v{i} failed: {ferr}")
                    err = ferr

            transform_handled = bool(concepts_raw)

    if not transform_handled:
        # Default path: instruction-style p-image-edit for everything else
        # (including scar camouflage / overshadow, and scar transform when
        # SAM couldn't isolate the scar — caller falls back to the prompt's
        # tap-location hint).
        concepts_raw, err = await _run_with_generation_slot(
            generate_tattoo_concepts(
                image_bytes,
                flow_id,
                answers,
                num_concepts=n,
                reference_jpeg=reference_jpeg,
            )
        )

    if err or not concepts_raw:
        msg = err or "Generation failed"
        status = 500
        if isinstance(msg, str) and (
            "Network error" in msg
            or "cannot reach Replicate" in msg
            or "getaddrinfo" in msg.lower()
        ):
            status = 503
        raise HTTPException(status_code=status, detail=msg)

    # Legacy radial pixel-restore for the rare case where TRANSFORM fell
    # through to the regular path (SAM didn't isolate the scar). We keep it
    # as a defensive net so a faded scar still doesn't get fully painted
    # over. The Flux path above handles the happy case natively.
    if (
        flow_id == "scar_coverup"
        and not transform_handled
        and str(answers.get("scar_strategy") or "").lower() == "transform"
        and scar_segmentation is not None
        and concepts_raw
    ):
        print(
            "[SCAR_PRESERVE] transform fallback: applying radial mask restore "
            f"(shape={scar_segmentation.geometry['shape']}, "
            f"length={scar_segmentation.geometry['length_pct']}%)"
        )
        preserved: list[dict[str, Any]] = []
        for c in concepts_raw:
            gen_b64 = c.get("image_base64")
            if not gen_b64:
                preserved.append(c)
                continue
            try:
                gen_bytes = _b64.b64decode(gen_b64)
                new_bytes = restore_scar_from_mask(
                    image_bytes,
                    gen_bytes,
                    scar_segmentation.mask_png,
                    feather_px=6,
                    strength=1.0,
                )
                c2 = dict(c)
                c2["image_base64"] = _b64.b64encode(new_bytes).decode("ascii")
                preserved.append(c2)
            except Exception as ex:  # pragma: no cover
                print(f"[SCAR_PRESERVE] restore failed for variant {c.get('variant_index')}: {ex}")
                preserved.append(c)
        concepts_raw = preserved

    body_region = str(answers.get("body_region") or "other")
    coverage = str(answers.get("coverage") or "medium")
    style = _resolved_style(flow_id, answers)
    fit = compute_fit(body_region, coverage, style)

    style_label = style.replace("_", " ").title() if style != "auto" else "AI-balanced"
    cov_label = coverage.title() if coverage else "Medium"

    concepts_out: list[dict[str, Any]] = []
    for i, c in enumerate(concepts_raw):
        adv = advisory_score_for_concept(
            body_region, coverage, style, c["variant_index"], int(c.get("seed", 0))
        )
        concepts_out.append(
            {
                "id": f"c{i + 1}",
                "variant_index": c["variant_index"],
                "image_base64": c["image_base64"],
                "media_type": c.get("media_type", "image/jpeg"),
                "style_label": style_label,
                "coverage_label": cov_label,
                "explanation": _short_explanation(flow_id, answers, i),
                "advisory_score": adv,
            }
        )

    gen_headers = {}
    if credits_remaining is not None:
        gen_headers["X-Credits-Remaining"] = str(credits_remaining)
    return JSONResponse(
        {
            "flow_id": flow_id,
            "concepts": concepts_out,
            "fit": fit,
            "disclaimer": "Visual simulation for planning only — not medical advice.",
            "replicate_calls": len(concepts_out),
        },
        headers=gen_headers,
    )


@limiter.limit(_GEN_LIMIT)
@router.post("/api/generate-couple")
async def generate_couple(
    request: Request,
    answers_json: str = Form(...),
    image_a: UploadFile | None = File(None),
    image_b: UploadFile | None = File(None),
    _: bool = Depends(verify_service_key),
):
    # Credit check
    x_device_id = request.headers.get("X-Device-ID")
    couple_credits_remaining: Optional[int] = None
    if x_device_id:
        couple_credits_remaining = await db.deduct_credit(x_device_id)
        if couple_credits_remaining == -1:
            raise HTTPException(
                status_code=402,
                detail="No credits remaining. Purchase more to continue.",
                headers={"X-Credits-Remaining": "0"},
            )
    if not REPLICATE_API_TOKEN or len(REPLICATE_API_TOKEN) < 10:
        raise HTTPException(
            status_code=503,
            detail="AI generation not configured. Set REPLICATE_API_TOKEN in backend/.env",
        )

    settings = get_settings()
    max_json = settings["max_answers_json_bytes"]
    if len(answers_json.encode("utf-8")) > max_json:
        raise HTTPException(status_code=400, detail="answers_json too large")

    try:
        answers: dict[str, Any] = json.loads(answers_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid answers_json: {e}") from e
    if not isinstance(answers, dict):
        raise HTTPException(status_code=400, detail="answers_json must be an object")

    # complementary_split mode is photoless — backend generates a stencil
    # and splits it on a neutral skin canvas. matching_pair mode still
    # requires both partner photos for the parallel two-body edits.
    mode = str(answers.get("couple_mode") or "matching_pair").strip().lower()
    if mode == "complementary_split":
        jpeg_a = b""
        jpeg_b = b""
    else:
        if image_a is None or image_b is None:
            raise HTTPException(
                status_code=400,
                detail="Matching pair mode requires both partner photos.",
            )
        raw_a = await read_upload_bytes(image_a, settings["max_upload_bytes"])
        raw_b = await read_upload_bytes(image_b, settings["max_upload_bytes"])
        jpeg_a = preprocess_image_to_jpeg(raw_a)
        jpeg_b = preprocess_image_to_jpeg(raw_b)

    bundle, err = await _run_with_generation_slot(
        generate_couple_preview(jpeg_a, jpeg_b, answers)
    )
    if err or not bundle:
        msg = err or "Couple generation failed"
        status = 500
        if isinstance(msg, str) and (
            "Network error" in msg
            or "cannot reach Replicate" in msg
            or "getaddrinfo" in msg.lower()
        ):
            status = 503
        raise HTTPException(status_code=status, detail=msg)

    cov = str(answers.get("shared_coverage") or "medium")
    mode = str(answers.get("couple_mode") or "matching_pair").replace("_", " ").title()
    style_a = _resolved_style("from_idea", {"style": answers.get("person_a_style", "auto")})
    style_b = _resolved_style("from_idea", {"style": answers.get("person_b_style", "auto")})

    region_a = str(answers.get("person_a_body_region") or "from_photo")
    region_b = str(answers.get("person_b_body_region") or "from_photo")
    fit_a = compute_fit(region_a, cov, style_a)
    fit_b = compute_fit(region_b, cov, style_b)
    pair_score = int(round((fit_a["score"] + fit_b["score"]) / 2.0))

    couple_headers = {}
    if couple_credits_remaining is not None:
        couple_headers["X-Credits-Remaining"] = str(couple_credits_remaining)
    return JSONResponse(
        {
            "flow_id": "couple_tattoo",
            "concepts": [
                {
                    "id": "c1",
                    "variant_index": 0,
                    "image_base64": bundle["pair_image_base64"],
                    "media_type": bundle.get("media_type", "image/jpeg"),
                    "style_label": mode,
                    "coverage_label": cov.title(),
                    "explanation": (
                        f"{mode} blueprint {bundle['pair_spec']['pair_id']} — coordinated tattoos "
                        f"designed as a unique pair."
                    ),
                    "advisory_score": pair_score,
                }
            ],
            "fit": {
                "score": pair_score,
                "summary": "Pair fit combines both placements and style constraints into one coordinated result.",
                "factors": [
                    {"key": "partner_a", "label": "Partner A fit", "value": fit_a["score"]},
                    {"key": "partner_b", "label": "Partner B fit", "value": fit_b["score"]},
                    {"key": "pair_link", "label": "Pair cohesion", "value": 95},
                ],
            },
            "disclaimer": "Visual simulation for planning only — not medical advice.",
            "replicate_calls": 2,
            "couple": {
                "pair_id": bundle["pair_spec"]["pair_id"],
                "mode": bundle["pair_spec"]["mode"],
                "left_image_base64": bundle["left_image_base64"],
                "right_image_base64": bundle["right_image_base64"],
                "pair_image_base64": bundle["pair_image_base64"],
                "media_type": bundle.get("media_type", "image/jpeg"),
            },
        },
        headers=couple_headers,
    )


@limiter.limit(_STATUS_LIMIT)
@router.get("/api/ai-status")
async def ai_status(request: Request):
    ok = bool(REPLICATE_API_TOKEN and len(REPLICATE_API_TOKEN) > 10)
    return {
        "ai_available": ok,
        "message": "Ready" if ok else "Set REPLICATE_API_TOKEN in backend/.env",
    }
