"""Deterministic business eligibility rules — never LLM-decided."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def check_return_eligibility(order: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    settings = get_settings()
    status = (order.get("order_status") or "").lower()
    now = datetime.now(timezone.utc)
    delivered_at = _parse_dt(order.get("delivered_at"))

    if status in {"cancelled", "returned"}:
        return {
            "eligible": False,
            "reason_codes": ["invalid_status"],
            "explanation": f"Orders with status '{status}' cannot be returned.",
            "window_days": settings.return_window_days,
        }
    if status == "return_requested":
        return {
            "eligible": False,
            "reason_codes": ["already_requested"],
            "explanation": "A return has already been requested for this order.",
            "window_days": settings.return_window_days,
        }
    if status not in {"delivered", "shipped", "out_for_delivery"} and "delay" not in reason.lower():
        if status not in {"shipped", "out_for_delivery"}:
            return {
                "eligible": False,
                "reason_codes": ["not_delivered"],
                "explanation": "Return is typically available after delivery, or for confirmed late shipments.",
                "window_days": settings.return_window_days,
            }

    if delivered_at:
        age_days = (now - delivered_at).days
        if age_days > settings.return_window_days:
            return {
                "eligible": False,
                "reason_codes": ["outside_return_window"],
                "explanation": f"Return window of {settings.return_window_days} days has expired ({age_days} days since delivery).",
                "window_days": settings.return_window_days,
                "days_since_delivery": age_days,
            }

    return {
        "eligible": True,
        "reason_codes": ["within_policy"],
        "explanation": "Order appears eligible for a return request pending support approval.",
        "window_days": settings.return_window_days,
    }


def calculate_refund_amount(order: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    settings = get_settings()
    eligibility = check_return_eligibility(order, reason=reason)
    total = float(order.get("total_amount") or 0)
    status = (order.get("order_status") or "").lower()
    expected = _parse_dt(order.get("expected_delivery_at"))
    now = datetime.now(timezone.utc)

    late = False
    if expected and status in {"shipped", "out_for_delivery", "processing"}:
        late = now.date() > expected.date() and (now - expected).days >= settings.late_delivery_grace_days

    if late and "delay" in reason.lower():
        eligibility = {
            "eligible": True,
            "reason_codes": ["late_delivery"],
            "explanation": "Shipment exceeds expected delivery by the late-delivery grace period.",
            "window_days": settings.return_window_days,
        }

    if not eligibility["eligible"]:
        return {
            **eligibility,
            "estimated_amount": 0.0,
            "currency": order.get("currency") or "USD",
            "capped": False,
        }

    amount = min(total, settings.max_simulated_refund_amount)
    return {
        "eligible": True,
        "reason_codes": eligibility.get("reason_codes", []),
        "explanation": eligibility.get("explanation"),
        "estimated_amount": round(amount, 2),
        "currency": order.get("currency") or "USD",
        "capped": amount < total,
        "order_total": total,
    }


def check_cancellation_eligibility(order: Dict[str, Any]) -> Dict[str, Any]:
    status = (order.get("order_status") or "").lower()
    if status in {"cancelled", "delivered", "returned", "return_requested"}:
        return {
            "eligible": False,
            "reason_codes": ["invalid_status"],
            "explanation": f"Cannot cancel an order with status '{status}'.",
        }
    if status in {"shipped", "out_for_delivery"}:
        return {
            "eligible": False,
            "reason_codes": ["already_shipped"],
            "explanation": "Order has already shipped. Cancellation is unavailable; consider a return after delivery.",
        }
    return {
        "eligible": True,
        "reason_codes": ["pre_shipment"],
        "explanation": "Order can be cancelled pending support approval.",
    }


def check_address_change_eligibility(order: Dict[str, Any]) -> Dict[str, Any]:
    status = (order.get("order_status") or "").lower()
    if status in {"shipped", "out_for_delivery", "delivered", "cancelled", "returned"}:
        return {
            "eligible": False,
            "reason_codes": ["shipment_locked"],
            "explanation": f"Shipping address cannot be changed when status is '{status}'.",
        }
    return {
        "eligible": True,
        "reason_codes": ["pre_shipment"],
        "explanation": "Address change is allowed pending support approval.",
    }
