from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError
from src.core.permissions import Action, Resource
from src.core.security import decode_access_token
from src.database import get_cx_db
from src.models.user import User
from src.services.rbac_service import has_permission

bearer_scheme = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_cx_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise ForbiddenError("Invalid or expired token")
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise ForbiddenError("Invalid token payload")

    stmt = select(User).options(selectinload(User.role)).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not int(user.is_active):
        raise ForbiddenError("User inactive or not found")

    request.state.user_id = user.id
    request.state.username = user.username
    request.state.role = user.role.name if user.role else None
    return user


class RequirePermission:
    """FastAPI dependency that checks RBAC permissions."""

    def __init__(self, resource: Resource, action: Action):
        self.resource = resource
        self.action = action

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role.name, self.resource, self.action):
            raise ForbiddenError(f"No {self.action} access on {self.resource}")
        return user
