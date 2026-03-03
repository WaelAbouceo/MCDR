"""CX Intelligent Layer data service.

Reads and writes GoChat247 operational data: calls, cases, notes,
escalations, SLA breaches, QA evaluations — all linked to
MCDR investors.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from src.config import get_settings

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
            "SELECT * FROM case_history WHERE case_id = ? ORDER BY changed_at",
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
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_SAFE_ID_TARGETS = {
    ("cases", "case_id"),
    ("case_notes", "note_id"),
    ("case_history", "history_id"),
    ("escalations", "escalation_id"),
}


def _next_id(conn: sqlite3.Connection, table: str, id_col: str) -> int:
    if (table, id_col) not in _SAFE_ID_TARGETS:
        raise ValueError(f"Unsafe _next_id target: {table}.{id_col}")
    row = conn.execute(f"SELECT MAX({id_col}) FROM {table}").fetchone()
    return (row[0] or 0) + 1


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
        case_id = _next_id(conn, "cases", "case_id")
        case_number = f"CAS-{case_id:06}"
        conn.execute(
            "INSERT INTO cases (case_id, case_number, call_id, investor_id, agent_id, "
            "taxonomy_id, priority, status, subject, description, sla_policy_id, "
            "first_response_at, resolved_at, closed_at, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, case_number, call_id, investor_id, agent_id,
             taxonomy_id, priority, "open", subject, description, sla_policy_id,
             None, None, None, now, now),
        )
    return get_case(case_id)


def update_case(case_id: int, *, agent_id: int, **fields) -> dict | None:
    allowed = {"status", "priority", "subject", "description", "taxonomy_id"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_case(case_id)

    now = _now()
    with _cx_write_conn() as conn:
        old = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if not old:
            return None
        old = dict(old)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values())

        if "status" in updates:
            if updates["status"] == "resolved" and not old.get("resolved_at"):
                set_clause += ", resolved_at = ?"
                params.append(now)
            if updates["status"] == "closed" and not old.get("closed_at"):
                set_clause += ", closed_at = ?"
                params.append(now)

        set_clause += ", updated_at = ?"
        params.append(now)
        params.append(case_id)

        conn.execute(f"UPDATE cases SET {set_clause} WHERE case_id = ?", params)

        history_id = _next_id(conn, "case_history", "history_id")
        for field, new_val in updates.items():
            conn.execute(
                "INSERT INTO case_history (history_id, case_id, field_changed, old_value, new_value, changed_by, changed_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (history_id, case_id, field, str(old.get(field)), str(new_val), agent_id, now),
            )
            history_id += 1

    return get_case(case_id)


def add_case_note(case_id: int, *, author_id: int, content: str, is_internal: bool = False) -> dict:
    now = _now()
    with _cx_write_conn() as conn:
        note_id = _next_id(conn, "case_notes", "note_id")
        conn.execute(
            "INSERT INTO case_notes (note_id, case_id, author_id, content, is_internal, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (note_id, case_id, author_id, content, 1 if is_internal else 0, now),
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
        supervisors = conn.execute(
            "SELECT user_id FROM cx_users WHERE role = 'supervisor' AND is_active = 1"
        ).fetchall()
        import random
        to_agent_id = random.choice(supervisors)[0] if supervisors else from_agent_id

        esc_id = _next_id(conn, "escalations", "escalation_id")
        conn.execute(
            "INSERT INTO escalations (escalation_id, case_id, rule_id, from_agent_id, to_agent_id, "
            "from_tier, to_tier, reason, escalated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (esc_id, case_id, 3, from_agent_id, to_agent_id, "tier1", "tier2", reason, now),
        )
        conn.execute("UPDATE cases SET status = 'escalated', updated_at = ? WHERE case_id = ?", (now, case_id))

        history_id = _next_id(conn, "case_history", "history_id")
        conn.execute(
            "INSERT INTO case_history (history_id, case_id, field_changed, old_value, new_value, changed_by, changed_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (history_id, case_id, "status", "open", "escalated", from_agent_id, now),
        )

    return get_escalations(case_id)
