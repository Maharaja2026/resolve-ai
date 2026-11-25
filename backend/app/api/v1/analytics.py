from fastapi import APIRouter

from app.core.security import StaffUser
from app.core.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/overview")
def overview(user: StaffUser):
    client = get_supabase_client()
    tickets = client.table("resolveai_support_tickets").select("id,status").execute().data or []
    runs = client.table("resolveai_agent_runs").select("id,status").execute().data or []
    approvals = client.table("resolveai_approval_requests").select("id,status").execute().data or []
    return {
        "total_tickets": len(tickets),
        "open_tickets": sum(1 for t in tickets if t.get("status") in {"open", "in_progress", "escalated"}),
        "resolved_tickets": sum(1 for t in tickets if t.get("status") == "resolved"),
        "total_agent_runs": len(runs),
        "waiting_approvals": sum(1 for a in approvals if a.get("status") == "pending"),
        "completed_runs": sum(1 for r in runs if r.get("status") == "completed"),
    }


@router.get("/agent-performance")
def agent_performance(user: StaffUser):
    client = get_supabase_client()
    runs = client.table("resolveai_agent_runs").select("selected_provider,status,total_tool_calls,total_steps").execute().data or []
    by_provider = {}
    for run in runs:
        provider = run.get("selected_provider") or "unknown"
        by_provider.setdefault(provider, {"runs": 0, "tool_calls": 0, "steps": 0})
        by_provider[provider]["runs"] += 1
        by_provider[provider]["tool_calls"] += int(run.get("total_tool_calls") or 0)
        by_provider[provider]["steps"] += int(run.get("total_steps") or 0)
    return {"by_provider": by_provider, "total_runs": len(runs)}


@router.get("/tool-usage")
def tool_usage(user: StaffUser):
    client = get_supabase_client()
    tools = client.table("resolveai_tool_executions").select("tool_name,status").execute().data or []
    counts = {}
    for row in tools:
        name = row.get("tool_name") or "unknown"
        counts.setdefault(name, {"count": 0, "failed": 0})
        counts[name]["count"] += 1
        if row.get("status") == "failed":
            counts[name]["failed"] += 1
    return {"tools": counts, "total": len(tools)}


@router.get("/approval-stats")
def approval_stats(user: StaffUser):
    client = get_supabase_client()
    rows = client.table("resolveai_approval_requests").select("status").execute().data or []
    stats = {"pending": 0, "approved": 0, "rejected": 0, "expired": 0, "cancelled": 0}
    for row in rows:
        status = row.get("status")
        if status in stats:
            stats[status] += 1
    stats["total"] = len(rows)
    return stats
