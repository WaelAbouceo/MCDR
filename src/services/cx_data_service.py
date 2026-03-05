"""CX Intelligent Layer data service.

Reads and writes GoChat247 operational data: calls, cases, notes,
escalations, SLA breaches, QA evaluations — all linked to
MCDR investors.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from src.config import get_settings

logger = logging.getLogger("mcdr.cx_data")

settings = get_settings()


@contextmanager
def _cx_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.mcdr_cx_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute(f"ATTACH DATABASE '{settings.mcdr_core_db_path}' AS core")
    try:
        yield conn
    finally:
        conn.close()


# ─── Taxonomy ────────────────────────────────────────────────────

def list_taxonomy() -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT taxonomy_id, category, subcategory, description "
            "FROM case_taxonomy WHERE is_active = 1 ORDER BY category, subcategory"
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Calls ───────────────────────────────────────────────────────

def get_call(call_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute("SELECT * FROM calls WHERE call_id = ?", (call_id,)).fetchone()
        return dict(row) if row else None


def list_calls_for_investor(investor_id: int, limit: int = 50) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM calls WHERE investor_id = ? ORDER BY call_start DESC LIMIT ?",
            (investor_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def list_calls_for_agent(agent_id: int, limit: int = 50) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM calls WHERE agent_id = ? ORDER BY call_start DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def call_stats() -> dict:
    with _cx_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM calls GROUP BY status"
        ).fetchall()
        avg_dur = conn.execute(
            "SELECT ROUND(AVG(duration_seconds)) FROM calls WHERE status='completed'"
        ).fetchone()[0]
        avg_wait = conn.execute(
            "SELECT ROUND(AVG(wait_seconds)) FROM calls"
        ).fetchone()[0]
        return {
            "total_calls": total,
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "avg_duration_seconds": avg_dur,
            "avg_wait_seconds": avg_wait,
        }


# ─── Cases ───────────────────────────────────────────────────────

def get_case(case_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT c.*, t.category, t.subcategory, "
            "u.full_name AS agent_name, "
            "inv.full_name AS investor_name, inv.investor_code "
            "FROM cases c "
            "LEFT JOIN case_taxonomy t ON c.taxonomy_id = t.taxonomy_id "
            "LEFT JOIN cx_users u ON c.agent_id = u.user_id "
            "LEFT JOIN core.investors inv ON c.investor_id = inv.investor_id "
            "WHERE c.case_id = ?",
            (case_id,),
        ).fetchone()
        if not row:
            return None
        case = dict(row)
        case["notes"] = get_case_notes(case_id)
        case["history"] = get_case_history(case_id)
        if case.get("call_id"):
            call = get_call(case["call_id"])
            case["call"] = call
        return case


def get_case_by_number(case_number: str) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute("SELECT * FROM cases WHERE case_number = ?", (case_number,)).fetchone()
        if not row:
            return None
        case = dict(row)
        case["notes"] = get_case_notes(case["case_id"])
        case["history"] = get_case_history(case["case_id"])
        return case


_CASE_SELECT = (
    "SELECT c.*, t.category, t.subcategory, "
    "u.full_name AS agent_name, "
    "inv.full_name AS investor_name, inv.investor_code "
    "FROM cases c "
    "JOIN case_taxonomy t ON c.taxonomy_id = t.taxonomy_id "
    "LEFT JOIN cx_users u ON c.agent_id = u.user_id "
    "LEFT JOIN core.investors inv ON c.investor_id = inv.investor_id "
)


def list_cases_for_investor(investor_id: int, limit: int = 50) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            _CASE_SELECT + "WHERE c.investor_id = ? ORDER BY c.created_at DESC LIMIT ?",
            (investor_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def list_cases_for_agent(agent_id: int, status: str | None = None, limit: int = 50) -> list[dict]:
    query = _CASE_SELECT + "WHERE c.agent_id = ?"
    params: list = [agent_id]
    if status:
        query += " AND c.status = ?"
        params.append(status)
    query += " ORDER BY c.created_at DESC LIMIT ?"
    params.append(limit)
    with _cx_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def search_cases(
    *,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    investor_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if status:
        clauses.append("c.status = ?")
        params.append(status)
    if priority:
        clauses.append("c.priority = ?")
        params.append(priority)
    if category:
        clauses.append("t.category = ?")
        params.append(category)
    if investor_id:
        clauses.append("c.investor_id = ?")
        params.append(investor_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = _CASE_SELECT + f"{where} ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _cx_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def case_stats() -> dict:
    with _cx_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM cases GROUP BY status"
        ).fetchall()
        by_priority = conn.execute(
            "SELECT priority, COUNT(*) AS cnt FROM cases GROUP BY priority"
        ).fetchall()
        by_category = conn.execute(
            "SELECT t.category, COUNT(*) AS cnt FROM cases c "
            "JOIN case_taxonomy t ON c.taxonomy_id = t.taxonomy_id "
            "GROUP BY t.category ORDER BY cnt DESC"
        ).fetchall()
        return {
            "total_cases": total,
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "by_priority": {r["priority"]: r["cnt"] for r in by_priority},
            "by_category": {r["category"]: r["cnt"] for r in by_category},
        }


# ─── Notes & History ────────────────────────────────────────────

def get_case_notes(case_id: int) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT n.*, u.full_name AS author_name FROM case_notes n "
            "JOIN cx_users u ON n.author_id = u.user_id "
            "WHERE n.case_id = ? ORDER BY n.created_at",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_case_history(case_id: int) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT h.*, u.full_name AS changed_by_name "
            "FROM case_history h "
            "LEFT JOIN cx_users u ON h.changed_by = u.user_id "
            "WHERE h.case_id = ? ORDER BY h.changed_at",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── SLA ─────────────────────────────────────────────────────────

def get_sla_breaches(case_id: int) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT b.*, p.name AS policy_name FROM sla_breaches b "
            "JOIN sla_policies p ON b.policy_id = p.policy_id "
            "WHERE b.case_id = ?",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def sla_stats() -> dict:
    with _cx_conn() as conn:
        by_type = conn.execute(
            "SELECT b.breach_type, p.name AS policy, COUNT(*) AS cnt "
            "FROM sla_breaches b JOIN sla_policies p ON b.policy_id = p.policy_id "
            "GROUP BY b.breach_type, p.name ORDER BY cnt DESC"
        ).fetchall()
        breach_rate = conn.execute(
            "SELECT c.priority, COUNT(DISTINCT c.case_id) AS total, "
            "COUNT(DISTINCT b.case_id) AS breached "
            "FROM cases c LEFT JOIN sla_breaches b ON c.case_id = b.case_id "
            "GROUP BY c.priority"
        ).fetchall()
        return {
            "by_type_and_policy": [dict(r) for r in by_type],
            "breach_rate_by_priority": [
                {**dict(r), "pct": round(r["breached"] * 100 / max(r["total"], 1), 1)}
                for r in breach_rate
            ],
        }


# ─── Escalations ────────────────────────────────────────────────

def get_escalations(case_id: int) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT e.*, f.full_name AS from_agent_name, t.full_name AS to_agent_name "
            "FROM escalations e "
            "JOIN cx_users f ON e.from_agent_id = f.user_id "
            "JOIN cx_users t ON e.to_agent_id = t.user_id "
            "WHERE e.case_id = ? ORDER BY e.escalated_at DESC",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── QA ──────────────────────────────────────────────────────────

def get_qa_evaluations(case_id: int) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT q.*, u.full_name AS evaluator_name "
            "FROM qa_evaluations q JOIN cx_users u ON q.evaluator_id = u.user_id "
            "WHERE q.case_id = ?",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def agent_qa_summary(agent_id: int) -> dict:
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS evals, ROUND(AVG(total_score),1) AS avg_score, "
            "MIN(total_score) AS min_score, MAX(total_score) AS max_score "
            "FROM qa_evaluations WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        return dict(row) if row else {}


def qa_leaderboard(limit: int = 20) -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT u.user_id, u.full_name, COUNT(*) AS evals, "
            "ROUND(AVG(q.total_score),1) AS avg_score "
            "FROM qa_evaluations q JOIN cx_users u ON q.agent_id = u.user_id "
            "GROUP BY q.agent_id HAVING COUNT(*) >= 5 "
            "ORDER BY avg_score DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Agent Performance ──────────────────────────────────────────

def agent_stats(agent_id: int) -> dict:
    """Quick counts for an agent's dashboard."""
    with _cx_conn() as conn:
        cases = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM cases WHERE agent_id = ? GROUP BY status",
            (agent_id,),
        ).fetchall()
        total_calls = conn.execute(
            "SELECT COUNT(*) FROM calls WHERE agent_id = ?", (agent_id,),
        ).fetchone()[0]
        return {
            "total_cases": sum(r["cnt"] for r in cases),
            "by_status": {r["status"]: r["cnt"] for r in cases},
            "total_calls": total_calls,
        }


