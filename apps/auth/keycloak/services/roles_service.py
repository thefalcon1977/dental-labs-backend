"""Service for Keycloak realm roles list and create/delete."""

from config.logging import get_logger

from ..helpers.exceptions import KeycloakConnectionError
from ..schemas.roles import (
    PermissionCreateRequest,
    RealmRolesListResponse,
    RoleItem,
    role_raw_to_item,
)
from ..types import RoleCreateDict
from ..utils.keycloak_client import KeycloakClient, get_keycloak_client

logger = get_logger(__name__)


def _get_client() -> KeycloakClient:
    """Get Keycloak client or raise.

    Returns:
        Keycloak client instance.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or client is None.
    """
    client = get_keycloak_client()
    if client is None:
        raise KeycloakConnectionError()
    return client


def _best_effort_total(page: int, page_size: int, items_count: int) -> int:
    """Compute best-effort total when backend does not return count.

    If returned items are fewer than page_size, total is (page-1)*page_size +
    items_count; otherwise page*page_size.

    Args:
        page: Page number (1-based).
        page_size: Items per page.
        items_count: Number of items returned for this page.

    Returns:
        Best-effort total item count.
    """
    if items_count < page_size:
        return (page - 1) * page_size + items_count
    return page * page_size + 1


async def list_realm_roles(
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> RealmRolesListResponse:
    """Return realm roles (paginated).

    Uses Keycloak Admin API (client_credentials).

    Args:
        search: Optional filter by role name only (Keycloak searches name+description;
            we filter results to name only)
        page: Page number (1-based)
        page_size: Items per page (max 100)

    Returns:
        Paginated response (items + meta). Total is best-effort when Keycloak
        does not provide count.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
    """
    client = _get_client()
    first = (page - 1) * page_size
    roles_raw = await client.list_realm_roles(
        first=first,
        max_=page_size,
        search=search,
    )
    # Keycloak search matches name or description; filter to name only
    if search is not None and search.strip():
        needle = search.strip().lower()
        roles_raw = [r for r in roles_raw if needle in (r.get("name") or "").lower()]
    items = [role_raw_to_item(r) for r in roles_raw]
    total_items = _best_effort_total(page, page_size, len(items))
    return RealmRolesListResponse.create(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )


async def create_realm_role(body: PermissionCreateRequest) -> RoleItem:
    """Create a realm role (permission) in Keycloak.

    Args:
        body: Name and optional description

    Returns:
        Created role as RoleItem (fetched by name after create)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        ConflictError: If a role with the same name already exists
    """
    client = _get_client()
    role_dict: RoleCreateDict = {"name": body.name}
    if body.description is not None:
        role_dict["description"] = body.description
    await client.create_realm_role(role_dict)
    created = await client.get_realm_role_by_name(body.name)
    if created is None:
        raise KeycloakConnectionError()
    return role_raw_to_item(created)


async def delete_realm_role(role_name: str) -> None:
    """Delete a realm role (permission) by name in Keycloak.

    Args:
        role_name: Realm role name

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
    """
    client = _get_client()
    await client.delete_realm_role_by_name(role_name)
