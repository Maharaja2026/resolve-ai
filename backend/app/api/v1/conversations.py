from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.security import CurrentUser
from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository
from app.services.agent_runner import AgentRunner

router = APIRouter()


class ConversationCreate(BaseModel):
    title: Optional[str] = "New support chat"


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


@router.post("")
def create_conversation(payload: ConversationCreate, user: CurrentUser):
    client = get_supabase_client()
    customer = OrderRepository().get_customer_by_user_id(user.user_id)
    row = {
        "user_id": user.user_id,
        "customer_id": customer["id"] if customer else None,
        "title": payload.title or "New support chat",
        "status": "open",
    }
    created = client.table("resolveai_conversations").insert(row).execute()
    if not created.data:
        raise HTTPException(status_code=500, detail="Failed to create conversation")
    return created.data[0]


@router.get("")
def list_conversations(user: CurrentUser):
    client = get_supabase_client()
    response = (
        client.table("resolveai_conversations")
        .select("*")
        .eq("user_id", user.user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data or []


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: CurrentUser):
    client = get_supabase_client()
    response = (
        client.table("resolveai_conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return response.data[0]


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, user: CurrentUser):
    get_conversation(conversation_id, user)
    client = get_supabase_client()
    response = (
        client.table("resolveai_messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return response.data or []


@router.post("/{conversation_id}/messages")
def send_message(conversation_id: str, payload: MessageCreate, user: CurrentUser):
    conversation = get_conversation(conversation_id, user)
    client = get_supabase_client()
    history_rows = (
        client.table("resolveai_messages")
        .select("role,content")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
        .data
        or []
    )
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows[-8:]]
    runner = AgentRunner()
    run = runner.start_run(
        conversation_id=conversation["id"],
        user_id=user.user_id,
        role=user.role,
        message=payload.content,
        history=history,
    )
    events = runner.list_events(run["id"])
    return {"run": run, "events": events, "assistant_message": run.get("final_response")}


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, user: CurrentUser):
    get_conversation(conversation_id, user)
    get_supabase_client().table("resolveai_conversations").delete().eq("id", conversation_id).eq("user_id", user.user_id).execute()
    return {"deleted": True}
