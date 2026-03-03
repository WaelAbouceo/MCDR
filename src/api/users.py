from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User, Role
from src.schemas.user import UserOut, UserUpdate, RoleOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.USER, Action.READ)),
):
    stmt = select(User).options(selectinload(User.role)).order_by(User.username)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.USER, Action.READ)),
):
    result = await db.execute(select(Role).order_by(Role.name))
    return result.scalars().all()


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_cx_db),
    _: User = Depends(RequirePermission(Resource.USER, Action.UPDATE)),
):
    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("User", user_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user, attribute_names=["role"])
    return user
