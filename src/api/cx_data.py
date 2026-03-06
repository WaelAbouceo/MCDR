"""CX Intelligent Layer API — GoChat247 operational data.

Exposes call history, case/ticket management, SLA tracking,
escalation logs, QA evaluations, and agent performance.
All endpoints are audit-logged for regulatory compliance.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User


class PresenceBody(BaseModel):
    status: Literal["available", "on_break", "acw", "in_call", "training", "offline"]
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/cx", tags=["cx-data"])


# ─── Taxonomy ────────────────────────────────────────────────────

@router.get("/taxonomy")
async def list_taxonomy(
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.list_taxonomy()


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
    q: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.search_cases(
        status=status, priority=priority, category=category,
        investor_id=investor_id, q=q, limit=limit, offset=offset,
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


# ─── Reports (SQLite-based for POC) ─────────────────────────────

@router.get("/reports/overview")
async def report_overview(
    days: int = Query(default=7, ge=1, le=90),
    _: User = Depends(RequirePermission(Resource.REPORT, Action.READ)),
):
    return cx_data_service.report_overview(days)


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


# ─── Knowledge Base ──────────────────────────────────────────────

@router.get("/kb")
async def list_kb_articles(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.list_kb_articles(category=category, search=search)


@router.get("/kb/categories")
async def kb_categories(
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    return cx_data_service.kb_categories()


@router.get("/kb/{article_id}")
async def get_kb_article(
    article_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    article = cx_data_service.get_kb_article(article_id)
    if not article:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Article", article_id)
    return article


# ─── Agent Presence ─────────────────────────────────────────────

@router.get("/presence")
async def list_presence(
    _: User = Depends(RequirePermission(Resource.USER, Action.READ)),
):
    return cx_data_service.list_agent_presence()


@router.get("/presence/summary")
async def presence_summary(
    _: User = Depends(RequirePermission(Resource.USER, Action.READ)),
):
    return cx_data_service.presence_summary()


@router.get("/presence/{agent_id}")
async def get_presence(
    agent_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    p = cx_data_service.get_agent_presence(agent_id)
    if not p:
        return {"agent_id": agent_id, "status": "offline", "updated_at": None}
    return p


@router.put("/presence/{agent_id}")
async def set_presence(
    agent_id: int,
    body: PresenceBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    if user.id != agent_id and user.role and user.role.name not in ("team_lead", "supervisor", "admin"):
        from src.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only change your own presence status")

    try:
        result = cx_data_service.set_agent_presence(agent_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await audit_service.log_action(
        db, user_id=user.id, action="set_presence", resource="agent",
        resource_id=agent_id, detail=f"status={body.status}"
    )
    await db.commit()
    return result
