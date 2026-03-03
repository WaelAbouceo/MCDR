"""Cisco CTI integration service.

Handles incoming call events, creates Call records, resolves
customer profiles via ANI, and builds screen-pop payloads.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.telephony import Call, CallStatus, CTIEvent, CTIEventType
from src.schemas.telephony import CallCreate, CTIEventCreate, ScreenPopPayload
from src.services import audit_service


async def register_call(db: AsyncSession, data: CallCreate) -> Call:
    call = Call(
        ani=data.ani,
        dnis=data.dnis,
        queue=data.queue,
        ivr_path=data.ivr_path,
        agent_id=data.agent_id,
    )
    db.add(call)
    await db.flush()
    return call


async def update_call_status(db: AsyncSession, call_id: int, status: CallStatus) -> Call:
    call = await db.get(Call, call_id)
    if not call:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Call", call_id)
    call.status = status
    await db.flush()
    return call


async def record_event(db: AsyncSession, data: CTIEventCreate) -> CTIEvent:
    event = CTIEvent(
        call_id=data.call_id,
        event_type=data.event_type,
        payload=data.payload,
    )
    db.add(event)
    await db.flush()
    return event


async def build_screen_pop(
    cx_db: AsyncSession,
    customer_db: AsyncSession,
    *,
    call_id: int,
    ani: str,
) -> ScreenPopPayload:
    """Look up customer by ANI and count open cases to assemble a screen-pop."""
    from src.models.customer import CustomerProfile
    from src.services.case_service import count_open_for_customer

    stmt = select(CustomerProfile).where(CustomerProfile.phone_number == ani)
    result = await customer_db.execute(stmt)
    customer = result.scalar_one_or_none()

    payload = ScreenPopPayload(call_id=call_id, ani=ani)
    if customer:
        payload.customer_id = customer.id
        payload.customer_name = customer.name
        payload.account_tier = customer.account_tier
        payload.open_cases = await count_open_for_customer(cx_db, customer.id)

    return payload


async def get_call(db: AsyncSession, call_id: int) -> Call | None:
    return await db.get(Call, call_id)


async def list_calls(
    db: AsyncSession,
    *,
    agent_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Call]:
    stmt = select(Call)
    if agent_id:
        stmt = stmt.where(Call.agent_id == agent_id)
    if status:
        stmt = stmt.where(Call.status == status)
    stmt = stmt.order_by(Call.call_start.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
