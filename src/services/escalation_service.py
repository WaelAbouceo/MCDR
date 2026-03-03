from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.models.case import Case, CaseStatus
from src.models.escalation import Escalation, EscalationRule
from src.models.user import User
from src.schemas.escalation import EscalationCreate
from src.services import audit_service


async def escalate(db: AsyncSession, *, data: EscalationCreate, from_user: User) -> Escalation:
    case = await db.get(Case, data.case_id)
    if not case:
        raise NotFoundError("Case", data.case_id)

    rule = await _match_rule(db, from_tier=from_user.tier.value, to_tier=data.to_tier)

    esc = Escalation(
        case_id=data.case_id,
        rule_id=rule.id if rule else None,
        from_agent_id=from_user.id,
        to_agent_id=data.to_agent_id,
        from_tier=from_user.tier.value,
        to_tier=data.to_tier,
        reason=data.reason,
    )
    db.add(esc)

    case.status = CaseStatus.ESCALATED
    if data.to_agent_id:
        case.agent_id = data.to_agent_id

    await db.flush()
    await audit_service.log_action(
        db,
        user_id=from_user.id,
        action="escalate",
        resource="case",
        resource_id=case.id,
        detail=f"tier {esc.from_tier} → {esc.to_tier}",
    )
    return esc


async def list_escalations(db: AsyncSession, case_id: int) -> list[Escalation]:
    stmt = select(Escalation).where(Escalation.case_id == case_id).order_by(Escalation.escalated_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_rules(db: AsyncSession) -> list[EscalationRule]:
    result = await db.execute(select(EscalationRule).where(EscalationRule.is_active.is_(True)))
    return list(result.scalars().all())


async def _match_rule(db: AsyncSession, *, from_tier: str, to_tier: str) -> EscalationRule | None:
    stmt = select(EscalationRule).where(
        EscalationRule.from_tier == from_tier,
        EscalationRule.to_tier == to_tier,
        EscalationRule.is_active.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
