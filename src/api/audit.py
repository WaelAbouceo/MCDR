from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.schemas.audit import AuditLogOut
from src.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


class PageViewBody(BaseModel):
    page: str
    referrer: str | None = None


@router.post("/page-view", status_code=204)
async def log_page_view(
    body: PageViewBody,
    request: Request,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(get_current_user),
):
    """Log a frontend page navigation for regulatory traceability."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    detail = f"referrer={body.referrer}" if body.referrer else None
    await audit_service.log_action(
        db, user_id=user.id, action="page_view", resource=body.page,
        detail=detail, ip_address=ip,
    )
    await db.commit()


@router.get("/logs", response_model=list[AuditLogOut])
async def query_audit_logs(
    user_id: int | None = None,
    resource: str | None = None,
    action: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.AUDIT, Action.READ)),
):
    return await audit_service.query_logs(
        db,
        user_id=user_id,
        resource=resource,
        action=action,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
