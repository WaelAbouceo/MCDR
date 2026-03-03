from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.schemas.qa import QAEvaluationCreate, QAEvaluationOut, QAScorecardCreate, QAScorecardOut
from src.services import qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.get("/scorecards", response_model=list[QAScorecardOut])
async def list_scorecards(
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    return await qa_service.list_scorecards(db)


@router.post("/scorecards", response_model=QAScorecardOut, status_code=201)
async def create_scorecard(
    body: QAScorecardCreate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.QA, Action.CREATE)),
):
    sc = await qa_service.create_scorecard(db, body)
    await db.commit()
    return sc


@router.post("/evaluations", response_model=QAEvaluationOut, status_code=201)
async def create_evaluation(
    body: QAEvaluationCreate,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.QA, Action.EVALUATE)),
):
    ev = await qa_service.create_evaluation(db, data=body, evaluator_id=user.id)
    await db.commit()
    return ev


@router.get("/evaluations", response_model=list[QAEvaluationOut])
async def list_evaluations(
    agent_id: int | None = None,
    case_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    return await qa_service.list_evaluations(db, agent_id=agent_id, case_id=case_id, limit=limit, offset=offset)
