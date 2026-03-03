from src.core.permissions import FIELD_MASKS, ROLE_PERMISSIONS, Action, Resource


def has_permission(role_name: str, resource: Resource, action: Action) -> bool:
    perms = ROLE_PERMISSIONS.get(role_name, set())
    return (resource, action) in perms


def get_field_mask(role_name: str, resource: str) -> list[str] | None:
    """Return the list of allowed fields for a given role and resource.

    Returns None if no mask is configured (i.e. all fields visible).
    """
    masks = FIELD_MASKS.get(role_name, {})
    return masks.get(resource)


def apply_field_mask(data: dict, allowed_fields: list[str] | None) -> dict:
    if allowed_fields is None:
        return data
    return {k: v for k, v in data.items() if k in allowed_fields}
