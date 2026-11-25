from fastapi import APIRouter, HTTPException

from app.core.security import CurrentUser
from app.repositories.orders import OrderRepository

router = APIRouter()


@router.get("")
def list_orders(user: CurrentUser):
    repo = OrderRepository()
    customer = repo.get_customer_by_user_id(user.user_id)
    if not customer:
        return {"items": [], "total": 0}
    if user.is_staff:
        # Staff can list via tickets/approvals; customer list remains ownership scoped here.
        items = repo.list_orders_for_customer(customer["id"])
    else:
        items = repo.list_orders_for_customer(customer["id"])
    return {"items": items, "total": len(items)}


@router.get("/{order_reference}")
def get_order(order_reference: str, user: CurrentUser):
    repo = OrderRepository()
    customer = repo.get_customer_by_user_id(user.user_id)
    if not customer and not user.is_staff:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    if user.is_staff:
        order = repo.get_order_by_reference(order_reference)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    return repo.get_owned_order(order_reference, customer["id"])


@router.get("/{order_reference}/events")
def get_order_events(order_reference: str, user: CurrentUser):
    repo = OrderRepository()
    customer = repo.get_customer_by_user_id(user.user_id)
    if user.is_staff:
        order = repo.get_order_by_reference(order_reference)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
    else:
        if not customer:
            raise HTTPException(status_code=404, detail="Customer profile not found")
        order = repo.get_owned_order(order_reference, customer["id"])
    return {"order_reference": order_reference, "events": repo.list_events(order["id"])}
