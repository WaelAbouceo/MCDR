"""CX Intelligent Layer API — GoChat247 operational data.

Exposes call history, case/ticket management, SLA tracking,
escalation logs, QA evaluations, and agent performance.
All endpoints are audit-logged for regulatory compliance.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/cx", tags=["cx-data"])


# ─── Calls ───────────────────────────────────────────────────────

@router.get("/calls/stats")
async def call_statistics(
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.call_stats()


@router.get("/calls/{call_id}")
async def get_call(
    call_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    call = cx_data_service.get_call(call_id)
    if not call:
        raise NotFoundError("Call", call_id)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="call",
        resource_id=call_id, detail=f"ani={call.get('ani')}"
    )
    await db.commit()
    return call


@router.get("/calls/investor/{investor_id}")
async def investor_call_history(
    investor_id: int,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="investor_calls",
        resource_id=investor_id, detail=f"limit={limit}"
    )
    await db.commit()
    return cx_data_service.list_calls_for_investor(investor_id, limit)


@router.get("/calls/agent/{agent_id}")
async def agent_call_history(
    agent_id: int,
    limit: int = Query(default=50, le=200),
    _: User = Depends(RequirePermission(Resource.CALL, Action.READ)),
):
    return cx_data_service.list_calls_for_agent(agent_id, limit)


# ─── Cases ───────────────────────────────────────────────────────

@router.get("/cases/stats")
async def case_statistics(
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.case_stats()


@router.get("/cases/search")
async def search_cases(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    investor_id: int | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.search_cases(
        status=status, priority=priority, category=category,
        investor_id=investor_id, limit=limit, offset=offset,
    )


@router.get("/cases/{case_id}")
async def get_case(
    case_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    case = cx_data_service.get_case(case_id)
    if not case:
        raise NotFoundError("Case", case_id)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="case",
        resource_id=case_id, detail=f"investor_id={case.get('investor_id')}"
    )
    await db.commit()
    return case


@router.get("/cases/number/{case_number}")
async def get_case_by_number(
    case_number: str,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    case = cx_data_service.get_case_by_number(case_number)
    if not case:
        raise NotFoundError("Case", case_number)
    return case


@router.get("/cases/investor/{investor_id}")
async def investor_case_history(
    investor_id: int,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="investor_cases",
        resource_id=investor_id, detail=f"limit={limit}"
    )
    await db.commit()
    return cx_data_service.list_cases_for_investor(investor_id, limit)


@router.get("/cases/agent/{agent_id}")
async def agent_case_queue(
    agent_id: int,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.list_cases_for_agent(agent_id, status, limit)


# ─── SLA ─────────────────────────────────────────────────────────

@router.get("/sla/stats")
async def sla_statistics(
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.sla_stats()


@router.get("/sla/breaches/{case_id}")
async def case_sla_breaches(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.SLA, Action.READ)),
):
    return cx_data_service.get_sla_breaches(case_id)


# ─── Escalations ────────────────────────────────────────────────

@router.get("/escalations/{case_id}")
async def case_escalations(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.ESCALATION, Action.READ)),
):
    return cx_data_service.get_escalations(case_id)


# ─── QA ──────────────────────────────────────────────────────────

@router.get("/qa/leaderboard")
async def qa_leaderboard(
    limit: int = Query(default=20, le=60),
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    return cx_data_service.qa_leaderboard(limit)


@router.get("/qa/agent/{agent_id}")
async def agent_qa_summary(
    agent_id: int,
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    return cx_data_service.agent_qa_summary(agent_id)


@router.get("/qa/case/{case_id}")
async def case_qa_evaluations(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    return cx_data_service.get_qa_evaluations(case_id)


# ─── Agent Performance ──────────────────────────────────────────

@router.get("/agents/{agent_id}/stats")
async def agent_stats(
    agent_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.agent_stats(agent_id)


@router.get("/agents/{agent_id}/performance")
async def agent_performance(
    agent_id: int,
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.agent_performance(agent_id)
