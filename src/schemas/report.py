from datetime import datetime

from pydantic import BaseModel


class DashboardFilters(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None
    agent_id: int | None = None
    priority: str | None = None
    status: str | None = None


class CaseVolumeRow(BaseModel):
    date: str
    total: int
    open: int
    resolved: int
    escalated: int


class SLAComplianceRow(BaseModel):
    policy_name: str
    total_cases: int
    frt_met: int
    frt_breached: int
    rt_met: int
    rt_breached: int
    compliance_pct: float


class AgentPerformanceRow(BaseModel):
    agent_id: int
    agent_name: str
    cases_handled: int
    avg_resolution_minutes: float | None
    sla_compliance_pct: float
    avg_qa_score: float | None


class OperationalDashboard(BaseModel):
    period_start: datetime
    period_end: datetime
    case_volume: list[CaseVolumeRow]
    sla_compliance: list[SLAComplianceRow]
    agent_performance: list[AgentPerformanceRow]
