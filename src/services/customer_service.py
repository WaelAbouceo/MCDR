"""Read-only customer profile lookups against the isolated customer data zone."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.customer import CustomerProfile
from src.services.rbac_service import apply_field_mask, get_field_mask


async def lookup_by_phone(db: AsyncSession, phone: str) -> CustomerProfile | None:
    stmt = select(CustomerProfile).where(CustomerProfile.phone_number == phone)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def lookup_by_account(db: AsyncSession, account_number: str) -> CustomerProfile | None:
    stmt = select(CustomerProfile).where(CustomerProfile.account_number == account_number)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_customer(db: AsyncSession, customer_id: int) -> CustomerProfile | None:
    return await db.get(CustomerProfile, customer_id)


def mask_profile(profile_dict: dict, role_name: str) -> dict:
    allowed = get_field_mask(role_name, "customer")
    return apply_field_mask(profile_dict, allowed)
