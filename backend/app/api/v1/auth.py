from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser
from app.services.llm.orchestrator import get_llm_orchestrator

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "supabase_configured": settings.supabase_configured,
        "demo_disclaimer": "DEMO ENVIRONMENT — All order, refund, cancellation, and shipping operations are simulated.",
    }


@router.get("/system/llm-status")
def llm_status(user: CurrentUser, settings: Settings = Depends(get_settings)):
    return {
        "primary_provider": settings.llm_primary_provider,
        "fallback_provider": settings.llm_fallback_provider,
        "providers": get_llm_orchestrator(settings).status(),
        "embedding": {
            "model": settings.embedding_model,
            "dimension": settings.embedding_dimension,
        },
    }


@router.get("/me")
def me(user: CurrentUser):
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "profile": user.profile,
        "demo_disclaimer": "DEMO ENVIRONMENT — All order, refund, cancellation, and shipping operations are simulated.",
    }


@router.get("/me/permissions")
def permissions(user: CurrentUser):
    return {
        "role": user.role,
        "can_approve": user.is_staff,
        "can_admin": user.is_admin,
        "can_view_all_tickets": user.is_staff,
    }
