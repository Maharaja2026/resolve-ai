from app.agent.tools.registry import TOOL_REGISTRY, list_tool_definitions
from app.services.retrieval.rrf import reciprocal_rank_fusion


def test_rrf_prefers_overlap():
    a = {"id": "1"}
    b = {"id": "2"}
    c = {"id": "3"}
    fused = reciprocal_rank_fusion([[a, b], [b, c]], key_fn=lambda x: x["id"])
    assert fused[0][0]["id"] == "2"


def test_tool_registry_complete():
    required = {
        "lookup_order",
        "get_delivery_status",
        "search_policy",
        "check_return_eligibility",
        "calculate_refund",
        "create_return_request",
        "submit_refund_request",
        "cancel_order",
        "update_shipping_address",
        "escalate_to_human",
    }
    assert required.issubset(set(TOOL_REGISTRY))
    defs = list_tool_definitions()
    assert len(defs) == len(TOOL_REGISTRY)
