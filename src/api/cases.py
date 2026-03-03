from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.services import audit_service, cx_data_service

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


class CaseUpdateBody(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    subject: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    taxonomy_id: int | None = Field(default=None, ge=1)


class CaseNoteBody(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


@router.post("", status_code=201)
async def create_case(
    body: CaseCreateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.CREATE)),
):
    case = cx_data_service.create_case(
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
    return cx_data_service.search_cases(
        status=status, priority=priority, limit=limit, offset=offset,
    )


@router.get("/{case_id}")
async def get_case(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    case = cx_data_service.get_case(case_id)
    if not case:
        raise NotFoundError("Case", case_id)
    return case


@router.patch("/{case_id}")
async def update_case(
    case_id: int,
    body: CaseUpdateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    existing = cx_data_service.get_case(case_id)
    if not existing:
        raise NotFoundError("Case", case_id)

    if user.role and user.role.name == "agent" and existing.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only modify their own cases")

    changes = body.model_dump(exclude_unset=True)
    case = cx_data_service.update_case(case_id, agent_id=user.id, **changes)
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="case",
        resource_id=case_id,
        detail=f"changes={changes}"
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
    existing = cx_data_service.get_case(case_id)
    if not existing:
        raise NotFoundError("Case", case_id)

    if user.role and user.role.name == "agent" and existing.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only add notes to their own cases")

    note = cx_data_service.add_case_note(
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
