"""LangGraph shared agent state."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict


def merge_dicts(left: Dict[str, Any] | None, right: Dict[str, Any] | None) -> Dict[str, Any]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class AgentState(TypedDict, total=False):
    run_id: str
    conversation_id: str
    authenticated_user_id: str
    authenticated_role: str
    customer_id: Optional[str]
    current_request: str
    conversation_context: List[Dict[str, str]]
    detected_intent: Optional[str]
    extracted_entities: Dict[str, Any]
    priority: str
    sentiment: str
    order_context: Dict[str, Any]
    retrieved_policies: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    tool_results: Annotated[List[Dict[str, Any]], operator.add]
    pending_approval: Optional[Dict[str, Any]]
    approval_result: Optional[Dict[str, Any]]
    execution_status: str
    provider: Optional[str]
    model: Optional[str]
    step_count: int
    tool_call_count: int
    error: Optional[str]
    final_response: Optional[str]
    needs_clarification: bool
    clarification_question: Optional[str]
    next_action: Optional[str]
    messages: List[Dict[str, Any]]
    metadata: Annotated[Dict[str, Any], merge_dicts]
