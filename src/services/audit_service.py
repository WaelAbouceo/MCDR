from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    resource: str,
    resource_id: int | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry


async def query_logs(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    resource: str | None = None,
    action: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if from_date:
        stmt = stmt.where(AuditLog.timestamp >= from_date)
    if to_date:
        stmt = stmt.where(AuditLog.timestamp <= to_date)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