def agent_performance(agent_id: int) -> dict:
    with _cx_conn() as conn:
        cases = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status IN ('resolved','closed') THEN 1 ELSE 0 END) AS resolved, "
            "SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) AS escalated "
            "FROM cases WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        calls = conn.execute(
            "SELECT COUNT(*) AS total, ROUND(AVG(duration_seconds)) AS avg_dur "
            "FROM calls WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        qa = conn.execute(
            "SELECT ROUND(AVG(total_score),1) AS avg_qa FROM qa_evaluations WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        breaches = conn.execute(
            "SELECT COUNT(DISTINCT b.case_id) AS cnt FROM sla_breaches b "
            "JOIN cases c ON b.case_id = c.case_id WHERE c.agent_id = ?",
            (agent_id,),
        ).fetchone()
        return {
            "cases": dict(cases),
            "calls": dict(calls),
            "avg_qa_score": qa["avg_qa"],
            "sla_breaches": breaches["cnt"],
        }


# ─── Write Operations ──────────────────────────────────────────

@contextmanager
def _cx_write_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.mcdr_cx_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _insert_and_get_id(conn: sqlite3.Connection, sql: str, params: tuple) -> int:
    """Insert a row and return the auto-generated rowid (concurrency-safe)."""
    cursor = conn.execute(sql, params)
    return cursor.lastrowid


