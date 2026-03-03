from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource: str
    resource_id: int | None
    detail: str | None
    ip_address: str | None
    timestamp: datetime
    model_config = {"from_attributes": True}


class AuditQuery(BaseModel):
    user_id: int | None = None
    resource: str | None = None
    action: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    limit: int = 100
    offset: int = 0
