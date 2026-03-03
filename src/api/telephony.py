from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_customer_db, get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.schemas.telephony import CallCreate, CallOut, CTIEventCreate, CTIEventOut, ScreenPopPayload
from src.services import cti_service

router = APIRouter(prefix="/telephony", tags=["telephony"])


@router.post("/calls", response_model=CallOut, status_code=201)
async def create_call(
    body: CallCreate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.CALL, Action.CREATE)),
):
    call = await cti_service.register_call(db, body)
    await db.commit()
    return call


@router.get("/calls", response_model=list[CallOut])
async def list_calls(
    agent_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    return await cti_service.list_calls(db, agent_id=agent_id, status=status, limit=limit, offset=offset)


@router.get("/calls/{call_id}", response_model=CallOut)
async def get_call(
    call_id: int,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    call = await cti_service.get_call(db, call_id)
    if not call:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Call", call_id)
    return call


@router.post("/events", response_model=CTIEventOut, status_code=201)
async def record_cti_event(
    body: CTIEventCreate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.CALL, Action.CREATE)),
):
    event = await cti_service.record_event(db, body)
    await db.commit()
    return event


@router.get("/screen-pop/{call_id}", response_model=ScreenPopPayload)
async def screen_pop(
    call_id: int,
    cx_db: AsyncSession = Depends(get_cx_db),
    customer_db: AsyncSession = Depends(get_customer_db),
    _: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    call = await cti_service.get_call(cx_db, call_id)
    if not call:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Call", call_id)
    return await cti_service.build_screen_pop(cx_db, customer_db, call_id=call.id, ani=call.ani)
