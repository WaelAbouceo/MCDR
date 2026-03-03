from datetime import datetime

from pydantic import BaseModel


class TaxonomyOut(BaseModel):
    id: int
    category: str
    subcategory: str
    description: str | None
    model_config = {"from_attributes": True}


class CaseCreate(BaseModel):
    call_id: int | None = None
    customer_id: int | None = None
    taxonomy_id: int | None = None
    priority: str = "medium"
    subject: str
    description: str | None = None


class CaseUpdate(BaseModel):
    taxonomy_id: int | None = None
    priority: str | None = None
    status: str | None = None
    subject: str | None = None
    description: str | None = None


class CaseNoteCreate(BaseModel):
    content: str
    is_internal: bool = False


class CaseNoteOut(BaseModel):
    id: int
    case_id: int
    author_id: int
    content: str
    is_internal: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class CaseHistoryOut(BaseModel):
    id: int
    case_id: int
    field_changed: str
    old_value: str | None
    new_value: str | None
    changed_by: int
    changed_at: datetime
    model_config = {"from_attributes": True}


class CaseOut(BaseModel):
    id: int
    call_id: int | None
    customer_id: int | None
    agent_id: int
    taxonomy_id: int | None
    priority: str
    status: str
    subject: str
    description: str | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    sla_policy_id: int | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class CaseDetail(CaseOut):
    notes: list[CaseNoteOut] = []
    history: list[CaseHistoryOut] = []
