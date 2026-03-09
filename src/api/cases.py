from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.services import audit_service
from src.services.async_cx import cx

router = APIRouter(prefix="/cases", tags=["cases"])

Priority = Literal["low", "medium", "high", "critical"]
Status = Literal["open", "in_progress", "pending_customer", "escalated", "resolved", "closed"]


class CaseCreateBody(BaseModel):
    subject: str = Field(min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority = "medium"
    investor_id: int | None = Field(default=None, ge=1)
    call_id: int | None = Field(default=None, ge=1)
    taxonomy_id: int | None = Field(default=None, ge=1)


ResolutionCode = Literal[
    "fixed", "duplicate", "cannot_reproduce", "wont_fix",
    "referred_third_party", "customer_withdrew", "information_provided",
    "account_updated",
]


class CaseUpdateBody(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    subject: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    taxonomy_id: int | None = Field(default=None, ge=1)
    resolution_code: ResolutionCode | None = None


class CaseReassignBody(BaseModel):
    agent_id: int = Field(ge=1)


class CaseNoteBody(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


@router.get("/check-duplicates")
async def check_duplicates(
    investor_id: int = Query(..., ge=1),
    subject: str = Query(..., min_length=2),
    days: int = Query(default=30, ge=1, le=90),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Return recent cases for the same investor that may be similar (for duplicate warning)."""
    return await cx.check_duplicate_cases(investor_id=investor_id, subject=subject, days=days)


@router.post("", status_code=201)
async def create_case(
    body: CaseCreateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.CREATE)),
):
    case = await cx.create_case(
        agent_id=user.id,
        investor_id=body.investor_id,
        call_id=body.call_id,
        subject=body.subject,
        description=body.description,
        priority=body.priority,
        taxonomy_id=body.taxonomy_id,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="create", resource="case",
        resource_id=case.get("case_id"),
        detail=f"subject={body.subject} investor_id={body.investor_id} priority={body.priority}"
    )
    await db.commit()
    return case


@router.get("")
async def list_cases(
    agent_id: int | None = None,
    status: Status | None = None,
    priority: Priority | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return await cx.search_cases(
        status=status, priority=priority, limit=limit, offset=offset,
    )


@router.get("/{case_id}")
async def get_case(
    case_id: int,
    user: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    case = await cx.get_case(case_id)
    if not case:
        raise NotFoundError("Case", case_id)
    if user.role and user.role.name in ("agent", "senior_agent") and case.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only view their own cases")
    return case


@router.patch("/{case_id}")
async def update_case(
    case_id: int,
    body: CaseUpdateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    existing = await cx.get_case(case_id)
    if not existing:
        raise NotFoundError("Case", case_id)

    if user.role and user.role.name in ("agent", "senior_agent") and existing.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only modify their own cases")

    if user.role and user.role.name == "qa_analyst":
        raise ForbiddenError("QA analysts cannot modify case fields — use notes instead")

    changes = body.model_dump(exclude_unset=True)
    try:
        case = await cx.update_case(case_id, agent_id=user.id, **changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="case",
        resource_id=case_id,
        detail=f"changes={changes}"
    )
    await db.commit()
    return case


@router.get("/{case_id}/transitions")
async def get_valid_transitions(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    case = await cx.get_case(case_id)
    if not case:
        raise NotFoundError("Case", case_id)
    return {
        "current_status": case["status"],
        "allowed": await cx.valid_next_statuses(case["status"]),
    }


@router.post("/{case_id}/reassign")
async def reassign_case(
    case_id: int,
    body: CaseReassignBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    existing = await cx.get_case(case_id)
    if not existing:
        raise NotFoundError("Case", case_id)

    if user.role and user.role.name == "qa_analyst":
        raise ForbiddenError("QA analysts cannot reassign cases")

    if user.role and user.role.name == "agent":
        raise ForbiddenError("T1 agents cannot reassign cases")

    case = await cx.reassign_case(
        case_id, new_agent_id=body.agent_id, changed_by=user.id,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="reassign", resource="case",
        resource_id=case_id,
        detail=f"new_agent_id={body.agent_id}"
    )
    await db.commit()
    return case


@router.post("/{case_id}/notes", status_code=201)
async def add_note(
    case_id: int,
    body: CaseNoteBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    existing = await cx.get_case(case_id)
    if not existing:
        raise NotFoundError("Case", case_id)

    if user.role and user.role.name in ("agent", "senior_agent") and existing.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only add notes to their own cases")

    note = await cx.add_case_note(
        case_id,
        author_id=user.id,
        content=body.content,
        is_internal=body.is_internal,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="add_note", resource="case",
        resource_id=case_id,
        detail=f"internal={body.is_internal}"
    )
    await db.commit()
    return note
