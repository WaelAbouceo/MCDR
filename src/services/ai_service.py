"""AI service for semantic KB search, case categorization, and other AI features."""

import json
import math
from datetime import datetime, timezone
from typing import Any

from src.config import get_settings
from src.services import cx_data_service

settings = get_settings()


def _get_embedding(text: str) -> list[float] | None:
    if not settings.openai_api_key or not text.strip():
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.embeddings.create(
            model="text-embedding-3-small",
            input=text.strip()[:8000],
        )
        return r.data[0].embedding
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def store_article_embedding(article_id: int, embedding: list[float]) -> None:
    """Store or replace embedding for a KB article."""
    from src.services.cx_data_service import _cx_write_conn
    emb_json = json.dumps(embedding)
    with _cx_write_conn() as conn:
        conn.execute(
            "INSERT INTO kb_article_embeddings (article_id, embedding) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE embedding = VALUES(embedding), updated_at = CURRENT_TIMESTAMP",
            (article_id, emb_json),
        )


def get_article_embedding(article_id: int) -> list[float] | None:
    """Load stored embedding for an article."""
    from src.services.cx_data_service import _cx_conn
    with _cx_conn() as conn:
        row = conn.execute(
            "SELECT embedding FROM kb_article_embeddings WHERE article_id = %s",
            (article_id,),
        ).fetchone()
    if not row or not row.get("embedding"):
        return None
    emb = row["embedding"]
    if isinstance(emb, str):
        return json.loads(emb)
    return emb


def list_article_embeddings() -> list[tuple[int, list[float]]]:
    """Return (article_id, embedding) for all stored embeddings."""
    from src.services.cx_data_service import _cx_conn
    with _cx_conn() as conn:
        rows = conn.execute(
            "SELECT article_id, embedding FROM kb_article_embeddings",
        ).fetchall()
    out = []
    for r in rows:
        emb = r.get("embedding")
        if emb is None:
            continue
        if isinstance(emb, str):
            emb = json.loads(emb)
        out.append((r["article_id"], emb))
    return out


def semantic_kb_search(query: str, limit: int = 10, category: str | None = None) -> list[dict[str, Any]]:
    """Search KB articles by semantic similarity. Falls back to keyword search if no embeddings or no API key."""
    if not settings.ai_enabled or not settings.openai_api_key:
        return cx_data_service.list_kb_articles(category=category, search=query)[:limit]

    query_emb = _get_embedding(query)
    if not query_emb:
        return cx_data_service.list_kb_articles(category=category, search=query)[:limit]

    stored = list_article_embeddings()
    if not stored:
        return cx_data_service.list_kb_articles(category=category, search=query)[:limit]

    articles_by_id = {a["article_id"]: a for a in cx_data_service.list_kb_articles(category=category)}
    scored = []
    for aid, emb in stored:
        if aid not in articles_by_id:
            continue
        sim = _cosine_similarity(query_emb, emb)
        scored.append((articles_by_id[aid], sim))
    scored.sort(key=lambda x: -x[1])
    return [a for a, _ in scored[:limit]]


def embed_kb_article(article_id: int) -> bool:
    """Generate and store embedding for one KB article. Returns True if successful."""
    article = cx_data_service.get_kb_article(article_id)
    if not article:
        return False
    text = f"{article.get('title', '')} {article.get('content', '')} {article.get('category', '')}"
    emb = _get_embedding(text)
    if not emb:
        return False
    store_article_embedding(article_id, emb)
    return True


def embed_all_kb_articles() -> dict[str, int]:
    """Generate and store embeddings for all published KB articles. Returns counts {ok, fail}."""
    articles = cx_data_service.list_kb_articles()
    ok = fail = 0
    for a in articles:
        aid = a.get("article_id")
        if not aid:
            continue
        if embed_kb_article(aid):
            ok += 1
        else:
            fail += 1
    return {"ok": ok, "fail": fail}


def _chat(prompt: str, max_tokens: int = 200) -> str | None:
    if not settings.openai_api_key or not settings.ai_enabled:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return (r.choices[0].message.content or "").strip() if r.choices else None
    except Exception:
        return None


def suggest_case_category(subject: str, description: str | None) -> dict[str, Any] | None:
    """Suggest taxonomy_id, category, subcategory from case subject and description."""
    taxonomy = cx_data_service.list_taxonomy()
    if not taxonomy:
        return None
    options = "\n".join(
        f"- {t['taxonomy_id']}: {t['category']} / {t['subcategory']}"
        for t in taxonomy[:50]
    )
    prompt = f"""Given this support case, pick the single best matching category from the list. Reply with only one line: taxonomy_id, category, subcategory (e.g. 1, Trading, Order Status).

Case subject: {subject[:200]}
Description: {(description or '')[:500]}

Options:
{options}

Reply with: taxonomy_id, category, subcategory"""
    out = _chat(prompt, max_tokens=80)
    if not out:
        return None
    parts = [p.strip() for p in out.split(",")]
    if len(parts) >= 3:
        try:
            tid = int(parts[0])
            return {"taxonomy_id": tid, "category": parts[1], "subcategory": parts[2]}
        except (ValueError, IndexError):
            pass
    return None


RESOLUTION_CODES_LIST = [
    "fixed", "information_provided", "account_updated", "duplicate",
    "cannot_reproduce", "referred_third_party", "customer_withdrew", "wont_fix",
]


