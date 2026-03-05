"""Outbound task management — callback queue, follow-ups, QA callbacks."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/outbound", tags=["outbound"])

TaskType = Literal["broken_signup", "inactive_user", "transaction_verification", "qa_callback"]
TaskStatus = Literal["pending", "in_progress", "completed", "failed", "cancelled"]


class OutboundTaskCreate(BaseModel):
    task_type: TaskType
    investor_id: int | None = Field(default=None, ge=1)
    case_id: int | None = Field(default=None, ge=1)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    notes: str | None = Field(default=None, max_length=2000)
    scheduled_at: str | None = None


class OutboundTaskUpdate(BaseModel):
    status: TaskStatus | None = None
    outcome: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


@router.get("/stats")
async def outbound_stats(
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.outbound_stats()


@router.get("")
async def list_tasks(
    status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    agent_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.list_outbound_tasks(
        status=status, task_type=task_type, agent_id=agent_id,
        limit=limit, offset=offset,
    )


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    task = cx_data_service.get_outbound_task(task_id)
    if not task:
        raise NotFoundError("OutboundTask", task_id)
    return task


@router.post("", status_code=201)
async def create_task(
    body: OutboundTaskCreate,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.CREATE)),
):
    task = cx_data_service.create_outbound_task(
        task_type=body.task_type,
        investor_id=body.investor_id,
        agent_id=user.id,
        case_id=body.case_id,
        priority=body.priority,
        notes=body.notes,
        scheduled_at=body.scheduled_at,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="create", resource="outbound_task",
        resource_id=task.get("task_id"),
        detail=f"type={body.task_type} investor_id={body.investor_id}",
    )
    await db.commit()
    return task


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    body: OutboundTaskUpdate,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.UPDATE)),
):
    existing = cx_data_service.get_outbound_task(task_id)
    if not existing:
        raise NotFoundError("OutboundTask", task_id)

    changes = body.model_dump(exclude_unset=True)
    task = cx_data_service.update_outbound_task(task_id, agent_id=user.id, **changes)
    await audit_service.log_action(
        db, user_id=user.id, action="update", resource="outbound_task",
        resource_id=task_id, detail=f"changes={changes}",
    )
    await db.commit()
    return task
