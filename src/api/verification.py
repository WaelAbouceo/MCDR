"""Identity verification session management."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/verification", tags=["verification"])


class VerificationStart(BaseModel):
    investor_id: int = Field(ge=1)
    call_id: int | None = Field(default=None, ge=1)
    method: Literal["verbal", "otp", "document"] = "verbal"


class VerificationStepUpdate(BaseModel):
    step: str = Field(min_length=1, max_length=50)
    passed: bool


class VerificationComplete(BaseModel):
    status: Literal["passed", "failed", "skipped"]
    failure_reason: str | None = Field(default=None, max_length=500)


class VerificationLink(BaseModel):
    case_id: int = Field(ge=1)


@router.post("/start", status_code=201)
async def start_verification(
    body: VerificationStart,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.CREATE)),
):
    session = cx_data_service.start_verification(
        investor_id=body.investor_id,
        agent_id=user.id,
        call_id=body.call_id,
        method=body.method,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="create", resource="verification",
        resource_id=session.get("verification_id"),
        detail=f"investor_id={body.investor_id} method={body.method}",
    )
    await db.commit()
    return session


@router.get("/{verification_id}")
async def get_verification(
    verification_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    v = cx_data_service.get_verification(verification_id)
    if not v:
        raise NotFoundError("Verification", verification_id)
    return v


@router.get("/case/{case_id}")
async def get_verification_for_case(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    v = cx_data_service.get_verification_for_case(case_id)
    return v or {"verification_id": None, "status": "none"}


@router.patch("/{verification_id}/step")
async def update_step(
    verification_id: int,
    body: VerificationStepUpdate,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    v = cx_data_service.get_verification(verification_id)
    if not v:
        raise NotFoundError("Verification", verification_id)

    result = cx_data_service.update_verification_step(
        verification_id, step=body.step, passed=body.passed,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="verification",
        resource_id=verification_id,
        detail=f"step={body.step} passed={body.passed}",
    )
    await db.commit()
    return result


@router.patch("/{verification_id}/complete")
async def complete_verification(
    verification_id: int,
    body: VerificationComplete,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    v = cx_data_service.get_verification(verification_id)
    if not v:
        raise NotFoundError("Verification", verification_id)

    result = cx_data_service.complete_verification(
        verification_id, status=body.status, failure_reason=body.failure_reason,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="verification",
        resource_id=verification_id,
        detail=f"status={body.status}",
    )
    await db.commit()
    return result


@router.post("/{verification_id}/link")
async def link_to_case(
    verification_id: int,
    body: VerificationLink,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    v = cx_data_service.get_verification(verification_id)
    if not v:
        raise NotFoundError("Verification", verification_id)

    try:
        cx_data_service.link_verification_to_case(body.case_id, verification_id)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="case",
        resource_id=body.case_id,
        detail=f"linked verification_id={verification_id}",
    )
    await db.commit()
    return {"linked": True, "case_id": body.case_id, "verification_id": verification_id}