def create_case(
    *,
    agent_id: int,
    investor_id: int | None = None,
    call_id: int | None = None,
    subject: str,
    description: str | None = None,
    priority: str = "medium",
    taxonomy_id: int | None = None,
) -> dict:
    now = _now()
    policy_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    sla_policy_id = policy_map.get(priority, 3)
    if not taxonomy_id:
        taxonomy_id = 1

    with _cx_write_conn() as conn:
        case_id = _insert_and_get_id(conn,
            "INSERT INTO cases (case_number, call_id, investor_id, agent_id, "
            "taxonomy_id, priority, status, subject, description, sla_policy_id, "
            "first_response_at, resolved_at, closed_at, created_at, updated_at, "
            "pending_seconds, pending_since, resolution_code) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("TMP", call_id, investor_id, agent_id,
             taxonomy_id, priority, "open", subject, description, sla_policy_id,
             None, None, None, now, now, 0, None, None),
        )
        case_number = f"CAS-{case_id:06}"
        conn.execute("UPDATE cases SET case_number = ? WHERE case_id = ?", (case_number, case_id))
    return get_case(case_id)


_VALID_TRANSITIONS: dict[str, set[str]] = {
    "open":             {"in_progress", "escalated", "closed"},
    "in_progress":      {"pending_customer", "escalated", "resolved", "closed"},
    "pending_customer": {"in_progress", "escalated", "resolved", "closed"},
    "escalated":        {"in_progress", "resolved", "closed"},
    "resolved":         {"closed", "in_progress"},
    "closed":           set(),
}


def valid_next_statuses(current_status: str) -> list[str]:
    return sorted(_VALID_TRANSITIONS.get(current_status, set()))


