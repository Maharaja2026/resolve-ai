"""Start and inspect ResolveAI agent runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException

from app.agent.graph import get_agent_graph
from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository


class AgentRunner:
    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def start_run(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        customer = OrderRepository().get_customer_by_user_id(user_id)
        run_id = str(uuid4())
        created = (
            self.client.table("resolveai_agent_runs")
            .insert(
                {
                    "id": run_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "input_message": message,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .execute()
        )
        if not created.data:
            raise HTTPException(status_code=500, detail="Failed to create agent run")

        self.client.table("resolveai_messages").insert(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "user",
                "content": message,
                "agent_run_id": run_id,
            }
        ).execute()

        initial_state = {
            "run_id": run_id,
            "conversation_id": conversation_id,
            "authenticated_user_id": user_id,
            "authenticated_role": role,
            "customer_id": customer["id"] if customer else None,
            "current_request": message,
            "conversation_context": history or [],
            "tool_results": [],
            "step_count": 0,
            "tool_call_count": 0,
            "execution_status": "running",
            "metadata": {},
        }
        graph = get_agent_graph()
        config = {"configurable": {"thread_id": run_id}}
        try:
            result = graph.invoke(initial_state, config=config)
        except Exception as exc:  # noqa: BLE001
            self.client.table("resolveai_agent_runs").update(
                {
                    "status": "failed",
                    "error_message": str(exc)[:1000],
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", run_id).execute()
            raise

        final_response = result.get("final_response")
        status = result.get("execution_status") or "completed"
        if status == "waiting_for_approval":
            db_status = "waiting_for_approval"
        elif status in {"failed"}:
            db_status = "failed"
        elif status == "escalated":
            db_status = "completed"
        else:
            db_status = "completed" if final_response else "running"

        # If interrupted, LangGraph may leave run waiting.
        snapshot = graph.get_state(config)
        if snapshot and snapshot.next:
            db_status = "waiting_for_approval"
            if not final_response:
                final_response = "I've submitted your request for support approval. You'll be notified once it's reviewed."

        self.client.table("resolveai_agent_runs").update(
            {
                "status": db_status,
                "intent": result.get("detected_intent"),
                "selected_provider": result.get("provider"),
                "selected_model": result.get("model"),
                "total_steps": result.get("step_count") or 0,
                "total_tool_calls": result.get("tool_call_count") or 0,
                "final_response": final_response,
                "completed_at": datetime.now(timezone.utc).isoformat() if db_status in {"completed", "failed"} else None,
            }
        ).eq("id", run_id).execute()

        if final_response:
            self.client.table("resolveai_messages").insert(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": final_response,
                    "agent_run_id": run_id,
                    "metadata": {
                        "provider": result.get("provider"),
                        "model": result.get("model"),
                        "intent": result.get("detected_intent"),
                    },
                }
            ).execute()

        self.client.table("resolveai_conversations").update(
            {"title": message[:80], "updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", conversation_id).execute()

        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Dict[str, Any]:
        response = self.client.table("resolveai_agent_runs").select("*").eq("id", run_id).limit(1).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Agent run not found")
        return response.data[0]

    def list_events(self, run_id: str) -> List[Dict[str, Any]]:
        response = (
            self.client.table("resolveai_agent_events")
            .select("*")
            .eq("agent_run_id", run_id)
            .order("sequence_number")
            .execute()
        )
        return response.data or []
