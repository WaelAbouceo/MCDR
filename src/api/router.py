from fastapi import APIRouter

from src.api import (
    ai,
    approvals, audit, auth, cases, customers, cx_data, escalations,
    outbound, qa, registry, reports, simulate, sla, telephony, users,
    verification,
)

_sub_routers = [
    auth.router,
    users.router,
    telephony.router,
    cases.router,
    escalations.router,
    sla.router,
    customers.router,
    registry.router,
    qa.router,
    cx_data.router,
    simulate.router,
    ai.router,
    audit.router,
    reports.router,
    outbound.router,
    verification.router,
    approvals.router,
]

api_router = APIRouter(prefix="/api/v1")
for r in _sub_routers:
    api_router.include_router(r)

legacy_router = APIRouter(prefix="/api")
for r in _sub_routers:
    legacy_router.include_router(r)
