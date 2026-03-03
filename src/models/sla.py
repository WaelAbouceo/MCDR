import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class BreachType(str, enum.Enum):
    FIRST_RESPONSE = "first_response"
    RESOLUTION = "resolution"


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    first_response_minutes: Mapped[int] = mapped_column(Integer)
    resolution_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SLABreach(Base):
    __tablename__ = "sla_breaches"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("sla_policies.id"))
    breach_type: Mapped[BreachType] = mapped_column(Enum(BreachType))
    breached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
