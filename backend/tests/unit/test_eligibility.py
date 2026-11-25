from datetime import datetime, timedelta, timezone

from app.services.orders.eligibility import (
    calculate_refund_amount,
    check_address_change_eligibility,
    check_cancellation_eligibility,
    check_return_eligibility,
)


def _order(**overrides):
    base = {
        "order_status": "delivered",
        "payment_status": "paid",
        "total_amount": 120.0,
        "currency": "USD",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "expected_delivery_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    }
    base.update(overrides)
    return base


def test_return_eligible_within_window():
    result = check_return_eligibility(_order(), reason="damaged")
    assert result["eligible"] is True


def test_return_ineligible_outside_window():
    old = datetime.now(timezone.utc) - timedelta(days=45)
    result = check_return_eligibility(_order(delivered_at=old.isoformat()), reason="changed mind")
    assert result["eligible"] is False
    assert "outside_return_window" in result["reason_codes"]


def test_cancellation_blocked_when_shipped():
    result = check_cancellation_eligibility(_order(order_status="shipped"))
    assert result["eligible"] is False


def test_address_change_allowed_pre_shipment():
    result = check_address_change_eligibility(_order(order_status="processing"))
    assert result["eligible"] is True


def test_refund_calculation_caps_amount():
    result = calculate_refund_amount(_order(total_amount=99999), reason="delay")
    assert result["eligible"] is True
    assert result["estimated_amount"] <= 5000
