from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/approvals", tags=["approvals"])

ApprovalType = Literal["refund", "account_closure", "data_correction", "fee_waiver", "escalation_override"]


class ApprovalCreateBody(BaseModel):
    case_id: int = Field(ge=1)
    approval_type: ApprovalType
    description: str = Field(min_length=5, max_length=2000)
    amount: float | None = Field(default=None, ge=0)


class ApprovalReviewBody(BaseModel):
    decision: Literal["approved", "rejected"]
    notes: str | None = Field(default=None, max_length=2000)


@router.post("", status_code=201)
async def create_approval(
    body: ApprovalCreateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.APPROVAL, Action.CREATE)),
):
    try:
        result = cx_data_service.create_approval(
            case_id=body.case_id,
            requested_by=user.id,
            approval_type=body.approval_type,
            description=body.description,
            amount=body.amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await audit_service.log_action(
        db, user_id=user.id, action="request_approval", resource="approval",
        resource_id=result.get("approval_id"),
        detail=f"type={body.approval_type} case={body.case_id} amount={body.amount}",
    )
    await db.commit()
    return result


@router.get("")
async def list_approvals(
    status: str | None = None,
    case_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(RequirePermission(Resource.APPROVAL, Action.READ)),
):
    return cx_data_service.list_approvals(status=status, case_id=case_id, limit=limit)


@router.get("/pending/count")
async def pending_count(
    _: User = Depends(RequirePermission(Resource.APPROVAL, Action.READ)),
):
    return {"count": cx_data_service.pending_approval_count()}


@router.patch("/{approval_id}")
async def review_approval(
    approval_id: int,
    body: ApprovalReviewBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.APPROVAL, Action.UPDATE)),
):
    try:
        result = cx_data_service.review_approval(
            approval_id=approval_id,
            reviewed_by=user.id,
            decision=body.decision,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await audit_service.log_action(
        db, user_id=user.id, action=f"approval_{body.decision}", resource="approval",
        resource_id=approval_id,
        detail=f"notes={body.notes}",
    )
    await db.commit()
    return result
