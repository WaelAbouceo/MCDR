from datetime import datetime

from pydantic import BaseModel


class CallCreate(BaseModel):
    ani: str
    dnis: str
    queue: str | None = None
    ivr_path: str | None = None
    agent_id: int | None = None


class CallOut(BaseModel):
    id: int
    ani: str
    dnis: str
    queue: str | None
    ivr_path: str | None
    agent_id: int | None
    status: str
    call_start: datetime
    call_end: datetime | None
    model_config = {"from_attributes": True}


class CTIEventCreate(BaseModel):
    call_id: int
    event_type: str
    payload: str | None = None


class CTIEventOut(BaseModel):
    id: int
    call_id: int
    event_type: str
    timestamp: datetime
    payload: str | None
    model_config = {"from_attributes": True}


class ScreenPopPayload(BaseModel):
    """Sent to the agent console when a call arrives."""
    call_id: int
    ani: str
    customer_id: int | None = None
    customer_name: str | None = None
    account_tier: str | None = None
    open_cases: int = 0
