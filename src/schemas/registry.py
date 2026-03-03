from pydantic import BaseModel


class InvestorOut(BaseModel):
    investor_id: int
    investor_code: str
    full_name: str
    national_id: str | None = None
    investor_type: str
    account_status: str
    created_at: str


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
    last_updated: str
    isin: str
    ticker: str
    company_name: str
    sector: str


class PortfolioSummary(BaseModel):
    positions: int
    total_shares: int
    total_value: float
    sectors: int


class AppUserOut(BaseModel):
    app_user_id: int
    investor_id: int
    username: str
    mobile: str
    email: str
    otp_verified: int
    status: str
    last_login: str | None = None
    created_at: str


class InvestorFullProfile(BaseModel):
    investor_id: int
    investor_code: str
    full_name: str
    national_id: str | None = None
    investor_type: str
    account_status: str
    created_at: str
    app_user: AppUserOut | None = None
    portfolio: PortfolioSummary | None = None
