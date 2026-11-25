from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.security import StaffUser
from app.services.approvals.service import ApprovalService

router = APIRouter()


class ReviewBody(BaseModel):
    comment: str = Field(default="", max_length=2000)


@router.get("")
def list_approvals(user: StaffUser):
    return ApprovalService().list_pending()


@router.get("/{approval_id}")
def get_approval(approval_id: str, user: StaffUser):
    return ApprovalService().get(approval_id)


@router.post("/{approval_id}/approve")
def approve(approval_id: str, payload: ReviewBody, user: StaffUser):
    return ApprovalService().approve(
        approval_id,
        reviewer_user_id=user.user_id,
        reviewer_role=user.role,
        comment=payload.comment,
    )


@router.post("/{approval_id}/reject")
def reject(approval_id: str, payload: ReviewBody, user: StaffUser):
    return ApprovalService().reject(
        approval_id,
        reviewer_user_id=user.user_id,
        reviewer_role=user.role,
        comment=payload.comment,
    )
