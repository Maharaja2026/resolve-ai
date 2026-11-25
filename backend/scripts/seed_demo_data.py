"""Idempotent synthetic data seeder for ResolveAI demo.

Creates policy documents and sample customers/orders using deterministic references.
Does not create Supabase Auth users — link customer.user_id after registration.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.core.supabase_client import get_supabase_client
from app.services.embeddings.fastembed_service import get_embedding_service


POLICIES = [
    ("Return and Refund Policy", "refund", "return_refund.md"),
    ("Cancellation Policy", "cancellation", "cancellation.md"),
    ("Shipping and Delivery Policy", "shipping", "shipping.md"),
    ("Refund Processing Policy", "refund", None),
    ("Product Replacement Policy", "replacement", None),
    ("Damaged Item Policy", "damaged", None),
    ("Wrong Item Policy", "wrong_item", None),
    ("Late Delivery Policy", "shipping", None),
    ("Address Modification Policy", "address", None),
    ("Customer Escalation Policy", "escalation", None),
]

FALLBACK_CONTENT = {
    "Refund Processing Policy": "Simulated refunds are processed after support approval and recorded with a synthetic transaction reference.",
    "Product Replacement Policy": "Replacements may be offered for damaged or wrong items after eligibility checks.",
    "Damaged Item Policy": "Report damaged items within 7 days of delivery with photos when possible.",
    "Wrong Item Policy": "If the wrong item arrives, customers may request a replacement or refund review.",
    "Late Delivery Policy": "Deliveries delayed beyond expected date + 3 days may qualify for refund review.",
    "Address Modification Policy": "Shipping addresses can be changed only before shipment and require approval.",
    "Customer Escalation Policy": "Customers may request a human agent at any time. Complex disputes must be escalated.",
}


def upsert_policies(client):
    policy_dir = ROOT / "sample_data" / "policies"
    emb = get_embedding_service()
    for title, category, filename in POLICIES:
        if filename:
            content = (policy_dir / filename).read_text(encoding="utf-8")
        else:
            content = FALLBACK_CONTENT[title]
        existing = (
            client.table("resolveai_policy_documents")
            .select("id")
            .eq("title", title)
            .eq("version", "1.0")
            .limit(1)
            .execute()
        )
        if existing.data:
            doc_id = existing.data[0]["id"]
        else:
            created = (
                client.table("resolveai_policy_documents")
                .insert(
                    {
                        "title": title,
                        "category": category,
                        "content": content,
                        "version": "1.0",
                        "is_active": True,
                    }
                )
                .execute()
            )
            doc_id = created.data[0]["id"]

        # Recreate chunks idempotently
        client.table("resolveai_policy_chunks").delete().eq("document_id", doc_id).execute()
        chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
        vectors = emb.embed_documents(chunks)
        rows = []
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            rows.append(
                {
                    "document_id": doc_id,
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": vector,
                    "metadata": {"category": category, "title": title},
                }
            )
        if rows:
            client.table("resolveai_policy_chunks").insert(rows).execute()
        print(f"Policy ready: {title} ({len(rows)} chunks)")


def upsert_customers_and_orders(client):
    now = datetime.now(timezone.utc)
    customers = []
    for i in range(1, 9):
        ref = f"CUST-{1000 + i}"
        existing = client.table("resolveai_customers").select("*").eq("customer_reference", ref).limit(1).execute()
        if existing.data:
            customers.append(existing.data[0])
            continue
        created = (
            client.table("resolveai_customers")
            .insert(
                {
                    "customer_reference": ref,
                    "full_name": f"Demo Customer {i}",
                    "email": f"demo.customer{i}@example.com",
                    "phone": f"+1-555-010{i}",
                }
            )
            .execute()
        )
        customers.append(created.data[0])

    statuses = [
        "processing",
        "shipped",
        "out_for_delivery",
        "delivered",
        "delivered",
        "cancelled",
        "return_requested",
        "shipped",
        "delivered",
        "processing",
    ]
    for idx in range(1, 21):
        order_ref = f"ORD-{1000 + idx}"
        existing = client.table("resolveai_orders").select("id").eq("order_reference", order_ref).limit(1).execute()
        if existing.data:
            continue
        customer = customers[(idx - 1) % len(customers)]
        status = statuses[(idx - 1) % len(statuses)]
        ordered_at = now - timedelta(days=20 - (idx % 15))
        expected = ordered_at + timedelta(days=5)
        delivered_at = expected + timedelta(days=1) if status == "delivered" else None
        if idx in {5, 12}:
            # Late shipment examples
            status = "shipped"
            expected = now - timedelta(days=6)
            delivered_at = None
        order = (
            client.table("resolveai_orders")
            .insert(
                {
                    "order_reference": order_ref,
                    "customer_id": customer["id"],
                    "order_status": status,
                    "payment_status": "paid",
                    "total_amount": 49.99 + idx,
                    "currency": "USD",
                    "shipping_address": {
                        "line1": f"{100 + idx} Market Street",
                        "city": "Austin",
                        "state": "TX",
                        "postal_code": "78701",
                        "country": "US",
                    },
                    "tracking_reference": f"TRK{1000 + idx}",
                    "product_summary": f"Demo Product Bundle {idx}",
                    "ordered_at": ordered_at.isoformat(),
                    "expected_delivery_at": expected.isoformat(),
                    "delivered_at": delivered_at.isoformat() if delivered_at else None,
                }
            )
            .execute()
        )
        order_id = order.data[0]["id"]
        events = [
            ("created", "Order placed", "Online"),
            ("confirmed", "Payment confirmed", "Payments"),
            ("processing", "Order is being prepared", "Warehouse"),
        ]
        if status in {"shipped", "out_for_delivery", "delivered", "return_requested"}:
            events.append(("shipped", "Package shipped", "Warehouse"))
        if status in {"out_for_delivery", "delivered"}:
            events.append(("out_for_delivery", "Out for delivery", "Local hub"))
        if status == "delivered":
            events.append(("delivered", "Delivered to customer", "Customer address"))
        if status == "cancelled":
            events.append(("cancelled", "Order cancelled", "Support"))
        rows = []
        for offset, (etype, desc, loc) in enumerate(events):
            rows.append(
                {
                    "order_id": order_id,
                    "event_type": etype,
                    "description": desc,
                    "location": loc,
                    "event_timestamp": (ordered_at + timedelta(hours=offset * 8)).isoformat(),
                }
            )
        client.table("resolveai_order_events").insert(rows).execute()
        print(f"Order ready: {order_ref} ({status})")


def main():
    client = get_supabase_client()
    upsert_policies(client)
    upsert_customers_and_orders(client)
    print("Seed complete. Link a registered auth user to a resolveai_customers.user_id for demo chat.")


if __name__ == "__main__":
    main()
