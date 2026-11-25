"""Order and delivery event data access."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.supabase_client import get_supabase_client


class OrderRepository:
    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def get_customer_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table("resolveai_customers")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_orders_for_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        response = (
            self.client.table("resolveai_orders")
            .select("*")
            .eq("customer_id", customer_id)
            .order("ordered_at", desc=True)
            .execute()
        )
        return response.data or []

    def get_order_by_reference(self, order_reference: str) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table("resolveai_orders")
            .select("*")
            .eq("order_reference", order_reference)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_owned_order(self, order_reference: str, customer_id: str) -> Dict[str, Any]:
        order = self.get_order_by_reference(order_reference)
        if not order or str(order.get("customer_id")) != str(customer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found for this customer",
            )
        return order

    def list_events(self, order_id: str) -> List[Dict[str, Any]]:
        response = (
            self.client.table("resolveai_order_events")
            .select("*")
            .eq("order_id", order_id)
            .order("event_timestamp")
            .execute()
        )
        return response.data or []

    def update_order(self, order_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        response = (
            self.client.table("resolveai_orders")
            .update(updates)
            .eq("id", order_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Order not found")
        return response.data[0]
