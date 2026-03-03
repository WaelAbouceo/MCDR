from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseTaxonomy(Base):
    __tablename__ = "case_taxonomy"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    subcategory: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int | None] = mapped_column(ForeignKey("calls.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    taxonomy_id: Mapped[int | None] = mapped_column(ForeignKey("case_taxonomy.id"))

    priority: Mapped[CasePriority] = mapped_column(Enum(CasePriority), default=CasePriority.MEDIUM)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.OPEN, index=True)
    subject: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)

    sla_policy_id: Mapped[int | None] = mapped_column(ForeignKey("sla_policies.id"))
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    agent: Mapped[User] = relationship("User", foreign_keys=[agent_id])
    taxonomy: Mapped[CaseTaxonomy | None] = relationship()
    notes: Mapped[list[CaseNote]] = relationship(back_populates="case", order_by="CaseNote.created_at")
    history: Mapped[list[CaseHistory]] = relationship(back_populates="case", order_by="CaseHistory.changed_at.desc()")


class CaseNote(Base):
    __tablename__ = "case_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    case: Mapped[Case] = relationship(back_populates="notes")
    author: Mapped[User] = relationship("User", foreign_keys=[author_id])


class CaseHistory(Base):
    __tablename__ = "case_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    field_changed: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(String(500))
    new_value: Mapped[str | None] = mapped_column(String(500))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    case: Mapped[Case] = relationship(back_populates="history")
