"""Service for Keycloak groups list with full representation.

Uses Keycloak Admin API list_groups; maps raw GroupRepresentation to GroupDetail
without attributes or access. Also provides group members by id or name,
add/remove member, and add/remove permissions.
"""

import asyncio

import httpx

from apps.core.exceptions import NotFoundError
from config.logging import get_logger

from ..helpers.exceptions import KeycloakConnectionError
from ..schemas.groups import (
    GroupCreate,
    GroupDetail,
    GroupListParams,
    GroupListResponse,
    GroupMembersListResponse,
    GroupUpdate,
    UserBrief,
)
from ..schemas.roles import (
    GroupPermissionResponse,
    PermissionUpdateRequest,
    role_raw_to_item,
)
from ..types import GroupDetailList, RawKeycloakDict, RawKeycloakList, StringList
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


def _raw_to_group_detail(raw: RawKeycloakDict) -> GroupDetail:
    """Map Keycloak group representation dict to GroupDetail.

    Attributes and access are not included. Nested subGroups are mapped
    recursively with the same filter.

    Args:
        raw: Raw group dict from Keycloak Admin API

    Returns:
        GroupDetail instance
    """
    sub_groups_raw = raw.get("subGroups")
    sub_groups: GroupDetailList | None = None
    if sub_groups_raw:
        sub_groups = [_raw_to_group_detail(sg) for sg in sub_groups_raw]

    data: RawKeycloakDict = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "path": raw.get("path"),
        "description": raw.get("description"),
        "parentId": raw.get("parentId"),
        "subGroupCount": raw.get("subGroupCount"),
        "realmRoles": raw.get("realmRoles"),
        "clientRoles": raw.get("clientRoles"),
    }
    if sub_groups is not None:
        data["subGroups"] = [sg.model_dump(by_alias=True) for sg in sub_groups]
    return GroupDetail.model_validate(data)


async def list_groups_detail(params: GroupListParams) -> GroupListResponse:
    """Return a paginated list of groups with full Keycloak representation.

    Uses Keycloak Admin API (client_credentials). Each item includes id, name,
    path, description, parentId, subGroups, subGroupCount, realmRoles,
    clientRoles (no attributes or access).

    Args:
        params: List params (search, page, page_size)

    Returns:
        Paginated response (items + meta)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
    """
    client = _get_client()

    first = (params.page - 1) * params.page_size
    search = (params.search or "").strip() or None

    groups, total_items = await asyncio.gather(
        client.list_groups(
            first=first,
            max_=params.page_size,
            search=search,
        ),
        client.count_groups(search=search),
    )

    items = [_raw_to_group_detail(g) for g in groups]
    return GroupListResponse.create(
        items=items,
        page=params.page,
        page_size=params.page_size,
        total_items=total_items,
    )


async def create_group(body: GroupCreate) -> GroupDetail:
    """Create a top-level Keycloak group.

    Args:
        body: Group creation data (name only).

    Returns:
        Created group as GroupDetail.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        ConflictError: If group with same name already exists
    """
    client = _get_client()
    payload: RawKeycloakDict = {"name": body.name}
    raw = await client.create_group(payload)
    return _raw_to_group_detail(raw)


async def update_group(group_id: str, body: GroupUpdate) -> GroupDetail:
    """Update a Keycloak group by ID.

    Only provided fields are updated. Uses GET → merge → PUT to avoid wiping
    other group fields. Returns the updated group.

    Args:
        group_id: Keycloak group ID.
        body: Group update payload.

    Returns:
        Updated group as GroupDetail.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group not found.
    """
    client = _get_client()
    try:
        raw = await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    if body.name is not None:
        raw["name"] = body.name
    if body.description is not None:
        raw["description"] = body.description

    await client.update_group(group_id, raw)
    updated = await client.get_group(group_id)
    return _raw_to_group_detail(updated)


async def update_group_by_name(group_name: str, body: GroupUpdate) -> GroupDetail:
    """Update a Keycloak group by exact group name.

    Args:
        group_name: Keycloak group name (exact match).
        body: Group update payload.

    Returns:
        Updated group as GroupDetail.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group not found.
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    return await update_group(group_id, body)


async def delete_group(group_id: str) -> None:
    """Delete a Keycloak group by ID.

    Args:
        group_id: Keycloak group ID.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group not found.
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    await client.delete_group(group_id)


async def delete_group_by_name(group_name: str) -> None:
    """Delete a Keycloak group by exact group name.

    Args:
        group_name: Keycloak group name (exact match).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group not found.
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    await delete_group(group_id)


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


async def get_group_members_by_id(
    group_id: str,
    page: int = 1,
    page_size: int = 20,
) -> GroupMembersListResponse:
    """Get group members by group ID (paginated).

    Args:
        group_id: Keycloak group ID
        page: Page number (1-based)
        page_size: Items per page (max 100)

    Returns:
        Paginated response (items + meta). Total is best-effort when Keycloak
        does not provide count.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    first = (page - 1) * page_size
    members_raw = await client.get_group_members(group_id, first=first, max_=page_size)
    items = [UserBrief.model_validate(m) for m in members_raw]
    total_items = _best_effort_total(page, page_size, len(items))
    return GroupMembersListResponse.create(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )


