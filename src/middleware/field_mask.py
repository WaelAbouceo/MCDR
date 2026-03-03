"""Utility to strip fields from API responses based on the caller's RBAC role."""

from src.services.rbac_service import apply_field_mask, get_field_mask


def mask_response(data: dict | list[dict], *, role_name: str, resource: str) -> dict | list[dict]:
    allowed = get_field_mask(role_name, resource)
    if allowed is None:
        return data
    if isinstance(data, list):
        return [apply_field_mask(item, allowed) for item in data]
    return apply_field_mask(data, allowed)
