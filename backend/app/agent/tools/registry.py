"""Allowlisted ResolveAI tools with schema validation and permission levels."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository
from app.services.orders.eligibility import (
    calculate_refund_amount,
    check_address_change_eligibility,
    check_cancellation_eligibility,
    check_return_eligibility,
)
from app.services.retrieval.policy_search import search_policies


class ToolSpec(BaseModel):
    name: str
    description: str
    permission_level: str  # customer | staff
    classification: str  # read | write | escalate
    input_schema: type[BaseModel]
    execute: Callable[..., Dict[str, Any]]


class LookupOrderInput(BaseModel):
    order_reference: str = Field(..., min_length=3, max_length=64)


class DeliveryStatusInput(BaseModel):
    order_reference: str = Field(..., min_length=3, max_length=64)


class SearchPolicyInput(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    category: Optional[str] = None


class ReturnEligibilityInput(BaseModel):
    order_reference: str
    reason: str = ""


class CalculateRefundInput(BaseModel):
    order_reference: str
    reason: str = ""


class CreateReturnInput(BaseModel):
    order_reference: str
    reason: str
    customer_confirmation: bool = False


class SubmitRefundInput(BaseModel):
    order_reference: str
    refund_reason: str
    requested_amount: float = Field(..., ge=0)
    customer_confirmation: bool = False


class CancelOrderInput(BaseModel):
    order_reference: str
    cancellation_reason: str
    customer_confirmation: bool = False


class UpdateAddressInput(BaseModel):
    order_reference: str
    new_address: Dict[str, Any]
    customer_confirmation: bool = False


class EscalateInput(BaseModel):
    conversation_id: str
    issue_summary: str
    escalation_reason: str
    priority: str = "medium"


def _ctx_customer_id(context: Dict[str, Any]) -> str:
    customer_id = context.get("customer_id")
    if not customer_id:
        raise ValueError("Authenticated customer context is required")
    return str(customer_id)


def _create_approval(
    *,
    context: Dict[str, Any],
    order: Dict[str, Any],
    approval_type: str,
    requested_action: str,
    action_payload: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    settings = get_settings()
    client = get_supabase_client()
    # Prevent duplicate pending approvals for same order/action
    existing = (
        client.table("resolveai_approval_requests")
        .select("*")
        .eq("order_id", order["id"])
        .eq("requested_action", requested_action)
        .eq("status", "pending")
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"created": False, "approval": existing.data[0], "duplicate": True}

    expires = datetime.now(timezone.utc) + timedelta(hours=settings.approval_expiry_hours)
    row = {
        "agent_run_id": context.get("run_id"),
        "customer_id": order["customer_id"],
        "order_id": order["id"],
        "requested_by": context["authenticated_user_id"],
        "approval_type": approval_type,
        "requested_action": requested_action,
        "action_payload": action_payload,
        "reason": reason,
        "status": "pending",
        "expires_at": expires.isoformat(),
    }
    created = client.table("resolveai_approval_requests").insert(row).execute()
    if not created.data:
        raise RuntimeError("Failed to create approval request")
    return {"created": True, "approval": created.data[0], "duplicate": False}


def tool_lookup_order(args: LookupOrderInput, context: Dict[str, Any]) -> Dict[str, Any]:
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    return {"order": order}


def tool_get_delivery_status(args: DeliveryStatusInput, context: Dict[str, Any]) -> Dict[str, Any]:
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    events = repo.list_events(order["id"])
    return {"order_reference": order["order_reference"], "order_status": order["order_status"], "events": events}


def tool_search_policy(args: SearchPolicyInput, context: Dict[str, Any]) -> Dict[str, Any]:
    results = search_policies(query=args.query, category=args.category)
    return {"policies": results}


def tool_check_return_eligibility(args: ReturnEligibilityInput, context: Dict[str, Any]) -> Dict[str, Any]:
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    result = check_return_eligibility(order, reason=args.reason)
    return {"order_reference": args.order_reference, **result}


def tool_calculate_refund(args: CalculateRefundInput, context: Dict[str, Any]) -> Dict[str, Any]:
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    result = calculate_refund_amount(order, reason=args.reason)
    return {"order_reference": args.order_reference, **result}


def tool_create_return_request(args: CreateReturnInput, context: Dict[str, Any]) -> Dict[str, Any]:
    if not args.customer_confirmation:
        return {"requires_confirmation": True, "message": "Customer confirmation is required before creating a return request."}
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    eligibility = check_return_eligibility(order, reason=args.reason)
    if not eligibility["eligible"]:
        return {"created": False, "eligibility": eligibility}
    approval = _create_approval(
        context=context,
        order=order,
        approval_type="return",
        requested_action="create_return",
        action_payload={"order_reference": args.order_reference, "reason": args.reason},
        reason=args.reason,
    )
    return {"eligibility": eligibility, **approval, "waiting_for_approval": True}


def tool_submit_refund_request(args: SubmitRefundInput, context: Dict[str, Any]) -> Dict[str, Any]:
    if not args.customer_confirmation:
        return {"requires_confirmation": True, "message": "Customer confirmation is required before submitting a refund request."}
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    calc = calculate_refund_amount(order, reason=args.refund_reason)
    if not calc["eligible"]:
        return {"created": False, "calculation": calc}
    if args.requested_amount > float(calc["estimated_amount"]) + 0.01:
        return {
            "created": False,
            "error": "requested_amount_exceeds_eligible",
            "calculation": calc,
        }
    approval = _create_approval(
        context=context,
        order=order,
        approval_type="refund",
        requested_action="submit_refund",
        action_payload={
            "order_reference": args.order_reference,
            "refund_reason": args.refund_reason,
            "requested_amount": args.requested_amount,
            "currency": calc["currency"],
        },
        reason=args.refund_reason,
    )
    return {"calculation": calc, **approval, "waiting_for_approval": True}


def tool_cancel_order(args: CancelOrderInput, context: Dict[str, Any]) -> Dict[str, Any]:
    if not args.customer_confirmation:
        return {"requires_confirmation": True, "message": "Customer confirmation is required before cancellation."}
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    eligibility = check_cancellation_eligibility(order)
    if not eligibility["eligible"]:
        return {"created": False, "eligibility": eligibility}
    approval = _create_approval(
        context=context,
        order=order,
        approval_type="cancellation",
        requested_action="cancel_order",
        action_payload={
            "order_reference": args.order_reference,
            "cancellation_reason": args.cancellation_reason,
        },
        reason=args.cancellation_reason,
    )
    return {"eligibility": eligibility, **approval, "waiting_for_approval": True}


def tool_update_shipping_address(args: UpdateAddressInput, context: Dict[str, Any]) -> Dict[str, Any]:
    if not args.customer_confirmation:
        return {"requires_confirmation": True, "message": "Customer confirmation is required before address change."}
    repo = OrderRepository()
    order = repo.get_owned_order(args.order_reference, _ctx_customer_id(context))
    eligibility = check_address_change_eligibility(order)
    if not eligibility["eligible"]:
        return {"created": False, "eligibility": eligibility}
    approval = _create_approval(
        context=context,
        order=order,
        approval_type="address_change",
        requested_action="update_shipping_address",
        action_payload={
            "order_reference": args.order_reference,
            "new_address": args.new_address,
        },
        reason="Customer requested shipping address update",
    )
    return {"eligibility": eligibility, **approval, "waiting_for_approval": True}


def tool_escalate_to_human(args: EscalateInput, context: Dict[str, Any]) -> Dict[str, Any]:
    client = get_supabase_client()
    ticket_ref = f"TCK-{uuid4().hex[:8].upper()}"
    row = {
        "ticket_reference": ticket_ref,
        "customer_id": context.get("customer_id"),
        "conversation_id": args.conversation_id,
        "category": "escalation",
        "priority": args.priority if args.priority in {"low", "medium", "high", "urgent"} else "medium",
        "status": "escalated",
        "subject": args.issue_summary[:200],
        "sentiment": context.get("sentiment"),
    }
    created = client.table("resolveai_support_tickets").insert(row).execute()
    return {"ticket": created.data[0] if created.data else row, "escalated": True}


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "lookup_order": ToolSpec(
        name="lookup_order",
        description="Retrieve an order owned by the authenticated customer.",
        permission_level="customer",
        classification="read",
        input_schema=LookupOrderInput,
        execute=tool_lookup_order,
    ),
    "get_delivery_status": ToolSpec(
        name="get_delivery_status",
        description="Retrieve delivery/order events for an owned order.",
        permission_level="customer",
        classification="read",
        input_schema=DeliveryStatusInput,
        execute=tool_get_delivery_status,
    ),
    "search_policy": ToolSpec(
        name="search_policy",
        description="Search company policy documents with hybrid retrieval.",
        permission_level="customer",
        classification="read",
        input_schema=SearchPolicyInput,
        execute=tool_search_policy,
    ),
    "check_return_eligibility": ToolSpec(
        name="check_return_eligibility",
        description="Deterministically check whether a return is eligible.",
        permission_level="customer",
        classification="read",
        input_schema=ReturnEligibilityInput,
        execute=tool_check_return_eligibility,
    ),
    "calculate_refund": ToolSpec(
        name="calculate_refund",
        description="Estimate eligible refund amount using backend business rules. Does not create a refund.",
        permission_level="customer",
        classification="read",
        input_schema=CalculateRefundInput,
        execute=tool_calculate_refund,
    ),
    "create_return_request": ToolSpec(
        name="create_return_request",
        description="Create a pending return approval request after customer confirmation.",
        permission_level="customer",
        classification="write",
        input_schema=CreateReturnInput,
        execute=tool_create_return_request,
    ),
    "submit_refund_request": ToolSpec(
        name="submit_refund_request",
        description="Create a pending refund approval request after customer confirmation.",
        permission_level="customer",
        classification="write",
        input_schema=SubmitRefundInput,
        execute=tool_submit_refund_request,
    ),
    "cancel_order": ToolSpec(
        name="cancel_order",
        description="Create a pending cancellation approval request.",
        permission_level="customer",
        classification="write",
        input_schema=CancelOrderInput,
        execute=tool_cancel_order,
    ),
    "update_shipping_address": ToolSpec(
        name="update_shipping_address",
        description="Create a pending shipping address change approval request.",
        permission_level="customer",
        classification="write",
        input_schema=UpdateAddressInput,
        execute=tool_update_shipping_address,
    ),
    "escalate_to_human": ToolSpec(
        name="escalate_to_human",
        description="Escalate the conversation to a human support agent.",
        permission_level="customer",
        classification="escalate",
        input_schema=EscalateInput,
        execute=tool_escalate_to_human,
    ),
}


def list_tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "classification": spec.classification,
            "parameters": spec.input_schema.model_json_schema(),
        }
        for spec in TOOL_REGISTRY.values()
    ]


def execute_tool(tool_name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None:
        raise ValueError(f"Unregistered tool: {tool_name}")
    validated = spec.input_schema.model_validate(arguments)
    return spec.execute(validated, context)
