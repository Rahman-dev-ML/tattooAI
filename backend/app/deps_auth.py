"""
Optional service-to-service authentication.

Browsers should not embed long-lived secrets. Prefer:
- REQUIRE_API_KEY=false + rate limits + CDN/WAF for public MVP, or
- Next.js BFF (`app/api/tattoo/generate`) with TATTOO_SERVICE_KEY server-side only.
"""
from __future__ import annotations

from fastapi import Header, HTTPException

from .config import get_settings


def verify_service_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> bool:
    """Returns True if auth passes; raises 401/500 otherwise."""
    s = get_settings()
    if not s["require_api_key"]:
        return True
    expected = s["service_api_key"]
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="REQUIRE_API_KEY is true but TATTOO_SERVICE_KEY is not set",
        )
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
