"""MCDR Registry — read-only lookups into the core investor registry.

This is the data flow path: GoChat247 CX → MCDR Customer Data Zone.
All access is read-only, field-masked by role, and audit-logged.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_cx_db
from src.middleware.auth import RequirePermission
from src.middleware.field_mask import mask_response
from src.models.user import User
from src.schemas.registry import (
    AppUserOut,
    HoldingOut,
    InvestorFullProfile,
    InvestorOut,
    PortfolioSummary,
    SecurityOut,
)
from src.services import audit_service, registry_service

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/investors/{investor_id}", response_model=InvestorFullProfile)
async def get_investor_profile(
    investor_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    profile = registry_service.get_full_investor_profile(investor_id)
    if not profile:
        raise NotFoundError("Investor", investor_id)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="investor", resource_id=investor_id
    )
    await db.commit()
    return profile


@router.get("/investors/by-code/{investor_code}", response_model=InvestorOut)
async def get_investor_by_code(
    investor_code: str,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    investor = registry_service.get_investor_by_code(investor_code)
    if not investor:
        raise NotFoundError("Investor", investor_code)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="investor", detail=f"code={investor_code}"
    )
    await db.commit()
    return investor


@router.get("/investors", response_model=list[InvestorOut])
async def search_investors(
    name: str | None = None,
    national_id: str | None = None,
    investor_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    search_terms = " ".join(filter(None, [name, national_id, investor_type, status]))
    await audit_service.log_action(
        db, user_id=user.id, action="search", resource="investor",
        detail=f"query={search_terms} limit={limit}"
    )
    await db.commit()
    return registry_service.search_investors(
        name=name, national_id=national_id, investor_type=investor_type,
        status=status, limit=limit, offset=offset,
    )


@router.get("/investors/{investor_id}/holdings", response_model=list[HoldingOut])
async def get_investor_holdings(
    investor_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    investor = registry_service.get_investor_by_id(investor_id)
    if not investor:
        raise NotFoundError("Investor", investor_id)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="holdings", resource_id=investor_id
    )
    await db.commit()
    return registry_service.get_holdings(investor_id)


@router.get("/investors/{investor_id}/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary(
    investor_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    investor = registry_service.get_investor_by_id(investor_id)
    if not investor:
        raise NotFoundError("Investor", investor_id)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="portfolio",
        resource_id=investor_id
    )
    await db.commit()
    return registry_service.get_portfolio_summary(investor_id)


@router.get("/investors/{investor_id}/app-user", response_model=AppUserOut | None)
async def get_app_user(
    investor_id: int,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="app_user",
        resource_id=investor_id
    )
    await db.commit()
    return registry_service.get_app_user_by_investor(investor_id)


@router.get("/securities", response_model=list[SecurityOut])
async def list_securities(
    sector: str | None = None,
    limit: int = Query(default=50, le=250),
    offset: int = 0,
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    return registry_service.list_securities(sector=sector, limit=limit, offset=offset)


@router.get("/securities/by-ticker/{ticker}", response_model=SecurityOut)
async def get_security_by_ticker(
    ticker: str,
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    sec = registry_service.get_security_by_ticker(ticker.upper())
    if not sec:
        raise NotFoundError("Security", ticker)
    return sec


@router.get("/app-users/by-mobile/{mobile}", response_model=AppUserOut)
async def lookup_app_user_by_mobile(
    mobile: str,
    db: AsyncSession = Depends(get_cx_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    app_user = registry_service.get_app_user_by_mobile(mobile)
    if not app_user:
        raise NotFoundError("App User", mobile)
    await audit_service.log_action(
        db, user_id=user.id, action="read", resource="app_user", detail=f"mobile={mobile}"
    )
    await db.commit()
    return app_user
