from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.security import CurrentUser, StaffUser
from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository

router = APIRouter()


class AssignBody(BaseModel):
    agent_user_id: str


class ResolveBody(BaseModel):
    note: str = Field(default="", max_length=2000)


@router.get("")
def list_tickets(user: CurrentUser):
    client = get_supabase_client()
    if user.is_staff:
        response = client.table("resolveai_support_tickets").select("*").order("created_at", desc=True).execute()
        return response.data or []
    customer = OrderRepository().get_customer_by_user_id(user.user_id)
    if not customer:
        return []
    response = (
        client.table("resolveai_support_tickets")
        .select("*")
        .eq("customer_id", customer["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, user: CurrentUser):
    client = get_supabase_client()
    response = client.table("resolveai_support_tickets").select("*").eq("id", ticket_id).limit(1).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = response.data[0]
    if user.is_staff:
        return ticket
    customer = OrderRepository().get_customer_by_user_id(user.user_id)
    if not customer or str(ticket.get("customer_id")) != str(customer["id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    return ticket


@router.post("/{ticket_id}/assign")
def assign_ticket(ticket_id: str, payload: AssignBody, user: StaffUser):
    client = get_supabase_client()
    updated = (
        client.table("resolveai_support_tickets")
        .update({"assigned_agent_id": payload.agent_user_id, "status": "in_progress"})
        .eq("id", ticket_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated.data[0]


@router.post("/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, payload: ResolveBody, user: StaffUser):
    from datetime import datetime, timezone

    client = get_supabase_client()
    updated = (
        client.table("resolveai_support_tickets")
        .update(
            {
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", ticket_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated.data[0]


@router.post("/{ticket_id}/escalate")
def escalate_ticket(ticket_id: str, user: StaffUser):
    client = get_supabase_client()
    updated = (
        client.table("resolveai_support_tickets")
        .update({"status": "escalated", "priority": "high"})
        .eq("id", ticket_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated.data[0]
