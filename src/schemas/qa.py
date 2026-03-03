from datetime import datetime

from pydantic import BaseModel


class QAScorecardCreate(BaseModel):
    name: str
    criteria: str
    max_score: int = 100


class QAScorecardOut(BaseModel):
    id: int
    name: str
    criteria: str
    max_score: int
    is_active: bool
    model_config = {"from_attributes": True}


class QAEvaluationCreate(BaseModel):
    case_id: int
    call_id: int | None = None
    agent_id: int
    scorecard_id: int
    scores: str
    total_score: float
    feedback: str | None = None


class QAEvaluationOut(BaseModel):
    id: int
    case_id: int
    call_id: int | None
    evaluator_id: int
    agent_id: int
    scorecard_id: int
    scores: str
    total_score: float
    feedback: str | None
    evaluated_at: datetime
    model_config = {"from_attributes": True}
