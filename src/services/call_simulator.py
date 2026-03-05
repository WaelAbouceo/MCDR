"""Simulates an incoming call from Cisco IVR/ACD.

Replicates the real CTI flow:
  1. Cisco IVR receives call → captures ANI
  2. ACD routes to queue → assigns agent
  3. CTI adapter fires call_offered event
  4. System resolves ANI → investor profile
  5. Screen-pop assembled → pushed to agent console
"""

import sqlite3
import random
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Generator

from src.config import get_settings

settings = get_settings()

_incoming_calls: dict[int, dict] = {}
_lock = threading.Lock()


def push_incoming_call(agent_id: int, call_payload: dict) -> None:
    with _lock:
        _incoming_calls[agent_id] = call_payload


def poll_incoming_call(agent_id: int) -> dict | None:
    with _lock:
        return _incoming_calls.get(agent_id)


def accept_incoming_call(agent_id: int) -> dict | None:
    with _lock:
        return _incoming_calls.pop(agent_id, None)


def dismiss_incoming_call(agent_id: int) -> None:
    with _lock:
        _incoming_calls.pop(agent_id, None)


@contextmanager
def _ro_conn(path: str) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def simulate_incoming_call(
    ani: str | None = None,
    queue: str | None = None,
    target_agent_id: int | None = None,
    call_reason_id: int | None = None,
) -> dict:
    """Simulate a complete incoming call event from Cisco CTI.

    If no ANI is provided, picks a random active mobile app user.
    If target_agent_id is specified, the call is routed to that agent.
    Returns the full event payload as it would flow through the system.
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # ── Step 1: Resolve caller ANI ───────────────────────────────
    if ani:
        caller = _lookup_by_ani(ani)
    else:
        caller = _pick_random_caller()
        ani = caller["mobile"] if caller else "+20100000000"

    ivr_selections = random.choice(["1>2", "1>3", "2>1", "3>1", "1>1>2", "2>2", "1"])
    dnis = "+20221234567"
    call_queue = queue or random.choice(["billing", "technical", "general", "priority", "retention"])

    # ── Step 2: Cisco IVR / ACD event ────────────────────────────
    ivr_event = {
        "source": "cisco_ivr",
        "event": "call_received",
        "timestamp": timestamp,
        "ani": ani,
        "dnis": dnis,
        "ivr_path": ivr_selections,
        "queue_selected": call_queue,
    }

    # ── Step 3: Agent assignment (ACD) ───────────────────────────
    agent = _get_agent_by_id(target_agent_id) if target_agent_id else _pick_available_agent(call_queue)

    acd_event = {
        "source": "cisco_acd",
        "event": "call_routed",
        "timestamp": timestamp,
        "queue": call_queue,
        "agent_id": agent["user_id"],
        "agent_name": agent["full_name"],
        "wait_seconds": random.randint(5, 60),
    }

    # ── Step 4: CTI call_offered event ───────────────────────────
    call_id = random.randint(100000, 999999)

    cti_event = {
        "source": "cti_adapter",
        "event": "call_offered",
        "timestamp": timestamp,
        "call_id": call_id,
        "ani": ani,
        "dnis": dnis,
        "agent_id": agent["user_id"],
        "queue": call_queue,
        "ivr_path": ivr_selections,
    }

    # ── Step 5: ANI Resolution → Customer lookup ─────────────────
    ani_resolution = {"ani": ani, "matched": False}
    investor = None
    app_user = None
    portfolio = None
    case_history = []
    call_history = []

    if caller:
        ani_resolution["matched"] = True
        ani_resolution["investor_id"] = caller["investor_id"]

        investor = _get_investor(caller["investor_id"])
        app_user = dict(caller)
        portfolio = _get_portfolio(caller["investor_id"])
        case_history = _get_recent_cases(caller["investor_id"])
        call_history = _get_recent_calls(caller["investor_id"])

    # ── Step 5b: Resolve call reason taxonomy ──────────────────────
    call_reason = None
    if call_reason_id:
        call_reason = _get_taxonomy(call_reason_id)

    # ── Step 6: Assemble screen-pop ──────────────────────────────
    screen_pop = {
        "call_id": call_id,
        "ani": ani,
        "queue": call_queue,
        "call_reason": call_reason,
        "agent": {
            "id": agent["user_id"],
            "name": agent["full_name"],
            "role": agent["role"],
            "tier": agent["tier"],
        },
        "customer_identified": ani_resolution["matched"],
        "investor": investor,
        "app_user": _sanitize_app_user(app_user) if app_user else None,
        "portfolio_summary": portfolio,
        "open_cases": [c for c in case_history if c["status"] not in ("resolved", "closed")],
        "recent_cases": case_history[:5],
        "recent_calls": call_history[:5],
        "risk_flags": _compute_risk_flags(investor, app_user, case_history),
    }

    result = {
        "simulation": "cisco_incoming_call",
        "timestamp": timestamp,
        "events": [ivr_event, acd_event, cti_event],
        "ani_resolution": ani_resolution,
        "screen_pop": screen_pop,
    }

    push_incoming_call(agent["user_id"], result)

    return result


def _get_taxonomy(taxonomy_id: int) -> dict | None:
    with _ro_conn(settings.mcdr_cx_db_path) as conn:
        row = conn.execute(
            "SELECT taxonomy_id, category, subcategory, description "
            "FROM case_taxonomy WHERE taxonomy_id = ?",
            (taxonomy_id,),
        ).fetchone()
        return dict(row) if row else None


def _pick_random_caller() -> dict | None:
    with _ro_conn(settings.mcdr_mobile_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM app_users WHERE status='Active' ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def _lookup_by_ani(ani: str) -> dict | None:
    with _ro_conn(settings.mcdr_mobile_db_path) as conn:
        row = conn.execute("SELECT * FROM app_users WHERE mobile = ?", (ani,)).fetchone()
        return dict(row) if row else None


def _get_investor(investor_id: int) -> dict | None:
    with _ro_conn(settings.mcdr_core_db_path) as conn:
        row = conn.execute("SELECT * FROM investors WHERE investor_id = ?", (investor_id,)).fetchone()
        return dict(row) if row else None


def _get_portfolio(investor_id: int) -> dict | None:
    with _ro_conn(settings.mcdr_core_db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS positions, SUM(quantity) AS total_shares, "
            "ROUND(SUM(quantity * avg_price), 2) AS total_value, "
            "COUNT(DISTINCT s.sector) AS sectors "
            "FROM holdings h JOIN securities s ON h.security_id = s.security_id "
            "WHERE h.investor_id = ?",
            (investor_id,),
        ).fetchone()
        return dict(row) if row else None


def _get_recent_cases(investor_id: int) -> list[dict]:
    with _ro_conn(settings.mcdr_cx_db_path) as conn:
        rows = conn.execute(
            "SELECT c.case_id, c.case_number, c.priority, c.status, c.subject, "
            "t.category, t.subcategory, c.created_at "
            "FROM cases c JOIN case_taxonomy t ON c.taxonomy_id = t.taxonomy_id "
            "WHERE c.investor_id = ? ORDER BY c.created_at DESC LIMIT 10",
            (investor_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _get_recent_calls(investor_id: int) -> list[dict]:
    with _ro_conn(settings.mcdr_cx_db_path) as conn:
        rows = conn.execute(
            "SELECT call_id, queue, status, duration_seconds, wait_seconds, call_start "
            "FROM calls WHERE investor_id = ? ORDER BY call_start DESC LIMIT 10",
            (investor_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _pick_available_agent(queue: str) -> dict:
    with _ro_conn(settings.mcdr_cx_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cx_users WHERE role IN ('agent', 'senior_agent') AND is_active=1 ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        if not row:
            raise ValueError("No available agents in the system")
        return dict(row)


def _get_agent_by_id(agent_id: int) -> dict:
    with _ro_conn(settings.mcdr_cx_db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cx_users WHERE user_id = ?", (agent_id,)
        ).fetchone()
        return dict(row) if row else _pick_available_agent("general")


def _sanitize_app_user(app_user: dict) -> dict:
    """Strip sensitive fields before sending to agent console."""
    return {
        "investor_id": app_user.get("investor_id"),
        "username": app_user.get("username"),
        "mobile": app_user.get("mobile"),
        "email": app_user.get("email"),
        "status": app_user.get("status"),
        "otp_verified": bool(app_user.get("otp_verified", False)),
        "last_login": app_user.get("last_login"),
    }


def _compute_risk_flags(investor: dict | None, app_user: dict | None, cases: list[dict]) -> list[str]:
    flags = []
    if not investor:
        flags.append("UNIDENTIFIED_CALLER")
        return flags
    if investor.get("account_status") == "Suspended":
        flags.append("ACCOUNT_SUSPENDED")
    if investor.get("account_status") == "Dormant":
        flags.append("DORMANT_ACCOUNT")
    if investor.get("investor_type") == "Institutional":
        flags.append("INSTITUTIONAL_CLIENT")
    if app_user and app_user.get("status") == "Locked":
        flags.append("APP_ACCOUNT_LOCKED")
    if app_user and not app_user.get("otp_verified"):
        flags.append("OTP_NOT_VERIFIED")

    open_cases = [c for c in cases if c["status"] not in ("resolved", "closed")]
    if len(open_cases) >= 3:
        flags.append("MULTIPLE_OPEN_CASES")
    critical = [c for c in open_cases if c["priority"] == "critical"]
    if critical:
        flags.append("HAS_CRITICAL_CASE")
    repeat = len(cases) >= 5
    if repeat:
        flags.append("FREQUENT_CALLER")

    return flags
