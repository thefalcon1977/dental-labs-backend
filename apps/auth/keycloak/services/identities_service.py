"""Service for flat users-and-groups (identities) list from Keycloak Admin API."""

import asyncio

from config.logging import get_logger

from ..helpers.exceptions import KeycloakConnectionError
from ..schemas.identities import IdentityFlat, IdentityListParams, IdentityListResponse
from ..types import RawKeycloakDict
from ..utils.keycloak_client import get_keycloak_client

logger = get_logger(__name__)


def _user_to_identity(raw: RawKeycloakDict) -> IdentityFlat:
    """Map Keycloak user representation to IdentityFlat.

    Args:
        raw: Raw user dict from Keycloak API.

    Returns:
        IdentityFlat instance (id, name, username, type='user', etc.).
    """
    username = raw.get("username") or ""
    # Set name to username value (not first+last name)
    name = username
    return IdentityFlat(
        id=raw.get("id", ""),
        name=name,
        username=raw.get("username"),
        type="user",
        email=raw.get("email"),
        path=None,
        enabled=raw.get("enabled") if "enabled" in raw else None,
    )


def _group_to_identity(raw: RawKeycloakDict) -> IdentityFlat:
    """Map Keycloak group representation to IdentityFlat (top-level only).

    Args:
        raw: Raw group dict from Keycloak API.

    Returns:
        IdentityFlat instance (id, name, type='group', path, etc.).
    """
    return IdentityFlat(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        username=None,
        type="group",
        email=None,
        path=raw.get("path"),
        enabled=None,
    )


async def get_identities_flat(params: IdentityListParams) -> IdentityListResponse:
    """Return a flat, paginated list of users and/or groups from Keycloak.

    Uses Keycloak Admin API (client_credentials). Response shape matches
    standard list endpoints (items + meta with page, page_size, total_items,
    total_pages, has_next, has_previous). Total count is always fetched.

    Args:
        params: List params (type filter, search, page, page_size, etc.)

    Returns:
        Paginated response with items and meta.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
    """
    client = get_keycloak_client()
    if client is None:
        raise KeycloakConnectionError()

    page = params.page
    page_size = params.page_size
    first = (page - 1) * page_size
    search = (params.search or "").strip() or None
    enabled = params.enabled

    if params.type_filter == "user":
        users_fut = client.list_users(
            first=first,
            max_=page_size,
            search=search,
            enabled=enabled,
        )
        count_fut = client.count_users(search=search, enabled=enabled)
        users, total_items = await asyncio.gather(users_fut, count_fut)
        items = [_user_to_identity(u) for u in users]
        return IdentityListResponse.create(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    if params.type_filter == "group":
        groups_fut = client.list_groups(
            first=first,
            max_=page_size,
            search=search,
        )
        count_fut = client.count_groups(search=search)
        groups, total_items = await asyncio.gather(groups_fut, count_fut)
        items = [_group_to_identity(g) for g in groups]
        return IdentityListResponse.create(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    # type_filter == "all": fetch users and groups in parallel, then counts
    users_fut = client.list_users(
        first=first,
        max_=page_size,
        search=search,
        enabled=enabled,
    )
    groups_fut = client.list_groups(
        first=first,
        max_=page_size,
        search=search,
    )
    count_users_fut = client.count_users(search=search, enabled=enabled)
    count_groups_fut = client.count_groups(search=search)
    users, groups, total_users, total_groups = await asyncio.gather(
        users_fut, groups_fut, count_users_fut, count_groups_fut
    )

    identities = [_user_to_identity(u) for u in users]
    identities.extend(_group_to_identity(g) for g in groups)
    identities.sort(key=lambda p: p.name.lower())
    identities = identities[:page_size]
    total_items = total_users + total_groups

    return IdentityListResponse.create(
        items=identities,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )
