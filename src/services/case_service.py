from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError
from src.models.case import Case, CaseHistory, CaseNote, CaseStatus
from src.schemas.case import CaseCreate, CaseNoteCreate, CaseUpdate
from src.services import audit_service, sla_service


async def create_case(db: AsyncSession, *, data: CaseCreate, agent_id: int) -> Case:
    policy = await sla_service.match_policy(db, priority=data.priority)
    case = Case(
        call_id=data.call_id,
        customer_id=data.customer_id,
        agent_id=agent_id,
        taxonomy_id=data.taxonomy_id,
        priority=data.priority,
        subject=data.subject,
        description=data.description,
        sla_policy_id=policy.id if policy else None,
    )
    db.add(case)
    await db.flush()

    await audit_service.log_action(
        db, user_id=agent_id, action="create", resource="case", resource_id=case.id
    )
    return case


async def get_case(db: AsyncSession, case_id: int) -> Case:
    stmt = (
        select(Case)
        .options(selectinload(Case.notes), selectinload(Case.history))
        .where(Case.id == case_id)
    )
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise NotFoundError("Case", case_id)
    return case


async def list_cases(
    db: AsyncSession,
    *,
    agent_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Case]:
    stmt = select(Case)
    if agent_id:
        stmt = stmt.where(Case.agent_id == agent_id)
    if status:
        stmt = stmt.where(Case.status == status)
    if priority:
        stmt = stmt.where(Case.priority == priority)
    stmt = stmt.order_by(Case.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_case(db: AsyncSession, case_id: int, *, data: CaseUpdate, user_id: int) -> Case:
    case = await get_case(db, case_id)
    changes: list[tuple[str, str | None, str | None]] = []

    for field, value in data.model_dump(exclude_unset=True).items():
        old = str(getattr(case, field, None))
        if old != str(value):
            changes.append((field, old, str(value)))
            setattr(case, field, value)

    if data.status == CaseStatus.RESOLVED and case.resolved_at is None:
        case.resolved_at = datetime.now(timezone.utc)
        changes.append(("resolved_at", None, str(case.resolved_at)))

    for field, old, new in changes:
        db.add(CaseHistory(case_id=case.id, field_changed=field, old_value=old, new_value=new, changed_by=user_id))

    await db.flush()

    if case.sla_policy_id:
        await sla_service.check_breach(db, case)

    await audit_service.log_action(db, user_id=user_id, action="update", resource="case", resource_id=case.id)
    return case


async def record_first_response(db: AsyncSession, case_id: int, user_id: int) -> Case:
    case = await get_case(db, case_id)
    if case.first_response_at is None:
        case.first_response_at = datetime.now(timezone.utc)
        await db.flush()
        if case.sla_policy_id:
            await sla_service.check_breach(db, case)
    return case


async def add_note(db: AsyncSession, case_id: int, *, data: CaseNoteCreate, author_id: int) -> CaseNote:
    await get_case(db, case_id)
    note = CaseNote(case_id=case_id, author_id=author_id, content=data.content, is_internal=data.is_internal)
    db.add(note)
    await db.flush()
    return note


async def count_open_for_customer(db: AsyncSession, customer_id: int) -> int:
    stmt = select(func.count()).where(
        Case.customer_id == customer_id,
        Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS, CaseStatus.ESCALATED]),
    )
    result = await db.execute(stmt)
    return result.scalar_one()
