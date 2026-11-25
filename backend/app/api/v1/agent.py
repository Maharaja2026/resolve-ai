from fastapi import APIRouter, HTTPException, Query

from app.core.security import CurrentUser, StaffUser
from app.core.supabase_client import get_supabase_client
from app.services.agent_runner import AgentRunner

router = APIRouter()


@router.get("/agent-runs")
def list_agent_runs(
    user: StaffUser,
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """Staff-only recent agent run history for the admin execution dashboard."""
    query = (
        get_supabase_client()
        .table("resolveai_agent_runs")
        .select(
            "id,conversation_id,user_id,input_message,status,intent,"
            "selected_provider,selected_model,total_steps,total_tool_calls,"
            "started_at,completed_at,error_message"
        )
        .order("started_at", desc=True)
        .limit(limit)
    )
    if status_filter:
        query = query.eq("status", status_filter)
    response = query.execute()
    items = response.data or []
    return {"items": items, "total": len(items)}


@router.get("/agent-runs/{run_id}")
def get_agent_run(run_id: str, user: CurrentUser):
    run = AgentRunner().get_run(run_id)
    if run["user_id"] != user.user_id and not user.is_staff:
        raise HTTPException(status_code=403, detail="Forbidden")
    return run


@router.get("/agent-runs/{run_id}/events")
def get_agent_events(run_id: str, user: CurrentUser):
    run = AgentRunner().get_run(run_id)
    if run["user_id"] != user.user_id and not user.is_staff:
        raise HTTPException(status_code=403, detail="Forbidden")
    return AgentRunner().list_events(run_id)


@router.get("/agent-runs/{run_id}/trace")
def get_agent_trace(run_id: str, user: StaffUser):
    run = AgentRunner().get_run(run_id)
    events = AgentRunner().list_events(run_id)
    tools = (
        get_supabase_client()
        .table("resolveai_tool_executions")
        .select("*")
        .eq("agent_run_id", run_id)
        .order("started_at")
        .execute()
        .data
        or []
    )
    return {"run": run, "events": events, "tool_executions": tools}
