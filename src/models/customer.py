from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import CustomerBase


class CustomerProfile(CustomerBase):
    """Lives in the separate customer-db (read-only zone)."""

    __tablename__ = "customer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    account_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    account_tier: Mapped[str] = mapped_column(String(20), default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
