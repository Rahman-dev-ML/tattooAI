"""
In-process rate limiting (per deployment instance).

Scale note: multiple replicas each enforce limits independently — effective limit ≈ N × limit.
For strict global limits use Redis + shared counter (e.g. Upstash) or enforce at API gateway / CDN.
"""
from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter


def _client_ip_key(request: Request) -> str:
    """
    Prefer the first X-Forwarded-For hop when present, then fall back to socket IP.

    Note: only trustworthy when your reverse proxy is configured correctly and
    strips/spoofs untrusted forwarded headers.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    client = request.client
    return client.host if client else "unknown"

_RATE_LIMIT_STORAGE_URI = os.environ.get("RATE_LIMIT_STORAGE_URL", "").strip() or None
_RATE_LIMIT_STRATEGY = os.environ.get("RATE_LIMIT_STRATEGY", "fixed-window").strip() or "fixed-window"

limiter = Limiter(
    key_func=_client_ip_key,
    storage_uri=_RATE_LIMIT_STORAGE_URI,
    strategy=_RATE_LIMIT_STRATEGY,
)
