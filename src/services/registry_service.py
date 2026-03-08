"""MCDR Core Registry + Mobile App lookup service.

Connects to the MCDR databases in READ-ONLY mode,
simulating the real cross-premises data lookup from GoChat247
back into MCDR's investor registry.
"""

import pymysql
import pymysql.cursors
from contextlib import contextmanager
from typing import Generator

from src.config import get_settings

settings = get_settings()


@contextmanager
def _readonly_conn(db_params: dict) -> Generator[pymysql.cursors.DictCursor, None, None]:
    conn = pymysql.connect(
        **db_params,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
    )
    try:
        cursor = conn.cursor()
        yield cursor
    finally:
        conn.close()


# ─── Investor Lookups ────────────────────────────────────────────

def get_investor_by_id(investor_id: int) -> dict | None:
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(
            "SELECT * FROM investors WHERE investor_id = %s", (investor_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_investor_by_code(investor_code: str) -> dict | None:
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(
            "SELECT * FROM investors WHERE investor_code = %s", (investor_code,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def search_investors(
    *,
    name: str | None = None,
    national_id: str | None = None,
    investor_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if name:
        clauses.append("full_name LIKE %s")
        params.append(f"%{name}%")
    if national_id:
        clauses.append("national_id = %s")
        params.append(national_id)
    if investor_type:
        clauses.append("investor_type = %s")
        params.append(investor_type)
    if status:
        clauses.append("account_status = %s")
        params.append(status)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM investors {where} ORDER BY investor_id LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ─── Holdings Lookups ────────────────────────────────────────────

def get_holdings(investor_id: int) -> list[dict]:
    query = """
        SELECT h.*, s.isin, s.ticker, s.company_name, s.sector
        FROM holdings h
        JOIN securities s ON h.security_id = s.security_id
        WHERE h.investor_id = %s
        ORDER BY h.quantity * h.avg_price DESC
    """
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(query, (investor_id,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_portfolio_summary(investor_id: int) -> dict:
    query = """
        SELECT
            COUNT(*) AS positions,
            SUM(quantity) AS total_shares,
            SUM(quantity * avg_price) AS total_value,
            COUNT(DISTINCT s.sector) AS sectors
        FROM holdings h
        JOIN securities s ON h.security_id = s.security_id
        WHERE h.investor_id = %s
    """
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(query, (investor_id,))
        row = cur.fetchone()
        return dict(row) if row else {}


# ─── Security Lookups ────────────────────────────────────────────

def get_security_by_ticker(ticker: str) -> dict | None:
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(
            "SELECT * FROM securities WHERE ticker = %s", (ticker,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_security_by_isin(isin: str) -> dict | None:
    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(
            "SELECT * FROM securities WHERE isin = %s", (isin,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_securities(sector: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    if sector:
        query = "SELECT * FROM securities WHERE sector = %s ORDER BY ticker LIMIT %s OFFSET %s"
        params = (sector, limit, offset)
    else:
        query = "SELECT * FROM securities ORDER BY ticker LIMIT %s OFFSET %s"
        params = (limit, offset)

    with _readonly_conn(settings.core_db_params) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ─── Mobile App User Lookups ─────────────────────────────────────

def get_app_user_by_investor(investor_id: int) -> dict | None:
    with _readonly_conn(settings.mobile_db_params) as cur:
        cur.execute(
            "SELECT * FROM app_users WHERE investor_id = %s", (investor_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_app_user_by_mobile(mobile: str) -> dict | None:
    with _readonly_conn(settings.mobile_db_params) as cur:
        cur.execute(
            "SELECT * FROM app_users WHERE mobile = %s", (mobile,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_full_investor_profile(investor_id: int) -> dict | None:
    """Combined view: investor + app user + portfolio summary."""
    investor = get_investor_by_id(investor_id)
    if not investor:
        return None
    investor["app_user"] = get_app_user_by_investor(investor_id)
    investor["portfolio"] = get_portfolio_summary(investor_id)
    return investor
