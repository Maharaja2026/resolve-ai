"""Authentication and role-based authorization dependencies."""

from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.supabase_client import get_supabase_client

VALID_ROLES = {"customer", "support_agent", "admin"}


class AuthenticatedUser:
    def __init__(
        self,
        user_id: str,
        email: Optional[str] = None,
        role: str = "customer",
        profile: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role if role in VALID_ROLES else "customer"
        self.profile = profile or {}

    @property
    def is_staff(self) -> bool:
        return self.role in {"support_agent", "admin"}

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _load_profile(user_id: str) -> Dict[str, Any]:
    client = get_supabase_client()
    response = (
        client.table("resolveai_user_profiles")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    # First login: create a customer profile. Never trust client-supplied roles.
    created = (
        client.table("resolveai_user_profiles")
        .insert(
            {
                "user_id": user_id,
                "full_name": "Customer",
                "role": "customer",
                "is_active": True,
            }
        )
        .execute()
    )
    if not created.data:
        raise HTTPException(status_code=500, detail="Failed to create user profile")
    return created.data[0]


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.supabase_configured:
        raise HTTPException(status_code=503, detail="Authentication service is not configured")

    client = get_supabase_client()
    try:
        response = client.auth.get_user(token.strip())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = getattr(response, "user", None)
    if user is None or not getattr(user, "id", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile = _load_profile(str(user.id))
    if not profile.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")

    return AuthenticatedUser(
        user_id=str(user.id),
        email=getattr(user, "email", None),
        role=str(profile.get("role") or "customer"),
        profile=profile,
    )


def require_roles(*roles: str):
    async def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
StaffUser = Annotated[AuthenticatedUser, Depends(require_roles("support_agent", "admin"))]
AdminUser = Annotated[AuthenticatedUser, Depends(require_roles("admin"))]
