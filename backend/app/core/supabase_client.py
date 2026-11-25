"""Supabase service-role client for ResolveAI backend only."""

from __future__ import annotations

from functools import lru_cache

import httpx
from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase is not configured for ResolveAI")
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    # PostgREST defaults to HTTP/2; concurrent agent + UI traffic can trigger
    # "Server disconnected". Prefer HTTP/1.1 for stability in local demos.
    try:
        postgrest = client.postgrest
        old = postgrest.session
        postgrest.session = httpx.Client(
            base_url=str(old.base_url),
            headers=dict(old.headers),
            timeout=old.timeout,
            verify=old.verify,
            follow_redirects=True,
            http2=False,
        )
        try:
            old.close()
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
    return client


def reset_supabase_client() -> None:
    get_supabase_client.cache_clear()
