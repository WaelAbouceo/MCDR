from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.permissions import Action, Resource
from src.database import get_customer_db
from src.middleware.auth import RequirePermission
from src.middleware.field_mask import mask_response
from src.models.user import User
from src.schemas.customer import CustomerProfileOut
from src.services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/by-phone/{phone}", response_model=dict)
async def lookup_by_phone(
    phone: str,
    db: AsyncSession = Depends(get_customer_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    profile = await customer_service.lookup_by_phone(db, phone)
    if not profile:
        raise NotFoundError("Customer", phone)
    data = CustomerProfileOut.model_validate(profile).model_dump()
    return mask_response(data, role_name=user.role.name, resource="customer")


@router.get("/by-account/{account_number}", response_model=dict)
async def lookup_by_account(
    account_number: str,
    db: AsyncSession = Depends(get_customer_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    profile = await customer_service.lookup_by_account(db, account_number)
    if not profile:
        raise NotFoundError("Customer", account_number)
    data = CustomerProfileOut.model_validate(profile).model_dump()
    return mask_response(data, role_name=user.role.name, resource="customer")


@router.get("/{customer_id}", response_model=dict)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_customer_db),
    user: User = Depends(RequirePermission(Resource.CUSTOMER, Action.READ)),
):
    profile = await customer_service.get_customer(db, customer_id)
    if not profile:
        raise NotFoundError("Customer", customer_id)
    data = CustomerProfileOut.model_validate(profile).model_dump()
    return mask_response(data, role_name=user.role.name, resource="customer")
