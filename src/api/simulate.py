"""Call simulation endpoints — mimics Cisco CTI incoming call flow."""

from fastapi import APIRouter, Depends, Query

from src.core.permissions import Action, Resource
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.services.call_simulator import (
    simulate_incoming_call,
    poll_incoming_call,
    accept_incoming_call,
    dismiss_incoming_call,
)

router = APIRouter(prefix="/simulate", tags=["simulation"])


@router.post("/incoming-call")
async def simulate_call(
    ani: str | None = Query(default=None, description="Caller phone number (ANI). Random if omitted."),
    queue: str | None = Query(default=None, description="Target queue"),
    agent_id: int | None = Query(default=None, description="Target agent ID. Random if omitted."),
    call_reason: int | None = Query(default=None, description="Taxonomy ID for call reason"),
    _: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    """Simulate a Cisco IVR incoming call. Pushes screen-pop to the assigned agent's queue."""
    return simulate_incoming_call(ani=ani, queue=queue, target_agent_id=agent_id, call_reason_id=call_reason)


@router.get("/incoming")
async def check_incoming(user: User = Depends(get_current_user)):
    """Poll for an incoming call assigned to the current agent."""
    call = poll_incoming_call(user.id)
    if call:
        return {"has_call": True, "call": call}
    return {"has_call": False}


@router.post("/incoming/accept")
async def accept_call(user: User = Depends(get_current_user)):
    """Agent accepts the incoming call — returns full screen-pop and clears the queue."""
    call = accept_incoming_call(user.id)
    if call:
        return {"accepted": True, "call": call}
    return {"accepted": False}


@router.post("/incoming/dismiss")
async def dismiss_call(user: User = Depends(get_current_user)):
    """Agent dismisses/rejects the incoming call."""
    dismiss_incoming_call(user.id)
    return {"dismissed": True}
