# Tool Registry

| Tool | Class | Notes |
| --- | --- | --- |
| lookup_order | read | Ownership enforced |
| get_delivery_status | read | Ownership enforced |
| search_policy | read | Hybrid RAG |
| check_return_eligibility | read | Deterministic |
| calculate_refund | read | Does not create refund |
| create_return_request | write | Creates pending approval |
| submit_refund_request | write | Creates pending approval |
| cancel_order | write | Creates pending approval |
| update_shipping_address | write | Creates pending approval |
| escalate_to_human | escalate | Creates support ticket |

Unregistered tools are rejected.
