from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.qa import QAEvaluation, QAScorecard
from src.schemas.qa import QAEvaluationCreate, QAScorecardCreate
from src.services import audit_service


async def create_scorecard(db: AsyncSession, data: QAScorecardCreate) -> QAScorecard:
    sc = QAScorecard(name=data.name, criteria=data.criteria, max_score=data.max_score)
    db.add(sc)
    await db.flush()
    return sc


async def list_scorecards(db: AsyncSession) -> list[QAScorecard]:
    result = await db.execute(select(QAScorecard).where(QAScorecard.is_active.is_(True)))
    return list(result.scalars().all())


async def create_evaluation(db: AsyncSession, *, data: QAEvaluationCreate, evaluator_id: int) -> QAEvaluation:
    ev = QAEvaluation(
        case_id=data.case_id,
        call_id=data.call_id,
        evaluator_id=evaluator_id,
        agent_id=data.agent_id,
        scorecard_id=data.scorecard_id,
        scores=data.scores,
        total_score=data.total_score,
        feedback=data.feedback,
    )
    db.add(ev)
    await db.flush()
    await audit_service.log_action(
        db, user_id=evaluator_id, action="evaluate", resource="qa", resource_id=ev.id
    )
    return ev


async def list_evaluations(
    db: AsyncSession,
    *,
    agent_id: int | None = None,
    case_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[QAEvaluation]:
    stmt = select(QAEvaluation)
    if agent_id:
        stmt = stmt.where(QAEvaluation.agent_id == agent_id)
    if case_id:
        stmt = stmt.where(QAEvaluation.case_id == case_id)
    stmt = stmt.order_by(QAEvaluation.evaluated_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def agent_avg_score(db: AsyncSession, agent_id: int) -> float | None:
    stmt = select(func.avg(QAEvaluation.total_score)).where(QAEvaluation.agent_id == agent_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
