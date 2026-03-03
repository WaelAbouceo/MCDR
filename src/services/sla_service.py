from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.sla import BreachType, SLABreach, SLAPolicy


async def match_policy(db: AsyncSession, *, priority: str) -> SLAPolicy | None:
    stmt = select(SLAPolicy).where(SLAPolicy.priority == priority, SLAPolicy.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_policies(db: AsyncSession) -> list[SLAPolicy]:
    result = await db.execute(select(SLAPolicy).order_by(SLAPolicy.priority))
    return list(result.scalars().all())


async def create_policy(db: AsyncSession, *, name: str, priority: str, frt: int, rt: int) -> SLAPolicy:
    policy = SLAPolicy(name=name, priority=priority, first_response_minutes=frt, resolution_minutes=rt)
    db.add(policy)
    await db.flush()
    return policy


async def check_breach(db: AsyncSession, case: Case) -> list[SLABreach]:
    if not case.sla_policy_id:
        return []

    policy = await db.get(SLAPolicy, case.sla_policy_id)
    if not policy:
        return []

    now = datetime.now(timezone.utc)
    breaches: list[SLABreach] = []

    elapsed_minutes = (now - case.created_at).total_seconds() / 60

    if case.first_response_at:
        frt_minutes = (case.first_response_at - case.created_at).total_seconds() / 60
    else:
        frt_minutes = elapsed_minutes

    if frt_minutes > policy.first_response_minutes:
        existing = await _breach_exists(db, case.id, BreachType.FIRST_RESPONSE)
        if not existing:
            breach = SLABreach(case_id=case.id, policy_id=policy.id, breach_type=BreachType.FIRST_RESPONSE)
            db.add(breach)
            breaches.append(breach)

    if case.resolved_at:
        rt_minutes = (case.resolved_at - case.created_at).total_seconds() / 60
    else:
        rt_minutes = elapsed_minutes

    if rt_minutes > policy.resolution_minutes:
        existing = await _breach_exists(db, case.id, BreachType.RESOLUTION)
        if not existing:
            breach = SLABreach(case_id=case.id, policy_id=policy.id, breach_type=BreachType.RESOLUTION)
            db.add(breach)
            breaches.append(breach)

    if breaches:
        await db.flush()
    return breaches


async def get_breaches(db: AsyncSession, case_id: int) -> list[SLABreach]:
    stmt = select(SLABreach).where(SLABreach.case_id == case_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _breach_exists(db: AsyncSession, case_id: int, breach_type: BreachType) -> bool:
    stmt = select(SLABreach.id).where(SLABreach.case_id == case_id, SLABreach.breach_type == breach_type).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
