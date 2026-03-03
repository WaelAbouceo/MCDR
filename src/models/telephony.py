from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class CallStatus(str, enum.Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    TRANSFERRED = "transferred"


class CTIEventType(str, enum.Enum):
    CALL_OFFERED = "call_offered"
    CALL_ANSWERED = "call_answered"
    CALL_HELD = "call_held"
    CALL_RESUMED = "call_resumed"
    CALL_ENDED = "call_ended"
    CALL_TRANSFERRED = "call_transferred"
    AGENT_READY = "agent_ready"
    AGENT_NOT_READY = "agent_not_ready"


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    ani: Mapped[str] = mapped_column(String(20), index=True)
    dnis: Mapped[str] = mapped_column(String(20))
    queue: Mapped[str | None] = mapped_column(String(100))
    ivr_path: Mapped[str | None] = mapped_column(String(500))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[CallStatus] = mapped_column(Enum(CallStatus), default=CallStatus.RINGING)
    call_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    call_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped[User] = relationship("User", foreign_keys=[agent_id])
    cti_events: Mapped[list["CTIEvent"]] = relationship(back_populates="call")


class CTIEvent(Base):
    __tablename__ = "cti_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[CTIEventType] = mapped_column(Enum(CTIEventType))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payload: Mapped[str | None] = mapped_column(Text)

    call: Mapped["Call"] = relationship(back_populates="cti_events")
