from datetime import datetime

from pydantic import BaseModel


class SLAPolicyCreate(BaseModel):
    name: str
    priority: str
    first_response_minutes: int
    resolution_minutes: int


class SLAPolicyOut(BaseModel):
    id: int
    name: str
    priority: str
    first_response_minutes: int
    resolution_minutes: int
    is_active: bool
    model_config = {"from_attributes": True}


class SLABreachOut(BaseModel):
    id: int
    case_id: int
    policy_id: int
    breach_type: str
    breached_at: datetime
    model_config = {"from_attributes": True}
