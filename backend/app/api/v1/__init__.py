from fastapi import APIRouter

from app.api.v1 import agent, analytics, approvals, auth, conversations, orders, tickets

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(agent.router, tags=["agent"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
