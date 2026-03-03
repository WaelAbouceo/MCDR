from datetime import datetime

from pydantic import BaseModel


class CustomerProfileOut(BaseModel):
    id: int
    phone_number: str
    name: str
    account_number: str
    account_tier: str
    created_at: datetime
    model_config = {"from_attributes": True}
