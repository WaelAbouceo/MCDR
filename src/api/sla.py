from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.schemas.sla import SLABreachOut, SLAPolicyCreate, SLAPolicyOut
from src.services import sla_service

router = APIRouter(prefix="/sla", tags=["sla"])


@router.get("/policies", response_model=list[SLAPolicyOut])
async def list_policies(
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.SLA, Action.READ)),
):
    return await sla_service.list_policies(db)


@router.post("/policies", response_model=SLAPolicyOut, status_code=201)
async def create_policy(
    body: SLAPolicyCreate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.SLA, Action.CREATE)),
):
    policy = await sla_service.create_policy(
        db, name=body.name, priority=body.priority, frt=body.first_response_minutes, rt=body.resolution_minutes
    )
    await db.commit()
    return policy


@router.get("/breaches/{case_id}", response_model=list[SLABreachOut])
async def case_breaches(
    case_id: int,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.SLA, Action.READ)),
):
    return await sla_service.get_breaches(db, case_id)
