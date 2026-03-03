from fastapi import APIRouter

from src.api import audit, auth, cases, customers, cx_data, escalations, qa, registry, reports, simulate, sla, telephony, users

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(telephony.router)
api_router.include_router(cases.router)
api_router.include_router(escalations.router)
api_router.include_router(sla.router)
api_router.include_router(customers.router)
api_router.include_router(registry.router)
api_router.include_router(qa.router)
api_router.include_router(cx_data.router)
api_router.include_router(simulate.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