def reassign_case(case_id: int, *, new_agent_id: int, changed_by: int) -> dict | None:
    """Transfer case ownership to a different agent (e.g. after escalation pickup)."""
    now = _now()
    with _cx_write_conn() as conn:
        old = conn.execute("SELECT agent_id FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if not old:
            return None
        old_agent_id = old[0]
        if old_agent_id == new_agent_id:
            return get_case(case_id)
        conn.execute(
            "UPDATE cases SET agent_id = ?, updated_at = ? WHERE case_id = ?",
            (new_agent_id, now, case_id),
        )
        _insert_and_get_id(conn,
            "INSERT INTO case_history (case_id, field_changed, old_value, new_value, changed_by, changed_at) "
            "VALUES (?,?,?,?,?,?)",
            (case_id, "agent_id", str(old_agent_id), str(new_agent_id), changed_by, now),
        )
    return get_case(case_id)


RESOLUTION_CODES = {
    "fixed",
    "duplicate",
    "cannot_reproduce",
    "wont_fix",
    "referred_third_party",
    "customer_withdrew",
    "information_provided",
    "account_updated",
}


def update_case(case_id: int, *, agent_id: int, **fields) -> dict | None:
    allowed = {"status", "priority", "subject", "description", "taxonomy_id", "resolution_code"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_case(case_id)

    now = _now()
    with _cx_write_conn() as conn:
        old = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if not old:
            return None
        old = dict(old)

        if "status" in updates:
            cur = old.get("status", "open")
            nxt = updates["status"]
            if nxt not in _VALID_TRANSITIONS.get(cur, set()):
                raise ValueError(
                    f"Invalid transition: {cur} → {nxt}. "
                    f"Allowed: {', '.join(sorted(_VALID_TRANSITIONS.get(cur, set()))) or 'none (terminal)'}"
                )

            if cur == "open" and nxt == "in_progress" and old.get("investor_id"):
                vid = old.get("verification_id")
                if not vid:
                    raise ValueError(
                        "Verification required: link a passed verification session "
                        "before moving an investor case out of 'open'."
                    )
                v_row = conn.execute(
                    "SELECT status, expires_at FROM verification_sessions WHERE verification_id = ?",
                    (vid,),
                ).fetchone()
                if not v_row:
                    raise ValueError("Linked verification session not found.")
                if v_row[0] not in ("passed", "verified"):
                    raise ValueError(
                        f"Verification not passed (status={v_row[0]}). "
                        "Cannot proceed until identity is verified."
                    )
                if v_row[1]:
                    expires = datetime.strptime(v_row[1], "%Y-%m-%d %H:%M:%S")
                    if datetime.strptime(now, "%Y-%m-%d %H:%M:%S") > expires:
                        raise ValueError(
                            "Verification session has expired. Start a new verification."
                        )

            if nxt == "resolved":
                rc = updates.get("resolution_code") or fields.get("resolution_code")
                if not rc:
                    raise ValueError(
                        "resolution_code is required when resolving a case. "
                        f"Valid codes: {', '.join(sorted(RESOLUTION_CODES))}"
                    )
                if rc not in RESOLUTION_CODES:
                    raise ValueError(
                        f"Invalid resolution_code '{rc}'. "
                        f"Valid codes: {', '.join(sorted(RESOLUTION_CODES))}"
                    )
                updates["resolution_code"] = rc

            if cur == "escalated" and nxt == "in_progress" and old.get("agent_id") != agent_id:
                updates["agent_id"] = agent_id

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values())

        if "status" in updates:
            old_status = old.get("status", "open")
            new_status = updates["status"]

            if old_status == "open" and new_status != "open" and not old.get("first_response_at"):
                set_clause += ", first_response_at = ?"
                params.append(now)

            if old_status == "pending_customer" and new_status != "pending_customer":
                pending_since = old.get("pending_since")
                if pending_since:
                    pending_dt = datetime.strptime(pending_since, "%Y-%m-%d %H:%M:%S")
                    elapsed = (datetime.strptime(now, "%Y-%m-%d %H:%M:%S") - pending_dt).total_seconds()
                    old_pending = old.get("pending_seconds") or 0
                    set_clause += ", pending_seconds = ?, pending_since = NULL"
                    params.extend([int(old_pending + elapsed)])

            if new_status == "pending_customer":
                set_clause += ", pending_since = ?"
                params.append(now)

            if new_status == "resolved" and not old.get("resolved_at"):
                set_clause += ", resolved_at = ?"
                params.append(now)
            if new_status == "closed" and not old.get("closed_at"):
                set_clause += ", closed_at = ?"
                params.append(now)

        set_clause += ", updated_at = ?"
        params.append(now)
        params.append(case_id)

        conn.execute(f"UPDATE cases SET {set_clause} WHERE case_id = ?", params)

        for field, new_val in updates.items():
            _insert_and_get_id(conn,
                "INSERT INTO case_history (case_id, field_changed, old_value, new_value, changed_by, changed_at) "
                "VALUES (?,?,?,?,?,?)",
                (case_id, field, str(old.get(field)), str(new_val), agent_id, now),
            )

    return get_case(case_id)


def add_case_note(case_id: int, *, author_id: int, content: str, is_internal: bool = False) -> dict:
    now = _now()
    with _cx_write_conn() as conn:
        note_id = _insert_and_get_id(conn,
            "INSERT INTO case_notes (case_id, author_id, content, is_internal, created_at) "
            "VALUES (?,?,?,?,?)",
            (case_id, author_id, content, 1 if is_internal else 0, now),
        )
        conn.execute("UPDATE cases SET updated_at = ? WHERE case_id = ?", (now, case_id))

    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT n.*, u.full_name AS author_name FROM case_notes n "
            "JOIN cx_users u ON n.author_id = u.user_id WHERE n.note_id = ?",
            (note_id,),
        ).fetchone()
        return dict(row) if row else {"note_id": note_id}


