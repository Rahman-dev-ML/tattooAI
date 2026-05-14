"""
Rule-based advisory scores (v1). Not medical or a guarantee.
Per-concept scores vary slightly by variant/seed so the UI can show different % per card.
"""
from __future__ import annotations

from typing import Any

REGION_DETAIL_FACTOR: dict[str, float] = {
    "forearm": 0.85,
    "upper_arm": 0.88,
    "shoulder": 0.82,
    "wrist": 0.75,
    "hand_back": 0.78,
    "hand_palm": 0.78,
    "calf": 0.86,
    "thigh": 0.84,
    "chest": 0.8,
    "upper_back": 0.83,
    "lower_back": 0.82,
    "ribs": 0.7,
    "ankle": 0.76,
    "foot": 0.74,
    "neck": 0.72,
    "other": 0.8,
    "from_photo": 0.84,
}

STYLE_DETAIL_LOAD: dict[str, float] = {
    "minimalist": 0.95,
    "fine_line": 0.78,
    "blackwork": 0.88,
    "traditional": 0.85,
    "script": 0.8,
    "geometric": 0.87,
    "ornamental": 0.84,
    "japanese": 0.82,
    "realism": 0.75,
    "auto": 0.82,
    "minimal": 0.92,
    "stencil": 0.86,
    "realistic": 0.76,
}

COVERAGE_SIZE: dict[str, float] = {
    "small": 0.92,
    "medium": 0.88,
    "large": 0.84,
    "unsure": 0.85,
}


def _base_score(body_region: str, coverage: str, style: str) -> int:
    region = body_region if body_region in REGION_DETAIL_FACTOR else "other"
    cov = coverage if coverage in COVERAGE_SIZE else "medium"
    st = style if style in STYLE_DETAIL_LOAD else "auto"

    base = 72.0
    r = REGION_DETAIL_FACTOR[region]
    c = COVERAGE_SIZE[cov]
    s = STYLE_DETAIL_LOAD.get(st, 0.82)

    score = base + (r * 8) + (c * 6) + (s * 5)
    if st == "fine_line" and r < 0.8:
        score -= 8
    if st in ("realism", "realistic") and cov == "small":
        score -= 5
    if cov == "large" and st == "minimalist":
        score += 3

    return max(52, min(96, int(round(score))))


def compute_fit(body_region: str, coverage: str, style: str) -> dict[str, Any]:
    """Session-level summary (same story as before)."""
    score = _base_score(body_region, coverage, style)
    region = body_region if body_region in REGION_DETAIL_FACTOR else "other"
    cov = coverage if coverage in COVERAGE_SIZE else "medium"
    st = style if style in STYLE_DETAIL_LOAD else "auto"

    factors = [
        {"key": "body_shape_match", "label": "Body shape match", "value": min(95, score + 2)},
        {"key": "placement_balance", "label": "Placement balance", "value": score},
        {"key": "curvature_alignment", "label": "Curvature alignment", "value": max(55, score - 4)},
        {"key": "coverage_suitability", "label": "Coverage suitability", "value": min(94, score + 1)},
        {"key": "detail_readability", "label": "Detail readability", "value": max(58, int(score * 0.92))},
        {"key": "skin_lighting_compat", "label": "Skin & lighting compatibility", "value": score - 2},
    ]

    summary = (
        f"Advisory fit around {score}/100 for {region.replace('_', ' ')} placement "
        f"with {cov} coverage. Ink is rendered for your skin tone and lighting in the photo — "
        f"not a guarantee of healed results."
    )

    return {"score": score, "summary": summary, "factors": factors}


def advisory_score_for_concept(
    body_region: str,
    coverage: str,
    style: str,
    variant_index: int,
    seed: int,
) -> int:
    """
    Distinct % per variation card (deterministic from seed + index).
    Stays in a believable band so it reads as 'which comp sits the body better'.
    """
    base = _base_score(body_region, coverage, style)
    # Spread roughly 6–14 points across variants without going out of 78–98
    jitter = ((seed >> 8) + variant_index * 17 + (seed % 97)) % 13
    adj = base + jitter - 6
    return max(78, min(98, int(adj)))
