"""Simple in-memory rate limiter for a single free-tier instance."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.time()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            bucket.append(now)


rate_limiter = InMemoryRateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    host = request.client.host if request.client else "unknown"
    auth = request.headers.get("authorization", "")
    key = f"{host}:{auth[-12:] if auth else 'anon'}"
    rate_limiter.check(key, settings.rate_limit_requests, settings.rate_limit_window_seconds)
