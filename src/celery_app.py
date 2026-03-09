"""Celery app for background and periodic tasks (e.g. SLA auto-escalation)."""

from celery import Celery
from src.config import get_settings

settings = get_settings()

app = Celery(
    "mcdr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks.sla_tasks"],
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "sla-check-every-2min": {
            "task": "src.tasks.sla_tasks.check_sla_breaches",
            "schedule": 120.0,
        },
    },
)
