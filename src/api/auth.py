import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError
from src.core.permissions import Action, Resource
from src.core.rate_limit import (
    is_locked_out_async,
    record_failure_async,
    record_success_async,
)
from src.core.security import create_access_token, hash_password, verify_password
from src.core.token_store import (
    generate_refresh_token,
    invalidate_family,
    revoke_access_token,
    revoke_all_user_tokens,
    store_refresh_token,
    validate_refresh_token,
)
from src.config import get_settings
from src.database import get_cx_db
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.schemas.user import LoginRequest, Token, UserCreate, UserOut

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


class TooManyAttemptsError(ForbiddenError):
    def __init__(self):
        super().__init__("Too many login attempts. Please wait 10 minutes.")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_cx_db)):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )

    if await is_locked_out_async(f"ip:{ip}") or await is_locked_out_async(f"user:{body.username}"):
        raise TooManyAttemptsError()

    stmt = select(User).options(selectinload(User.role)).where(User.username == body.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        locked = await record_failure_async(ip, body.username)
        if locked:
            raise TooManyAttemptsError()
        raise ForbiddenError("Invalid credentials")

    if not int(user.is_active):
        raise ForbiddenError("Account disabled")

    await record_success_async(ip, body.username)

    family_id = uuid.uuid4().hex[:12]
    access_token = create_access_token({"sub": str(user.id), "role": user.role.name})
    refresh_token = generate_refresh_token()
    await store_refresh_token(refresh_token, user.id, family_id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_cx_db)):
    """Exchange a valid refresh token for a new access + refresh token pair (rotation)."""
    data = await validate_refresh_token(body.refresh_token)
    if not data:
        raise ForbiddenError("Invalid or expired refresh token")

    user_id = int(data["user_id"])
    family_id = data.get("family_id", "")

    stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not int(user.is_active):
        await invalidate_family(user_id, family_id)
        raise ForbiddenError("User inactive or not found")

    new_access = create_access_token({"sub": str(user.id), "role": user.role.name})
    new_refresh = generate_refresh_token()
    await store_refresh_token(new_refresh, user.id, family_id)

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    user: User = Depends(get_current_user),
):
    """Revoke the current session. Optionally pass refresh_token to revoke it too."""
    if body.refresh_token:
        await validate_refresh_token(body.refresh_token)

    return {"message": "Logged out successfully"}


@router.post("/logout/all")
async def logout_all(user: User = Depends(get_current_user)):
    """Revoke all refresh tokens for the current user (all devices)."""
    count = await revoke_all_user_tokens(user.id)
    return {"message": f"Revoked {count} sessions"}


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.USER, Action.CREATE)),
):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        from src.core.exceptions import ConflictError
        raise ConflictError(f"Username '{body.username}' already taken")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        tier=body.tier,
        role_id=body.role_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user
