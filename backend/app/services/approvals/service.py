"""Approval review and approved action execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository
from app.services.orders.eligibility import (
    calculate_refund_amount,
    check_address_change_eligibility,
    check_cancellation_eligibility,
    check_return_eligibility,
)


class ApprovalService:
    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def get(self, approval_id: str) -> Dict[str, Any]:
        response = (
            self.client.table("resolveai_approval_requests")
            .select("*")
            .eq("id", approval_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Approval request not found")
        return response.data[0]

    def list_pending(self) -> list:
        response = (
            self.client.table("resolveai_approval_requests")
            .select("*")
            .eq("status", "pending")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def _audit(self, *, actor_user_id: str, actor_role: str, action: str, entity_id: str, old: dict, new: dict, agent_run_id=None):
        self.client.table("resolveai_audit_logs").insert(
            {
                "actor_user_id": actor_user_id,
                "actor_role": actor_role,
                "action": action,
                "entity_type": "approval_request",
                "entity_id": entity_id,
                "old_values": old,
                "new_values": new,
                "agent_run_id": agent_run_id,
            }
        ).execute()

    def _execute_approved_action(self, approval: Dict[str, Any]) -> Dict[str, Any]:
        payload = approval.get("action_payload") or {}
        action = approval.get("requested_action")
        repo = OrderRepository()
        order_ref = payload.get("order_reference")
        order = repo.get_order_by_reference(order_ref)
        if not order or str(order["id"]) != str(approval.get("order_id")):
            raise HTTPException(status_code=400, detail="Order mismatch for approval payload")

        if action == "submit_refund":
            calc = calculate_refund_amount(order, reason=payload.get("refund_reason") or "")
            if not calc["eligible"]:
                raise HTTPException(status_code=400, detail="Refund no longer eligible")
            amount = float(payload.get("requested_amount") or 0)
            if amount > float(calc["estimated_amount"]) + 0.01:
                raise HTTPException(status_code=400, detail="Refund amount exceeds eligible estimate")
            txn = f"SIM-REF-{uuid4().hex[:10].upper()}"
            refund = (
                self.client.table("resolveai_refund_records")
                .insert(
                    {
                        "order_id": order["id"],
                        "customer_id": order["customer_id"],
                        "approval_request_id": approval["id"],
                        "amount": amount,
                        "currency": payload.get("currency") or order.get("currency") or "USD",
                        "refund_reason": payload.get("refund_reason") or "",
                        "status": "simulated_completed",
                        "simulated_transaction_reference": txn,
                    }
                )
                .execute()
            )
            payment_status = "refunded" if amount >= float(order["total_amount"]) else "partially_refunded"
            repo.update_order(order["id"], {"payment_status": payment_status})
            return {"type": "refund", "reference": txn, "record": (refund.data or [None])[0]}

        if action == "cancel_order":
            eligibility = check_cancellation_eligibility(order)
            if not eligibility["eligible"]:
                raise HTTPException(status_code=400, detail="Cancellation no longer eligible")
            updated = repo.update_order(order["id"], {"order_status": "cancelled"})
            return {"type": "cancellation", "reference": order["order_reference"], "order": updated}

        if action == "create_return":
            eligibility = check_return_eligibility(order, reason=payload.get("reason") or "")
            if not eligibility["eligible"]:
                raise HTTPException(status_code=400, detail="Return no longer eligible")
            updated = repo.update_order(order["id"], {"order_status": "return_requested"})
            return {"type": "return", "reference": order["order_reference"], "order": updated}

        if action == "update_shipping_address":
            eligibility = check_address_change_eligibility(order)
            if not eligibility["eligible"]:
                raise HTTPException(status_code=400, detail="Address change no longer eligible")
            updated = repo.update_order(order["id"], {"shipping_address": payload.get("new_address") or {}})
            return {"type": "address_change", "reference": order["order_reference"], "order": updated}

        raise HTTPException(status_code=400, detail=f"Unsupported approved action: {action}")

    def approve(self, approval_id: str, *, reviewer_user_id: str, reviewer_role: str, comment: str = "") -> Dict[str, Any]:
        approval = self.get(approval_id)
        if approval["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Approval is already {approval['status']}")
        expires_at = approval.get("expires_at")
        if expires_at:
            try:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp:
                    self.client.table("resolveai_approval_requests").update({"status": "expired"}).eq("id", approval_id).execute()
                    raise HTTPException(status_code=409, detail="Approval request has expired")
            except HTTPException:
                raise
            except Exception:
                pass

        execution = self._execute_approved_action(approval)
        updated = (
            self.client.table("resolveai_approval_requests")
            .update(
                {
                    "status": "approved",
                    "reviewed_by": reviewer_user_id,
                    "review_comment": comment,
                    "approved_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", approval_id)
            .eq("status", "pending")
            .execute()
        )
        if not updated.data:
            raise HTTPException(status_code=409, detail="Approval was already processed")

        self._audit(
            actor_user_id=reviewer_user_id,
            actor_role=reviewer_role,
            action="approve",
            entity_id=approval_id,
            old={"status": "pending"},
            new={"status": "approved", "execution": execution},
            agent_run_id=approval.get("agent_run_id"),
        )

        # Resume LangGraph if possible
        resume_payload = {
            "status": "approved",
            "approval_id": approval_id,
            "review_comment": comment,
            "execution": execution,
        }
        self._resume_agent(approval.get("agent_run_id"), resume_payload)
        return {"approval": updated.data[0], "execution": execution}

    def reject(self, approval_id: str, *, reviewer_user_id: str, reviewer_role: str, comment: str = "") -> Dict[str, Any]:
        approval = self.get(approval_id)
        if approval["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Approval is already {approval['status']}")
        updated = (
            self.client.table("resolveai_approval_requests")
            .update(
                {
                    "status": "rejected",
                    "reviewed_by": reviewer_user_id,
                    "review_comment": comment or "Rejected by support",
                    "rejected_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", approval_id)
            .eq("status", "pending")
            .execute()
        )
        if not updated.data:
            raise HTTPException(status_code=409, detail="Approval was already processed")
        self._audit(
            actor_user_id=reviewer_user_id,
            actor_role=reviewer_role,
            action="reject",
            entity_id=approval_id,
            old={"status": "pending"},
            new={"status": "rejected"},
            agent_run_id=approval.get("agent_run_id"),
        )
        resume_payload = {
            "status": "rejected",
            "approval_id": approval_id,
            "review_comment": comment or "Rejected by support",
        }
        self._resume_agent(approval.get("agent_run_id"), resume_payload)
        return {"approval": updated.data[0], "execution": None}

    def _resume_agent(self, agent_run_id: str | None, payload: Dict[str, Any]) -> None:
        if not agent_run_id:
            return
        try:
            from langgraph.types import Command

            from app.agent.graph import get_agent_graph

            graph = get_agent_graph()
            config = {"configurable": {"thread_id": str(agent_run_id)}}
            graph.invoke(Command(resume=payload), config=config)
        except Exception as exc:  # noqa: BLE001
            # Application state still records approval outcome even if checkpoint resume fails.
            from app.core.logging import logger

            logger.warning("Agent resume failed for run %s: %s", agent_run_id, exc)
            self.client.table("resolveai_agent_runs").update(
                {
                    "status": "completed",
                    "final_response": (
                        "Your request was approved and executed."
                        if payload.get("status") == "approved"
                        else f"Your request was rejected. {payload.get('review_comment') or ''}"
                    ),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"resume_fallback": True, "approval_result": payload},
                }
            ).eq("id", agent_run_id).execute()
