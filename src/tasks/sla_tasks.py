"""Celery tasks for SLA breach detection and auto-escalation."""

from src.celery_app import app
from src.services import cx_data_service


@app.task(name="src.tasks.sla_tasks.check_sla_breaches")
def check_sla_breaches() -> dict:
    """Periodic task: check open/in_progress cases for SLA breach and auto-escalate if needed."""
    case_ids = cx_data_service.list_case_ids_for_sla_check(limit=200)
    for case_id in case_ids:
        try:
            cx_data_service.check_sla_and_auto_escalate(case_id)
        except Exception:
            continue
    return {"checked": len(case_ids)}
