"""AI endpoints: semantic KB search, embeddings, and other AI features."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.core.permissions import Action, Resource
from src.middleware.auth import RequirePermission, get_current_user
from src.models.user import User
from src.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


class SemanticSearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    category: str | None = None


class SuggestCategoryBody(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    description: str | None = None


class SuggestResolutionBody(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    notes_text: str = ""
    description: str | None = None


class SuggestQABody(BaseModel):
    case_subject: str = Field(min_length=1, max_length=300)
    case_description: str | None = None
    notes_text: str = ""
    resolution_code: str | None = None


class SummarizeBody(BaseModel):
    subject: str = Field(min_length=1, max_length=300)
    description: str | None = None
    notes_text: str = ""
    resolution_code: str | None = None


class SentimentBody(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


@router.post("/kb/semantic-search")
async def kb_semantic_search(
    body: SemanticSearchBody,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Semantic search over KB articles. Falls back to keyword search if AI unavailable."""
    return ai_service.semantic_kb_search(
        query=body.query,
        limit=body.limit,
        category=body.category,
    )


@router.post("/kb/embed-all")
async def kb_embed_all(
    user: User = Depends(RequirePermission(Resource.USER, Action.READ)),
):
    """Admin-only: build embeddings for all KB articles. Requires OPENAI_API_KEY."""
    if user.role and user.role.name != "admin":
        from src.core.exceptions import ForbiddenError
        raise ForbiddenError("Only admin can run embed-all")
    return ai_service.embed_all_kb_articles()


@router.post("/case/suggest-category")
async def case_suggest_category(
    body: SuggestCategoryBody,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Suggest case category/subcategory from subject and description."""
    return ai_service.suggest_case_category(body.subject, body.description)


@router.post("/case/suggest-resolution")
async def case_suggest_resolution(
    body: SuggestResolutionBody,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Suggest resolution code from case content."""
    return ai_service.suggest_resolution_code(
        body.subject, body.notes_text, body.description
    )


@router.post("/case/summarize")
async def case_summarize(
    body: SummarizeBody,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Generate a 2-3 sentence case summary."""
    return ai_service.summarize_case(
        body.subject, body.description, body.notes_text, body.resolution_code
    )


@router.post("/qa/suggest-draft")
async def qa_suggest_draft(
    body: SuggestQABody,
    _: User = Depends(RequirePermission(Resource.QA, Action.READ)),
):
    """Suggest QA score and feedback for a case (draft for analyst to review)."""
    return ai_service.suggest_qa_draft(
        body.case_subject, body.case_description, body.notes_text, body.resolution_code
    )


@router.post("/note/sentiment")
async def note_sentiment(
    body: SentimentBody,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Classify note sentiment (positive/negative/neutral)."""
    return ai_service.sentiment_note(body.content)


@router.get("/case/{case_id}/next-actions")
async def case_next_actions(
    case_id: int,
    _: User = Depends(RequirePermission(Resource.CASE, Action.READ)),
):
    """Next-best-action suggestions for the case (rule-based)."""
    from src.services.async_cx import cx
    case = await cx.get_case(case_id)
    if not case:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Case", case_id)
    return ai_service.next_best_actions(case)


@router.get("/sla/at-risk")
async def sla_at_risk(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(RequirePermission(Resource.SLA, Action.READ)),
):
    """Cases at risk of SLA breach (predicted)."""
    return ai_service.predict_sla_at_risk(limit=limit)
