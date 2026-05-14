"""
In-process rate limiting (per deployment instance).

Scale note: multiple replicas each enforce limits independently — effective limit ≈ N × limit.
For strict global limits use Redis + shared counter (e.g. Upstash) or enforce at API gateway / CDN.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