def create_escalation(case_id: int, *, from_agent_id: int, reason: str) -> dict:
    now = _now()
    with _cx_write_conn() as conn:
        from_user = conn.execute(
            "SELECT tier FROM cx_users WHERE user_id = ?", (from_agent_id,)
        ).fetchone()
        from_tier = from_user[0] if from_user else "tier1"

        targets = conn.execute(
            "SELECT user_id FROM cx_users "
            "WHERE (role = 'supervisor' OR (role = 'agent' AND tier = 'tier2')) "
            "AND is_active = 1 AND user_id != ?",
            (from_agent_id,),
        ).fetchall()
        import random
        to_agent_id = random.choice(targets)[0] if targets else from_agent_id

        esc_id = _insert_and_get_id(conn,
            "INSERT INTO escalations (case_id, rule_id, from_agent_id, to_agent_id, "
            "from_tier, to_tier, reason, escalated_at) VALUES (?,?,?,?,?,?,?,?)",
            (case_id, 3, from_agent_id, to_agent_id, from_tier, "tier2", reason, now),
        )
        old_status = conn.execute("SELECT status FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        old_status_val = old_status[0] if old_status else "open"
        conn.execute("UPDATE cases SET status = 'escalated', updated_at = ? WHERE case_id = ?", (now, case_id))

        _insert_and_get_id(conn,
            "INSERT INTO case_history (case_id, field_changed, old_value, new_value, changed_by, changed_at) "
            "VALUES (?,?,?,?,?,?)",
            (case_id, "status", old_status_val, "escalated", from_agent_id, now),
        )

    return get_escalations(case_id)


# ─── Outbound Tasks ─────────────────────────────────────────────

_OUTBOUND_SELECT = (
    "SELECT o.*, u.full_name AS agent_name, "
    "inv.full_name AS investor_name, inv.investor_code "
    "FROM outbound_tasks o "
    "LEFT JOIN cx_users u ON o.agent_id = u.user_id "
    "LEFT JOIN core.investors inv ON o.investor_id = inv.investor_id "
)


def list_outbound_tasks(
    *,
    status: str | None = None,
    task_type: str | None = None,
    agent_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if status:
        clauses.append("o.status = ?")
        params.append(status)
    if task_type:
        clauses.append("o.task_type = ?")
        params.append(task_type)
    if agent_id:
        clauses.append("o.agent_id = ?")
        params.append(agent_id)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = _OUTBOUND_SELECT + f"{where} ORDER BY o.scheduled_at ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _cx_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_outbound_task(task_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute(
            _OUTBOUND_SELECT + "WHERE o.task_id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None


def outbound_stats() -> dict:
    with _cx_conn() as conn:
        by_status = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM outbound_tasks GROUP BY status"
        ).fetchall()
        by_type = conn.execute(
            "SELECT task_type, COUNT(*) AS cnt FROM outbound_tasks GROUP BY task_type"
        ).fetchall()
        today_completed = conn.execute(
            "SELECT COUNT(*) FROM outbound_tasks WHERE status='completed' "
            "AND DATE(completed_at) = DATE('now')"
        ).fetchone()[0]
        return {
            "by_status": {r["status"]: r["cnt"] for r in by_status},
            "by_type": {r["task_type"]: r["cnt"] for r in by_type},
            "completed_today": today_completed,
            "total": sum(r["cnt"] for r in by_status),
        }


def create_outbound_task(
    *,
    task_type: str,
    investor_id: int | None = None,
    agent_id: int | None = None,
    case_id: int | None = None,
    priority: str = "medium",
    notes: str | None = None,
    scheduled_at: str | None = None,
) -> dict:
    now = _now()
    with _cx_write_conn() as conn:
        task_id = _insert_and_get_id(conn,
            "INSERT INTO outbound_tasks "
            "(task_type, investor_id, agent_id, case_id, status, priority, "
            "notes, outcome, scheduled_at, attempted_at, completed_at, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (task_type, investor_id, agent_id, case_id, "pending", priority,
             notes, None, scheduled_at or now, None, None, now, now),
        )
    return get_outbound_task(task_id)


