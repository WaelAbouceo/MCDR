from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.services import audit_service, cx_data_service

router = APIRouter(prefix="/escalations", tags=["escalations"])


class EscalateBody(BaseModel):
    case_id: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


@router.post("", status_code=201)
async def escalate_case(
    body: EscalateBody,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.ESCALATION, Action.ESCALATE)),
):
    existing = cx_data_service.get_case(body.case_id)
    if not existing:
        raise NotFoundError("Case", body.case_id)

    if existing.get("status") == "escalated":
        from src.core.exceptions import ConflictError
        raise ConflictError("Case is already escalated")

    if user.role and user.role.name == "agent" and existing.get("agent_id") != user.id:
        raise ForbiddenError("Agents can only escalate their own cases")

    result = cx_data_service.create_escalation(
        body.case_id,
        from_agent_id=user.id,
        reason=body.reason,
    )
    await audit_service.log_action(
        db, user_id=user.id, action="escalate", resource="case",
        resource_id=body.case_id,
        detail=f"reason={body.reason[:200]}"
    )
    await db.commit()
    return result


@router.get("/case/{case_id}")
async def case_escalations(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.ESCALATION, Action.READ)),
):
    return cx_data_service.get_escalations(case_id)
