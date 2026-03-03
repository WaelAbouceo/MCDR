from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    trigger_condition: Mapped[str] = mapped_column(String(500))
    from_tier: Mapped[str] = mapped_column(String(20))
    to_tier: Mapped[str] = mapped_column(String(20))
    alert_channels: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("escalation_rules.id"))
    from_agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    from_tier: Mapped[str] = mapped_column(String(20))
    to_tier: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