def update_outbound_task(task_id: int, *, agent_id: int, **fields) -> dict | None:
    allowed = {"status", "outcome", "notes", "agent_id"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_outbound_task(task_id)

    now = _now()
    with _cx_write_conn() as conn:
        if updates.get("status") == "in_progress":
            updates["attempted_at"] = now
        if updates.get("status") in ("completed", "failed"):
            updates["completed_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values())
        set_clause += ", updated_at = ?"
        params.append(now)
        params.append(task_id)
        conn.execute(f"UPDATE outbound_tasks SET {set_clause} WHERE task_id = ?", params)

    return get_outbound_task(task_id)


# ─── Verification Sessions ──────────────────────────────────────

def get_verification(verification_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT v.*, u.full_name AS agent_name, "
            "inv.full_name AS investor_name, inv.investor_code "
            "FROM verification_sessions v "
            "LEFT JOIN cx_users u ON v.agent_id = u.user_id "
            "LEFT JOIN core.investors inv ON v.investor_id = inv.investor_id "
            "WHERE v.verification_id = ?",
            (verification_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        import json
        d["steps_completed"] = json.loads(d.get("steps_completed") or "{}")
        d["steps_required"] = json.loads(d.get("steps_required") or "[]")
        return d


def get_verification_for_case(case_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT verification_id FROM cases WHERE case_id = ? AND verification_id IS NOT NULL",
            (case_id,),
        ).fetchone()
        if not row:
            return None
        return get_verification(row[0])


def start_verification(
    *,
    investor_id: int,
    agent_id: int,
    call_id: int | None = None,
    method: str = "verbal",
) -> dict:
    import json
    now = _now()
    steps_required = ["full_name", "national_id", "mobile_number", "account_status"]
    with _cx_write_conn() as conn:
        vid = _insert_and_get_id(conn,
            "INSERT INTO verification_sessions "
            "(investor_id, agent_id, call_id, method, status, "
            "steps_completed, steps_required, failure_reason, notes, created_at, verified_at, expires_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (investor_id, agent_id, call_id, method, "in_progress",
             json.dumps({}), json.dumps(steps_required), None, None, now, None, None),
        )
    return get_verification(vid)


def update_verification_step(verification_id: int, *, step: str, passed: bool) -> dict | None:
    import json
    v = get_verification(verification_id)
    if not v:
        return None

    steps_completed = v["steps_completed"]
    steps_completed[step] = "passed" if passed else "failed"
    now = _now()

    with _cx_write_conn() as conn:
        conn.execute(
            "UPDATE verification_sessions SET steps_completed = ? "
            "WHERE verification_id = ?",
            (json.dumps(steps_completed), verification_id),
        )

    all_required = v["steps_required"]
    all_done = all(step in steps_completed for step in all_required)
    any_failed = any(steps_completed.get(s) == "failed" for s in all_required)

    if all_done:
        status = "failed" if any_failed else "passed"
        complete_verification(verification_id, status=status)

    return get_verification(verification_id)


def complete_verification(verification_id: int, *, status: str, failure_reason: str | None = None) -> dict | None:
    now = _now()
    with _cx_write_conn() as conn:
        conn.execute(
            "UPDATE verification_sessions SET status = ?, failure_reason = ?, verified_at = ? "
            "WHERE verification_id = ?",
            (status, failure_reason, now if status == "passed" else None, verification_id),
        )
    return get_verification(verification_id)


def link_verification_to_case(case_id: int, verification_id: int) -> None:
    now = _now()
    v = get_verification(verification_id)
    if not v:
        raise ValueError("Verification session not found.")
    if v.get("status") not in ("passed", "verified"):
        raise ValueError(
            f"Cannot link verification with status '{v.get('status')}'. "
            "Only passed/verified sessions can be linked."
        )
    expires = v.get("expires_at")
    if expires:
        exp_dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        if datetime.strptime(now, "%Y-%m-%d %H:%M:%S") > exp_dt:
            raise ValueError("Verification session has expired. Start a new verification.")
    with _cx_write_conn() as conn:
        conn.execute(
            "UPDATE cases SET verification_id = ?, updated_at = ? WHERE case_id = ?",
            (verification_id, now, case_id),
        )


# ─── Reports (SQLite-based for POC) ─────────────────────────────

def report_overview(days: int = 7) -> dict:
    with _cx_conn() as conn:
        volume = conn.execute(
            "SELECT DATE(created_at) AS day, COUNT(*) AS total, "
            "SUM(CASE WHEN status IN ('open','in_progress','pending_customer') THEN 1 ELSE 0 END) AS active, "
            "SUM(CASE WHEN status IN ('resolved','closed') THEN 1 ELSE 0 END) AS resolved, "
            "SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) AS escalated "
            "FROM cases WHERE created_at >= DATE('now', ?) "
            "GROUP BY DATE(created_at) ORDER BY day",
            (f"-{days} days",),
        ).fetchall()

        sla_compliance = conn.execute(
            "SELECT p.name AS policy_name, COUNT(DISTINCT c.case_id) AS total_cases, "
            "COUNT(DISTINCT CASE WHEN b.breach_type = 'first_response' THEN b.case_id END) AS frt_breached, "
            "COUNT(DISTINCT CASE WHEN b.breach_type = 'resolution' THEN b.case_id END) AS rt_breached "
            "FROM cases c "
            "JOIN sla_policies p ON c.sla_policy_id = p.policy_id "
            "LEFT JOIN sla_breaches b ON c.case_id = b.case_id "
            "WHERE c.created_at >= DATE('now', ?) "
            "GROUP BY p.name",
            (f"-{days} days",),
        ).fetchall()

        agent_perf = conn.execute(
            "SELECT u.user_id AS agent_id, u.full_name AS agent_name, "
            "COUNT(c.case_id) AS cases_handled, "
            "ROUND(AVG(CASE WHEN c.resolved_at IS NOT NULL "
            "  THEN (julianday(c.resolved_at) - julianday(c.created_at)) * 24 * 60 END), 1) AS avg_resolution_min, "
            "ROUND(AVG(q.total_score), 1) AS avg_qa_score "
            "FROM cx_users u "
            "JOIN cases c ON u.user_id = c.agent_id "
            "LEFT JOIN qa_evaluations q ON c.case_id = q.case_id "
            "WHERE u.role = 'agent' AND c.created_at >= DATE('now', ?) "
            "GROUP BY u.user_id HAVING cases_handled >= 3 "
            "ORDER BY cases_handled DESC LIMIT 20",
            (f"-{days} days",),
        ).fetchall()

        category_breakdown = conn.execute(
            "SELECT t.category, COUNT(*) AS cnt, "
            "SUM(CASE WHEN c.status IN ('resolved','closed') THEN 1 ELSE 0 END) AS resolved "
            "FROM cases c JOIN case_taxonomy t ON c.taxonomy_id = t.taxonomy_id "
            "WHERE c.created_at >= DATE('now', ?) "
            "GROUP BY t.category ORDER BY cnt DESC",
            (f"-{days} days",),
        ).fetchall()

        fcr = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN c.status IN ('resolved','closed') "
            "  AND c.case_id NOT IN (SELECT case_id FROM escalations) "
            "  THEN 1 ELSE 0 END) AS first_contact "
            "FROM cases c WHERE c.created_at >= DATE('now', ?)",
            (f"-{days} days",),
        ).fetchone()

        avg_handle = conn.execute(
            "SELECT ROUND(AVG(duration_seconds) / 60.0, 1) AS aht_min "
            "FROM calls WHERE status = 'completed' AND call_start >= DATE('now', ?)",
            (f"-{days} days",),
        ).fetchone()

        verif_stats = conn.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN status IN ('passed','verified') THEN 1 ELSE 0 END) AS passed, "
            "SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed "
            "FROM verification_sessions WHERE created_at >= DATE('now', ?)",
            (f"-{days} days",),
        ).fetchone()

        escalation_rate = conn.execute(
            "SELECT COUNT(*) AS total, "
            "(SELECT COUNT(DISTINCT e.case_id) FROM escalations e "
            "  JOIN cases c2 ON e.case_id = c2.case_id "
            "  WHERE c2.created_at >= DATE('now', ?)) AS escalated "
            "FROM cases WHERE created_at >= DATE('now', ?)",
            (f"-{days} days", f"-{days} days"),
        ).fetchone()

        compliance_rows = []
        for r in sla_compliance:
            d = dict(r)
            total = d["total_cases"] or 1
            frt_met = total - d["frt_breached"]
            rt_met = total - d["rt_breached"]
            d["frt_compliance_pct"] = round(frt_met / total * 100, 1)
            d["rt_compliance_pct"] = round(rt_met / total * 100, 1)
            d["compliance_pct"] = round((frt_met + rt_met) / (total * 2) * 100, 1) if total else 100.0
            compliance_rows.append(d)

        reopen_count = conn.execute(
            "SELECT COUNT(DISTINCT h.case_id) AS reopened "
            "FROM case_history h JOIN cases c ON h.case_id = c.case_id "
            "WHERE h.field_changed = 'status' AND h.old_value = 'resolved' "
            "AND h.new_value = 'in_progress' AND c.created_at >= DATE('now', ?)",
            (f"-{days} days",),
        ).fetchone()

        resolution_breakdown = conn.execute(
            "SELECT resolution_code, COUNT(*) AS cnt "
            "FROM cases WHERE resolution_code IS NOT NULL "
            "AND created_at >= DATE('now', ?) GROUP BY resolution_code ORDER BY cnt DESC",
            (f"-{days} days",),
        ).fetchall()

        total_cases = fcr["total"] or 1
        fcr_pct = round((fcr["first_contact"] or 0) / total_cases * 100, 1)
        esc_total = escalation_rate["total"] or 1
        esc_pct = round((escalation_rate["escalated"] or 0) / esc_total * 100, 1)

        resolved_total = sum(1 for r in volume for _ in [1] if True)
        resolved_count = conn.execute(
            "SELECT COUNT(*) FROM cases WHERE status IN ('resolved','closed') "
            "AND created_at >= DATE('now', ?)", (f"-{days} days",),
        ).fetchone()[0] or 1
        reopen_pct = round((reopen_count["reopened"] or 0) / resolved_count * 100, 1)

        return {
            "period_days": days,
            "case_volume": [dict(r) for r in volume],
            "sla_compliance": compliance_rows,
            "agent_performance": [dict(r) for r in agent_perf],
            "category_breakdown": [dict(r) for r in category_breakdown],
            "resolution_breakdown": [dict(r) for r in resolution_breakdown],
            "kpis": {
                "fcr_pct": fcr_pct,
                "avg_handling_time_min": avg_handle["aht_min"] or 0,
                "escalation_rate_pct": esc_pct,
                "reopen_rate_pct": reopen_pct,
                "verification_total": verif_stats["total"] or 0,
                "verification_pass_rate": round(
                    (verif_stats["passed"] or 0) / max(verif_stats["total"] or 1, 1) * 100, 1
                ),
            },
        }