def suggest_resolution_code(subject: str, notes_text: str, description: str | None) -> str | None:
    """Suggest resolution code from case content."""
    prompt = f"""Given this support case, pick the single best resolution code. Reply with only the code, nothing else.

Codes: {', '.join(RESOLUTION_CODES_LIST)}

Case subject: {subject[:200]}
Description: {(description or '')[:150]}
Notes excerpt: {notes_text[:300]}

Reply with exactly one code from the list."""
    out = _chat(prompt, max_tokens=30)
    if out and out.lower().replace(" ", "_") in RESOLUTION_CODES_LIST:
        return out.lower().replace(" ", "_")
    for code in RESOLUTION_CODES_LIST:
        if code in (out or "").lower():
            return code
    return None


def suggest_qa_draft(case_subject: str, case_description: str | None, notes_text: str, resolution_code: str | None) -> dict[str, Any] | None:
    """Suggest QA score (0-100) and short feedback."""
    prompt = f"""As a QA analyst, suggest a quality score (0-100) and one sentence feedback for this support case. Reply in exactly two lines: Line 1: score (number only). Line 2: feedback sentence.

Case subject: {case_subject[:200]}
Description: {(case_description or '')[:200]}
Notes: {notes_text[:400]}
Resolution: {resolution_code or 'N/A'}"""
    out = _chat(prompt, max_tokens=120)
    if not out:
        return None
    lines = out.strip().split("\n")
    score = None
    for line in lines:
        try:
            score = int("".join(c for c in line if c.isdigit())[:3])
            if 0 <= score <= 100:
                break
        except (ValueError, IndexError):
            continue
    feedback = lines[1].strip() if len(lines) > 1 else ""
    return {"total_score": score or 70, "feedback": feedback or "No feedback."}


def summarize_case(subject: str, description: str | None, notes_text: str, resolution_code: str | None) -> str | None:
    """Generate a 2-3 sentence case summary."""
    prompt = f"""Summarize this support case in 2-3 sentences: issue and outcome.

Subject: {subject[:200]}
Description: {(description or '')[:300]}
Notes: {notes_text[:500]}
Resolution: {resolution_code or 'N/A'}

Summary:"""
    return _chat(prompt, max_tokens=150)


def next_best_actions(case_data: dict) -> list[str]:
    """Rule-based next-best-action suggestions (no LLM)."""
    suggestions = []
    status = (case_data.get("status") or "").lower()
    if status == "open" and case_data.get("investor_id") and not case_data.get("verification_id"):
        suggestions.append("Verify caller identity — investor not verified yet.")
    if status in ("open", "in_progress") and case_data.get("priority") == "critical":
        suggestions.append("High priority — consider escalating if blocked.")
    if status == "pending_customer":
        suggestions.append("Follow up with customer — case is waiting on their response.")
    return suggestions


def sentiment_note(content: str) -> dict[str, Any] | None:
    """Classify note sentiment: positive, negative, or neutral."""
    if not content.strip():
        return None
    out = _chat(
        f"Classify the sentiment of this support note as exactly one word: positive, negative, or neutral.\n\nNote: {content[:500]}\n\nReply with one word only.",
        max_tokens=10,
    )
    if not out:
        return None
    out = out.lower().strip()
    label = "neutral"
    if "positive" in out:
        label = "positive"
    elif "negative" in out:
        label = "negative"
    return {"label": label, "score": 1.0}


def predict_sla_at_risk(limit: int = 20) -> list[dict[str, Any]]:
    """Return cases at risk of SLA breach (heuristic: FRT or RT due within threshold)."""
    from src.services.cx_data_service import _cx_conn
    with _cx_conn() as conn:
        rows = conn.execute("""
            SELECT c.case_id, c.case_number, c.subject, c.status, c.priority, c.created_at,
                   c.first_response_at, c.resolved_at, c.pending_seconds,
                   p.first_response_minutes, p.resolution_minutes, p.name AS policy_name
            FROM cases c
            JOIN sla_policies p ON c.sla_policy_id = p.policy_id
            WHERE c.status IN ('open', 'in_progress') AND c.sla_policy_id IS NOT NULL
            ORDER BY c.created_at ASC
            LIMIT %s
        """, (limit * 2,)).fetchall()
    at_risk = []
    now = datetime.now(timezone.utc)
    for r in rows:
        created = r.get("created_at")
        first_response_at = r.get("first_response_at")
        resolved_at = r.get("resolved_at")
        pending_min = (r.get("pending_seconds") or 0) / 60.0
        if not created:
            continue
        if getattr(created, "tzinfo", None) is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (now - created).total_seconds() / 60.0 - pending_min
        frt_limit = float(r.get("first_response_minutes") or 9999)
        rt_limit = float(r.get("resolution_minutes") or 9999)
        frt_breach_in = frt_limit - elapsed if not first_response_at else None
        rt_breach_in = rt_limit - elapsed if not resolved_at else None
        if (frt_breach_in is not None and frt_breach_in <= 15) or (rt_breach_in is not None and rt_breach_in <= 30):
            at_risk.append({
                "case_id": r["case_id"],
                "case_number": r["case_number"],
                "subject": r["subject"],
                "status": r["status"],
                "priority": r["priority"],
                "policy_name": r.get("policy_name"),
                "frt_breach_in_minutes": round(frt_breach_in, 1) if frt_breach_in is not None else None,
                "rt_breach_in_minutes": round(rt_breach_in, 1) if rt_breach_in is not None else None,
            })
            if len(at_risk) >= limit:
                break
    return at_risk
