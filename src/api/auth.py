from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError
from src.core.permissions import Action, Resource
from src.core.rate_limit import is_locked_out, record_failure, record_success
from src.core.security import create_access_token, hash_password, verify_password
from src.config import get_settings
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.models.user import User
from src.schemas.user import LoginRequest, Token, UserCreate, UserOut

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


class TooManyAttemptsError(ForbiddenError):
    def __init__(self):
        super().__init__("Too many login attempts. Please wait 10 minutes.")


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_cx_db)):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )

    if is_locked_out(f"ip:{ip}") or is_locked_out(f"user:{body.username}"):
        raise TooManyAttemptsError()

    stmt = select(User).options(selectinload(User.role)).where(User.username == body.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        locked = record_failure(ip, body.username)
        if locked:
            raise TooManyAttemptsError()
        raise ForbiddenError("Invalid credentials")

    if not int(user.is_active):
        raise ForbiddenError("Account disabled")

    record_success(ip, body.username)
    token = create_access_token({"sub": str(user.id), "role": user.role.name})
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


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
