import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class Tier(str, enum.Enum):
    TIER1 = "tier1"
    TIER2 = "tier2"


RolePermission = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    field_mask_config: Mapped[str | None] = mapped_column(String(2000), default=None)

    permissions: Mapped[list["Permission"]] = relationship(secondary=RolePermission, back_populates="roles")
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(50))

    roles: Mapped[list["Role"]] = relationship(secondary=RolePermission, back_populates="permissions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    tier: Mapped[str] = mapped_column(String(20), default="tier1")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    created_at: Mapped[str | None] = mapped_column(String(50), default=None)

    role: Mapped["Role"] = relationship(back_populates="users")
