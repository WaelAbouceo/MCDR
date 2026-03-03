from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class QAScorecard(Base):
    __tablename__ = "qa_scorecards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    criteria: Mapped[str] = mapped_column(Text)
    max_score: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QAEvaluation(Base):
    __tablename__ = "qa_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    call_id: Mapped[int | None] = mapped_column(ForeignKey("calls.id"))
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scorecard_id: Mapped[int] = mapped_column(ForeignKey("qa_scorecards.id"))
    scores: Mapped[str] = mapped_column(Text)
    total_score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
