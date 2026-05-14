"""
Central configuration from environment.

Why: one place to tune limits for staging vs production without hunting literals.
At very large scale: move rate limits to Redis/Edge (see README); this stays stateless-friendly.
"""
from __future__ import annotations

import os
from functools import lru_cache


@lru_cache
def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@lru_cache
def get_settings() -> dict:
    """Immutable snapshot of security and provider settings."""
    return {
        "app_env": os.environ.get("APP_ENV", "development").strip().lower(),
        "replicate_token_configured": bool(
            len(os.environ.get("REPLICATE_API_TOKEN", "").strip()) > 10
        ),
        "require_api_key": _env_bool("REQUIRE_API_KEY", True),
        "service_api_key": os.environ.get("TATTOO_SERVICE_KEY", "").strip(),
        "cors_origins": os.environ.get("CORS_ORIGINS", "http://localhost:3000"),
        "max_upload_bytes": int(os.environ.get("MAX_UPLOAD_MB", "8")) * 1024 * 1024,
        "max_answers_json_bytes": int(os.environ.get("MAX_ANSWERS_JSON_BYTES", "65536")),
        "generate_rate_limit": os.environ.get("GENERATE_RATE_LIMIT", "20/minute"),
        "status_rate_limit": os.environ.get("STATUS_RATE_LIMIT", "120/minute"),
        "max_concurrent_generations": max(1, int(os.environ.get("MAX_CONCURRENT_GENERATIONS", "8"))),
        "max_concepts_per_request": min(4, max(1, int(os.environ.get("MAX_CONCEPTS", "3")))),
        "default_concepts": min(
            min(4, max(1, int(os.environ.get("MAX_CONCEPTS", "3")))),
            max(1, int(os.environ.get("DEFAULT_CONCEPTS", "1"))),
        ),
    }
