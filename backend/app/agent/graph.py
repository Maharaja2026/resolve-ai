"""LangGraph StateGraph for ResolveAI support workflows."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Literal
from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agent.checkpointer import build_checkpointer
from app.agent.prompts.system import PLAN_PROMPT, UNDERSTAND_PROMPT
from app.agent.state import AgentState
from app.agent.tools.registry import TOOL_REGISTRY, execute_tool, list_tool_definitions
from app.core.config import get_settings
from app.core.logging import logger
from app.core.supabase_client import get_supabase_client
from app.repositories.orders import OrderRepository
from app.services.llm.base import LLMMessage, LLMProviderError
from app.services.llm.orchestrator import get_llm_orchestrator
from app.services.retrieval.policy_search import search_policies

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = JSON_RE.search(text)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _record_event(state: AgentState, event_type: str, event_name: str, summary: str, status: str = "completed", **payload):
    try:
        client = get_supabase_client()
        seq = int(state.get("step_count") or 0) + 1
        client.table("resolveai_agent_events").insert(
            {
                "agent_run_id": state["run_id"],
                "event_type": event_type,
                "event_name": event_name,
                "summary": summary,
                "safe_input": payload.get("safe_input") or {},
                "safe_output": payload.get("safe_output") or {},
                "status": status,
                "sequence_number": seq,
            }
        ).execute()
        state["step_count"] = seq
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist agent event: %s", exc)


def understand_request(state: AgentState) -> AgentState:
    llm = get_llm_orchestrator()
    messages = [
        LLMMessage(role="system", content=UNDERSTAND_PROMPT),
        LLMMessage(role="user", content=state["current_request"]),
    ]
    try:
        decision = llm.decide(messages, tools=[], temperature=0.0)
        parsed = _parse_json(decision.content or "")
        state["provider"] = decision.provider
        state["model"] = decision.model
    except LLMProviderError as exc:
        # Deterministic heuristic fallback when LLM unavailable.
        text = state["current_request"].lower()
        parsed = {
            "intent": "general_question",
            "order_reference": None,
            "priority": "medium",
            "sentiment": "neutral",
        }
        if "refund" in text:
            parsed["intent"] = "refund_request"
        elif "cancel" in text:
            parsed["intent"] = "cancellation_request"
        elif "address" in text:
            parsed["intent"] = "address_change"
        elif "where" in text or "track" in text or "status" in text:
            parsed["intent"] = "track_order"
        elif "human" in text or "agent" in text:
            parsed["intent"] = "human_escalation"
        match = re.search(r"ORD-\d+", state["current_request"], re.IGNORECASE)
        if match:
            parsed["order_reference"] = match.group(0).upper()
        state["error"] = str(exc)

    state["detected_intent"] = parsed.get("intent") or "general_question"
    state["extracted_entities"] = {
        "order_reference": parsed.get("order_reference"),
        "requested_action": parsed.get("requested_action"),
    }
    state["priority"] = parsed.get("priority") or "medium"
    state["sentiment"] = parsed.get("sentiment") or "neutral"
    if parsed.get("missing_information") and parsed.get("clarification_question"):
        state["needs_clarification"] = True
        state["clarification_question"] = parsed.get("clarification_question")
        state["final_response"] = parsed.get("clarification_question")
        state["execution_status"] = "needs_clarification"
    else:
        state["needs_clarification"] = False
    _record_event(
        state,
        "intent_detected",
        "understand_request",
        f"Detected intent={state['detected_intent']}",
        safe_output={"intent": state["detected_intent"], "entities": state["extracted_entities"]},
    )
    return state


def load_customer_context(state: AgentState) -> AgentState:
    if state.get("needs_clarification"):
        return state
    repo = OrderRepository()
    customer = repo.get_customer_by_user_id(state["authenticated_user_id"])
    if not customer:
        state["error"] = "No customer profile linked to this account"
        state["final_response"] = (
            "I could not find a customer profile linked to your account. "
            "Please contact support to link your demo customer record."
        )
        state["execution_status"] = "failed"
        return state
    state["customer_id"] = customer["id"]
    order_ref = (state.get("extracted_entities") or {}).get("order_reference")
    if order_ref:
        try:
            order = repo.get_owned_order(order_ref, customer["id"])
            state["order_context"] = {"order": order, "events": repo.list_events(order["id"])}
        except Exception as exc:  # noqa: BLE001
            state["order_context"] = {"error": str(exc)}
    else:
        state["order_context"] = {"recent_orders": repo.list_orders_for_customer(customer["id"])[:5]}
    _record_event(state, "context_loaded", "load_customer_context", "Loaded authorized customer context")
    return state


def retrieve_policies(state: AgentState) -> AgentState:
    if state.get("needs_clarification") or state.get("execution_status") == "failed":
        return state
    intent = state.get("detected_intent") or "general_question"
    category_map = {
        "refund_request": "refund",
        "return_request": "return",
        "cancellation_request": "cancellation",
        "delayed_delivery": "shipping",
        "address_change": "address",
        "damaged_item": "damaged",
        "wrong_item": "wrong_item",
    }
    query = state["current_request"]
    try:
        policies = search_policies(query=query, category=category_map.get(intent))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Policy retrieval failed: %s", exc)
        policies = []
    state["retrieved_policies"] = policies
    _record_event(
        state,
        "policy_retrieved",
        "retrieve_policies",
        f"Retrieved {len(policies)} policy chunks",
        safe_output={"count": len(policies), "titles": [p.get("title") for p in policies[:3]]},
    )
    return state


def agent_decision(state: AgentState) -> AgentState:
    if state.get("needs_clarification") or state.get("final_response"):
        state["next_action"] = "respond"
        return state
    if state.get("approval_result"):
        result = state["approval_result"]
        if result.get("status") == "approved":
            state["final_response"] = (
                f"Your request was approved and executed. Reference: "
                f"{result.get('execution', {}).get('reference', 'N/A')}."
            )
        else:
            state["final_response"] = (
                f"Your request was reviewed and rejected. "
                f"Reason: {result.get('review_comment') or 'No reason provided.'}"
            )
        state["next_action"] = "respond"
        state["execution_status"] = "completed"
        return state

    settings = get_settings()
    if int(state.get("tool_call_count") or 0) >= settings.max_tool_calls:
        state["final_response"] = "I reached the tool-call limit for this request. A human specialist can continue from here."
        state["next_action"] = "escalate"
        return state
    if int(state.get("step_count") or 0) >= settings.max_agent_steps:
        state["final_response"] = "I could not complete the workflow within the step limit. Escalating to a human agent."
        state["next_action"] = "escalate"
        return state

    llm = get_llm_orchestrator()
    tools = list_tool_definitions()
    context_blob = {
        "intent": state.get("detected_intent"),
        "entities": state.get("extracted_entities"),
        "order_context": state.get("order_context"),
        "policies": state.get("retrieved_policies"),
        "tool_results": state.get("tool_results"),
        "trusted_user_id": state.get("authenticated_user_id"),
        "trusted_customer_id": state.get("customer_id"),
    }
    messages = [
        LLMMessage(role="system", content=PLAN_PROMPT),
        LLMMessage(role="user", content=f"Customer request:\n{state['current_request']}\n\nTrusted context JSON:\n{json.dumps(context_blob, default=str)[:12000]}"),
    ]
    try:
        decision = llm.decide(messages, tools=tools, temperature=0.1)
        state["provider"] = decision.provider
        state["model"] = decision.model
        if decision.tool_calls:
            call = decision.tool_calls[0]
            state["tool_calls"] = [{"name": call.name, "arguments": call.arguments}]
            state["next_action"] = "tool"
        else:
            state["final_response"] = decision.content or "I checked your request and have no further actions to take."
            state["next_action"] = "respond"
            state["execution_status"] = "completed"
    except LLMProviderError as exc:
        state["error"] = str(exc)
        state["final_response"] = "Our AI providers are temporarily unavailable. I created an escalation path for a human agent."
        state["next_action"] = "escalate"
    return state


def route_after_decision(state: AgentState) -> Literal["execute_tool", "request_approval", "escalate", "respond", "end"]:
    action = state.get("next_action")
    if action == "tool":
        calls = state.get("tool_calls") or []
        if not calls:
            return "respond"
        name = calls[0].get("name")
        spec = TOOL_REGISTRY.get(name or "")
        if spec is None:
            return "respond"
        if spec.classification == "write":
            return "request_approval_via_tool"
        if spec.classification == "escalate":
            return "escalate"
        return "execute_tool"
    if action == "escalate":
        return "escalate"
    if action == "respond":
        return "respond"
    return "end"


def execute_read_tool(state: AgentState) -> AgentState:
    call = (state.get("tool_calls") or [{}])[0]
    name = call.get("name")
    args = call.get("arguments") or {}
    context = {
        "run_id": state["run_id"],
        "authenticated_user_id": state["authenticated_user_id"],
        "customer_id": state.get("customer_id"),
        "conversation_id": state.get("conversation_id"),
        "sentiment": state.get("sentiment"),
    }
    _record_event(state, "tool_started", name, f"Starting tool {name}", safe_input={"arguments": args})
    try:
        result = execute_tool(name, args, context)
        state.setdefault("tool_results", [])
        # LangGraph Annotated add reducer expects return delta; we mutate carefully:
        state["tool_results"] = list(state.get("tool_results") or []) + [{"tool": name, "result": result}]
        state["tool_call_count"] = int(state.get("tool_call_count") or 0) + 1
        _record_event(state, "tool_completed", name, f"Completed tool {name}", safe_output={"ok": True})
        # Persist tool execution
        try:
            get_supabase_client().table("resolveai_tool_executions").insert(
                {
                    "agent_run_id": state["run_id"],
                    "conversation_id": state.get("conversation_id"),
                    "tool_name": name,
                    "tool_arguments": args,
                    "execution_result": result,
                    "status": "completed",
                    "idempotency_key": f"{state['run_id']}:{name}:{uuid4().hex[:8]}",
                }
            ).execute()
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        state["tool_results"] = list(state.get("tool_results") or []) + [{"tool": name, "error": str(exc)}]
        state["tool_call_count"] = int(state.get("tool_call_count") or 0) + 1
        _record_event(state, "error", name, f"Tool failed: {exc}", status="failed")
    state["next_action"] = "decide"
    return state


def execute_write_tool_and_maybe_interrupt(state: AgentState) -> AgentState:
    """Execute write tool (creates pending approval) then interrupt for human approval."""
    call = (state.get("tool_calls") or [{}])[0]
    name = call.get("name")
    args = call.get("arguments") or {}
    context = {
        "run_id": state["run_id"],
        "authenticated_user_id": state["authenticated_user_id"],
        "customer_id": state.get("customer_id"),
        "conversation_id": state.get("conversation_id"),
        "sentiment": state.get("sentiment"),
    }
    _record_event(state, "tool_started", name, f"Starting write tool {name}", safe_input={"arguments": args})
    try:
        result = execute_tool(name, args, context)
        state["tool_results"] = list(state.get("tool_results") or []) + [{"tool": name, "result": result}]
        state["tool_call_count"] = int(state.get("tool_call_count") or 0) + 1
        if result.get("requires_confirmation"):
            state["final_response"] = result.get("message") or "Please confirm that you want me to proceed."
            state["execution_status"] = "needs_confirmation"
            state["next_action"] = "respond"
            return state
        if result.get("waiting_for_approval"):
            approval = result.get("approval") or {}
            state["pending_approval"] = approval
            state["execution_status"] = "waiting_for_approval"
            try:
                get_supabase_client().table("resolveai_agent_runs").update(
                    {"status": "waiting_for_approval"}
                ).eq("id", state["run_id"]).execute()
            except Exception:  # noqa: BLE001
                pass
            _record_event(
                state,
                "approval_requested",
                name,
                "Pending support approval",
                safe_output={"approval_id": approval.get("id")},
            )
            # Pause graph until support approves/rejects.
            approval_result = interrupt(
                {
                    "type": "approval_required",
                    "approval_id": approval.get("id"),
                    "requested_action": approval.get("requested_action"),
                    "message": "Waiting for support approval",
                }
            )
            state["approval_result"] = approval_result
            state["next_action"] = "decide"
            return state
        state["next_action"] = "decide"
    except Exception as exc:  # noqa: BLE001
        state["tool_results"] = list(state.get("tool_results") or []) + [{"tool": name, "error": str(exc)}]
        state["final_response"] = f"I could not submit that request: {exc}"
        state["next_action"] = "respond"
    return state


def escalate(state: AgentState) -> AgentState:
    from app.agent.tools.registry import EscalateInput, tool_escalate_to_human

    args = EscalateInput(
        conversation_id=state["conversation_id"],
        issue_summary=state.get("final_response") or state["current_request"][:200],
        escalation_reason=state.get("error") or "Agent escalation",
        priority=state.get("priority") or "medium",
    )
    result = tool_escalate_to_human(
        args,
        {
            "customer_id": state.get("customer_id"),
            "sentiment": state.get("sentiment"),
        },
    )
    state["tool_results"] = list(state.get("tool_results") or []) + [{"tool": "escalate_to_human", "result": result}]
    ticket_ref = (result.get("ticket") or {}).get("ticket_reference")
    state["final_response"] = (
        state.get("final_response")
        or f"I've escalated this to a human support specialist. Ticket: {ticket_ref}."
    )
    state["execution_status"] = "escalated"
    _record_event(state, "tool_completed", "escalate_to_human", f"Escalated as {ticket_ref}")
    return state


def compose_response(state: AgentState) -> AgentState:
    if not state.get("final_response"):
        state["final_response"] = "I've finished reviewing your request."
    citations = state.get("retrieved_policies") or []
    if citations and "policy" not in (state["final_response"] or "").lower():
        titles = ", ".join(sorted({c.get("title") for c in citations if c.get("title")})[:3])
        if titles:
            state["final_response"] = f"{state['final_response']}\n\nPolicy references: {titles}."
    state["execution_status"] = state.get("execution_status") or "completed"
    _record_event(state, "response_generated", "compose_response", "Generated customer response")
    try:
        get_supabase_client().table("resolveai_agent_runs").update(
            {
                "status": "completed" if state["execution_status"] != "failed" else "failed",
                "intent": state.get("detected_intent"),
                "selected_provider": state.get("provider"),
                "selected_model": state.get("model"),
                "total_steps": state.get("step_count") or 0,
                "total_tool_calls": state.get("tool_call_count") or 0,
                "final_response": state.get("final_response"),
                "completed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            }
        ).eq("id", state["run_id"]).execute()
    except Exception:  # noqa: BLE001
        pass
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("understand_request", understand_request)
    graph.add_node("load_customer_context", load_customer_context)
    graph.add_node("retrieve_policies", retrieve_policies)
    graph.add_node("agent_decision", agent_decision)
    graph.add_node("execute_read_tool", execute_read_tool)
    graph.add_node("execute_write_tool", execute_write_tool_and_maybe_interrupt)
    graph.add_node("escalate", escalate)
    # Node name must not collide with AgentState keys (e.g. final_response).
    graph.add_node("compose_response", compose_response)

    graph.set_entry_point("understand_request")
    graph.add_edge("understand_request", "load_customer_context")
    graph.add_edge("load_customer_context", "retrieve_policies")
    graph.add_edge("retrieve_policies", "agent_decision")

    def _route(state: AgentState) -> str:
        action = state.get("next_action")
        if action == "tool":
            calls = state.get("tool_calls") or []
            name = (calls[0] or {}).get("name") if calls else None
            spec = TOOL_REGISTRY.get(name or "")
            if spec and spec.classification == "write":
                return "execute_write_tool"
            if spec and spec.classification == "escalate":
                return "escalate"
            return "execute_read_tool"
        if action == "decide":
            return "agent_decision"
        if action == "escalate":
            return "escalate"
        return "compose_response"

    graph.add_conditional_edges(
        "agent_decision",
        _route,
        {
            "execute_read_tool": "execute_read_tool",
            "execute_write_tool": "execute_write_tool",
            "escalate": "escalate",
            "compose_response": "compose_response",
            "agent_decision": "agent_decision",
        },
    )
    graph.add_conditional_edges(
        "execute_read_tool",
        lambda s: "agent_decision" if s.get("next_action") == "decide" else "compose_response",
        {"agent_decision": "agent_decision", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "execute_write_tool",
        lambda s: "agent_decision" if s.get("next_action") == "decide" else "compose_response",
        {"agent_decision": "agent_decision", "compose_response": "compose_response"},
    )
    graph.add_edge("escalate", "compose_response")
    graph.add_edge("compose_response", END)

    checkpointer = build_checkpointer()
    return graph.compile(checkpointer=checkpointer)


_GRAPH = None


def get_agent_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH
