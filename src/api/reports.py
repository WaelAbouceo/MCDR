from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case as sql_case
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.case import Case, CaseStatus
from src.models.sla import SLABreach, SLAPolicy, BreachType
from src.models.qa import QAEvaluation
from src.models.user import User
from src.schemas.report import AgentPerformanceRow, CaseVolumeRow, OperationalDashboard, SLAComplianceRow

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard", response_model=OperationalDashboard)
async def operational_dashboard(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    volume = await _case_volume(db, start, now)
    compliance = await _sla_compliance(db, start, now)
    performance = await _agent_performance(db, start, now)

    return OperationalDashboard(
        period_start=start,
        period_end=now,
        case_volume=volume,
        sla_compliance=compliance,
        agent_performance=performance,
    )


async def _case_volume(db: AsyncSession, start: datetime, end: datetime) -> list[CaseVolumeRow]:
    date_col = func.date(Case.created_at).label("date")
    stmt = (
        select(
            date_col,
            func.count().label("total"),
            func.count().filter(Case.status.in_([CaseStatus.OPEN, CaseStatus.IN_PROGRESS])).label("open"),
            func.count().filter(Case.status == CaseStatus.RESOLVED).label("resolved"),
            func.count().filter(Case.status == CaseStatus.ESCALATED).label("escalated"),
        )
        .where(Case.created_at.between(start, end))
        .group_by(date_col)
        .order_by(date_col)
    )
    result = await db.execute(stmt)
    return [CaseVolumeRow(date=str(r.date), total=r.total, open=r.open, resolved=r.resolved, escalated=r.escalated) for r in result]


async def _sla_compliance(db: AsyncSession, start: datetime, end: datetime) -> list[SLAComplianceRow]:
    stmt = (
        select(
            SLAPolicy.name,
            func.count(Case.id).label("total_cases"),
            func.count().filter(
                ~Case.id.in_(select(SLABreach.case_id).where(SLABreach.breach_type == BreachType.FIRST_RESPONSE))
            ).label("frt_met"),
            func.count().filter(
                Case.id.in_(select(SLABreach.case_id).where(SLABreach.breach_type == BreachType.FIRST_RESPONSE))
            ).label("frt_breached"),
            func.count().filter(
                ~Case.id.in_(select(SLABreach.case_id).where(SLABreach.breach_type == BreachType.RESOLUTION))
            ).label("rt_met"),
            func.count().filter(
                Case.id.in_(select(SLABreach.case_id).where(SLABreach.breach_type == BreachType.RESOLUTION))
            ).label("rt_breached"),
        )
        .join(SLAPolicy, Case.sla_policy_id == SLAPolicy.id)
        .where(Case.created_at.between(start, end))
        .group_by(SLAPolicy.name)
    )
    result = await db.execute(stmt)
    rows = []
    for r in result:
        pct = (r.frt_met + r.rt_met) / max(r.total_cases * 2, 1) * 100
        rows.append(SLAComplianceRow(
            policy_name=r.name, total_cases=r.total_cases,
            frt_met=r.frt_met, frt_breached=r.frt_breached,
            rt_met=r.rt_met, rt_breached=r.rt_breached,
            compliance_pct=round(pct, 1),
        ))
    return rows


async def _agent_performance(db: AsyncSession, start: datetime, end: datetime) -> list[AgentPerformanceRow]:
    resolved_minutes = func.extract("epoch", Case.resolved_at - Case.created_at) / 60

    stmt = (
        select(
            User.id,
            User.full_name,
            func.count(Case.id).label("cases_handled"),
            func.avg(resolved_minutes).label("avg_resolution_minutes"),
        )
        .join(Case, Case.agent_id == User.id)
        .where(Case.created_at.between(start, end))
        .group_by(User.id, User.full_name)
        .order_by(func.count(Case.id).desc())
    )
    result = await db.execute(stmt)
    rows = []
    for r in result:
        avg_qa = await db.execute(
            select(func.avg(QAEvaluation.total_score)).where(
                QAEvaluation.agent_id == r.id,
                QAEvaluation.evaluated_at.between(start, end),
            )
        )
        qa_score = avg_qa.scalar_one_or_none()

        total = await db.execute(
            select(func.count(Case.id)).where(Case.agent_id == r.id, Case.created_at.between(start, end))
        )
        breached = await db.execute(
            select(func.count(SLABreach.id))
            .join(Case, SLABreach.case_id == Case.id)
            .where(Case.agent_id == r.id, Case.created_at.between(start, end))
        )
        total_count = total.scalar_one()
        breach_count = breached.scalar_one()
        compliance = ((total_count - breach_count) / max(total_count, 1)) * 100

        rows.append(AgentPerformanceRow(
            agent_id=r.id,
            agent_name=r.full_name,
            cases_handled=r.cases_handled,
            avg_resolution_minutes=round(r.avg_resolution_minutes, 1) if r.avg_resolution_minutes else None,
            sla_compliance_pct=round(compliance, 1),
            avg_qa_score=round(qa_score, 1) if qa_score else None,
        ))
    return rows