# ─── Knowledge Base ──────────────────────────────────────────────


def list_kb_articles(category: str | None = None, search: str | None = None) -> list[dict]:
    with _cx_conn() as conn:
        sql = "SELECT * FROM kb_articles WHERE is_published = 1"
        params = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if search:
            sql += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        sql += " ORDER BY updated_at DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_kb_article(article_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute("SELECT * FROM kb_articles WHERE article_id = ?", (article_id,)).fetchone()
        return dict(row) if row else None


def kb_categories() -> list[str]:
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM kb_articles WHERE is_published = 1 ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


# ─── Approvals ───────────────────────────────────────────────────

VALID_APPROVAL_TYPES = ("refund", "account_closure", "data_correction", "fee_waiver", "escalation_override")


def create_approval(case_id: int, requested_by: int, approval_type: str,
                    description: str, amount: float | None = None) -> dict:
    if approval_type not in VALID_APPROVAL_TYPES:
        raise ValueError(f"Invalid approval type. Valid: {', '.join(VALID_APPROVAL_TYPES)}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _cx_write_conn() as conn:
        cur = conn.execute(
            """INSERT INTO approvals (case_id, requested_by, approval_type, amount, description, status, requested_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (case_id, requested_by, approval_type, amount, description, now),
        )
        row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def review_approval(approval_id: int, reviewed_by: int, decision: str, notes: str | None = None) -> dict:
    if decision not in ("approved", "rejected"):
        raise ValueError("Decision must be 'approved' or 'rejected'")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _cx_write_conn() as conn:
        existing = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        if not existing:
            raise ValueError(f"Approval {approval_id} not found")
        if existing["status"] != "pending":
            raise ValueError(f"Approval already {existing['status']}")
        conn.execute(
            "UPDATE approvals SET status = ?, reviewed_by = ?, reviewer_notes = ?, reviewed_at = ? WHERE approval_id = ?",
            (decision, reviewed_by, notes, now, approval_id),
        )
        row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
        return dict(row)


def list_approvals(status: str | None = None, case_id: int | None = None, limit: int = 50) -> list[dict]:
    with _cx_conn() as conn:
        sql = """SELECT a.*, cu.full_name as requester_name
                 FROM approvals a
                 JOIN cx_users cu ON a.requested_by = cu.user_id
                 WHERE 1=1"""
        params = []
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        if case_id:
            sql += " AND a.case_id = ?"
            params.append(case_id)
        sql += " ORDER BY a.requested_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def pending_approval_count() -> int:
    with _cx_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM approvals WHERE status = 'pending'").fetchone()
        return row["cnt"]


# ─── Agent Presence ──────────────────────────────────────────────

VALID_PRESENCE_STATUSES = ("available", "on_break", "acw", "in_call", "training", "offline")


def get_agent_presence(agent_id: int) -> dict | None:
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT * FROM agent_presence WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        return dict(row) if row else None


def set_agent_presence(agent_id: int, status: str) -> dict:
    if status not in VALID_PRESENCE_STATUSES:
        raise ValueError(f"Invalid presence status: {status}. Valid: {', '.join(VALID_PRESENCE_STATUSES)}")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _cx_write_conn() as conn:
        existing = conn.execute(
            "SELECT agent_id FROM agent_presence WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE agent_presence SET status = ?, updated_at = ? WHERE agent_id = ?",
                (status, now, agent_id),
            )
        else:
            conn.execute(
                "INSERT INTO agent_presence (agent_id, status, updated_at) VALUES (?, ?, ?)",
                (agent_id, status, now),
            )
        return {"agent_id": agent_id, "status": status, "updated_at": now}


def list_agent_presence() -> list[dict]:
    with _cx_conn() as conn:
        rows = conn.execute("""
            SELECT ap.agent_id, ap.status, ap.updated_at,
                   cu.full_name, cu.role, cu.tier
            FROM agent_presence ap
            JOIN cx_users cu ON ap.agent_id = cu.user_id
            ORDER BY cu.role, cu.full_name
        """).fetchall()
        return [dict(r) for r in rows]


def presence_summary() -> dict:
    with _cx_conn() as conn:
        rows = conn.execute("""
            SELECT ap.status, COUNT(*) as count
            FROM agent_presence ap
            JOIN cx_users cu ON ap.agent_id = cu.user_id
            WHERE cu.role IN ('agent', 'senior_agent')
            GROUP BY ap.status
        """).fetchall()
        return {r["status"]: r["count"] for r in rows}
