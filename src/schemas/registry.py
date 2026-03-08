from datetime import datetime

from pydantic import BaseModel, field_serializer


def _dt_to_str(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return v


class InvestorOut(BaseModel):
    investor_id: int
    investor_code: str
    full_name: str
    national_id: str | None = None
    investor_type: str
    account_status: str
    created_at: str | datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return _dt_to_str(v)


class SecurityOut(BaseModel):
    security_id: int
    isin: str
    ticker: str
    company_name: str
    sector: str


class HoldingOut(BaseModel):
    holding_id: int
    investor_id: int
    security_id: int
    quantity: int
    avg_price: float
    last_updated: str | datetime
    isin: str
    ticker: str
    company_name: str
    sector: str

    @field_serializer("last_updated")
    def serialize_last_updated(self, v):
        return _dt_to_str(v)


class PortfolioSummary(BaseModel):
    positions: int
    total_shares: int | None = 0
    total_value: float | None = 0.0
    sectors: int


class AppUserOut(BaseModel):
    app_user_id: int
    investor_id: int
    username: str
    mobile: str
    email: str
    otp_verified: int
    status: str
    last_login: str | datetime | None = None
    created_at: str | datetime

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return _dt_to_str(v)

    @field_serializer("last_login")
    def serialize_last_login(self, v):
        return _dt_to_str(v)


class InvestorFullProfile(BaseModel):
    investor_id: int
    investor_code: str
    full_name: str
    national_id: str | None = None
    investor_type: str
    account_status: str
    created_at: str | datetime
    app_user: AppUserOut | None = None
    portfolio: PortfolioSummary | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, v):
        return _dt_to_str(v)
