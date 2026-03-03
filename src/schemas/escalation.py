from datetime import datetime

from pydantic import BaseModel


class EscalationRuleOut(BaseModel):
    id: int
    name: str
    trigger_condition: str
    from_tier: str
    to_tier: str
    alert_channels: str | None
    is_active: bool
    model_config = {"from_attributes": True}


class EscalationCreate(BaseModel):
    case_id: int
    to_agent_id: int | None = None
    to_tier: str = "tier2"
    reason: str


class EscalationOut(BaseModel):
    id: int
    case_id: int
    rule_id: int | None
    from_agent_id: int
    to_agent_id: int | None
    from_tier: str
    to_tier: str
    reason: str
    escalated_at: datetime
    model_config = {"from_attributes": True}