async def get_group_permission(group_id: str) -> GroupPermissionResponse:
    """Get group effective permissions (composite realm roles only).

    Args:
        group_id: Keycloak group ID

    Returns:
        GroupPermissionResponse with realm_roles

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    realm_roles_raw = await client.get_group_composite_realm_roles(group_id)
    realm_roles = [role_raw_to_item(r) for r in realm_roles_raw]

    return GroupPermissionResponse(realm_roles=realm_roles)


async def get_group_permission_by_name(group_name: str) -> GroupPermissionResponse:
    """Get group effective permissions by exact group name (composite realm roles).

    Args:
        group_name: Keycloak group name (exact match).

    Returns:
        GroupPermissionResponse with realm_roles.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group not found.
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    return await get_group_permission(group_id)


async def get_group_members_by_name(
    group_name: str,
    page: int = 1,
    page_size: int = 20,
) -> GroupMembersListResponse:
    """Get group members by group name (paginated).

    Finds the group by exact name match (searches top-level and nested),
    then returns its members.

    Args:
        group_name: Group name (exact match)
        page: Page number (1-based)
        page_size: Items per page (max 100)

    Returns:
        Paginated response (items + meta). Total is best-effort when Keycloak
        does not provide count.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group not found
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)

    group_id = group.get("id", "")
    first = (page - 1) * page_size
    members_raw = await client.get_group_members(group_id, first=first, max_=page_size)
    items = [UserBrief.model_validate(m) for m in members_raw]
    total_items = _best_effort_total(page, page_size, len(items))
    return GroupMembersListResponse.create(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )


async def _resolve_realm_roles_to_raw(
    client: KeycloakClient, role_names: StringList
) -> RawKeycloakList:
    """Resolve realm role names to Keycloak role representation dicts.

    Raises:
        NotFoundError: If any role name is not found
    """
    result: RawKeycloakList = []
    for name in role_names:
        role = await client.get_realm_role_by_name(name)
        if role is None:
            raise NotFoundError(resource="Realm role", identifier=name)
        result.append(role)
    return result


async def add_group_member_by_id(group_id: str, user_id: str) -> None:
    """Add a user to a group by group ID.

    Args:
        group_id: Keycloak group ID
        user_id: Keycloak user ID to add

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or user not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    await client.add_user_to_group(user_id, group_id)


async def remove_group_member_by_id(group_id: str, user_id: str) -> None:
    """Remove a user from a group by group ID.

    Args:
        group_id: Keycloak group ID
        user_id: Keycloak user ID to remove

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or user not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    await client.remove_user_from_group(user_id, group_id)


async def add_group_member_by_name(group_name: str, user_id: str) -> None:
    """Add a user to a group by group name.

    Args:
        group_name: Keycloak group name (exact match)
        user_id: Keycloak user ID to add

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or user not found
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    await client.add_user_to_group(user_id, group_id)


async def remove_group_member_by_name(group_name: str, user_id: str) -> None:
    """Remove a user from a group by group name.

    Args:
        group_name: Keycloak group name (exact match)
        user_id: Keycloak user ID to remove

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or user not found
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    await client.remove_user_from_group(user_id, group_id)


async def add_group_permission(
    group_id: str, body: PermissionUpdateRequest
) -> GroupPermissionResponse:
    """Add realm role mappings to a group.

    Args:
        group_id: Keycloak group ID
        body: Realm role names to add

    Returns:
        Group permission response after add

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or any role not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    if body.realm_roles:
        realm_raw = await _resolve_realm_roles_to_raw(client, body.realm_roles)
        await client.add_group_realm_role_mappings(group_id, realm_raw)

    return await get_group_permission(group_id)


async def add_group_permission_by_name(
    group_name: str,
    body: PermissionUpdateRequest,
) -> GroupPermissionResponse:
    """Add realm role mappings to a group by exact group name.

    Args:
        group_name: Keycloak group name (exact match).
        body: Realm role names to add.

    Returns:
        Group permission response after add.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or any role not found.
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    return await add_group_permission(group_id, body)


async def remove_group_permission(
    group_id: str, body: PermissionUpdateRequest
) -> GroupPermissionResponse:
    """Remove realm role mappings from a group.

    Args:
        group_id: Keycloak group ID
        body: Realm role names to remove

    Returns:
        Group permission response after remove

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group or any role not found
    """
    client = _get_client()
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    if body.realm_roles:
        realm_raw = await _resolve_realm_roles_to_raw(client, body.realm_roles)
        await client.delete_group_realm_role_mappings(group_id, realm_raw)

    return await get_group_permission(group_id)


async def remove_group_permission_by_name(
    group_name: str,
    body: PermissionUpdateRequest,
) -> GroupPermissionResponse:
    """Remove realm role mappings from a group by exact group name.

    Args:
        group_name: Keycloak group name (exact match).
        body: Realm role names to remove.

    Returns:
        Group permission response after remove.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or any role not found.
    """
    client = _get_client()
    group = await client.find_group_by_name(group_name)
    if group is None:
        raise NotFoundError(resource="Group", identifier=group_name)
    group_id = group.get("id", "")
    return await remove_group_permission(group_id, body)
