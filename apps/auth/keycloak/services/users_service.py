"""Service for Keycloak users list with full representation.

Uses Keycloak Admin API list_users; maps raw UserRepresentation to UserDetail
with profile (from attributes) and without totp, federationLink, access, etc.
Also provides user profile, permissions, and groups.
"""

import asyncio

import httpx

from apps.core.exceptions import NotFoundError, ValidationError
from config.logging import get_logger

from ..helpers.exceptions import KeycloakConnectionError
from ..schemas.groups import GroupBrief, UserGroupsListResponse
from ..schemas.roles import (
    PermissionUpdateRequest,
    UserPermissionResponse,
    role_raw_to_item,
)
from ..schemas.users import (
    UserDetail,
    UserListParams,
    UserListResponse,
    UserProfileFlat,
    UserProfileMainGroupUpdate,
    UserProfileUpdate,
)
from ..types import (
    GroupBriefNestedList,
    ProfileDict,
    RawKeycloakDict,
    RawKeycloakList,
    RawKeycloakListList,
    StringList,
    UserDetailList,
)
from ..utils.keycloak_client import KeycloakClient, get_keycloak_client

logger = get_logger(__name__)

# Max concurrent Keycloak Admin API calls when fetching user groups (avoids ConnectTimeout)
_MAX_CONCURRENT_GROUP_FETCHES = 5


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


def _raw_to_user_detail(raw: RawKeycloakDict) -> UserDetail:
    """Map Keycloak user representation dict to UserDetail.

    Keycloak 'attributes' is mapped to 'profile'. Removed keys (totp,
    federationLink, disableableCredentialTypes, notBefore, access, origin, self)
    are not passed through.

    Args:
        raw: Raw user dict from Keycloak Admin API

    Returns:
        UserDetail instance
    """
    data: RawKeycloakDict = {
        "id": raw.get("id", ""),
        "username": raw.get("username"),
        "firstName": raw.get("firstName"),
        "lastName": raw.get("lastName"),
        "email": raw.get("email"),
        "emailVerified": raw.get("emailVerified"),
        "enabled": raw.get("enabled"),
        "createdTimestamp": raw.get("createdTimestamp"),
        "requiredActions": raw.get("requiredActions"),
        "realmRoles": raw.get("realmRoles"),
        "clientRoles": raw.get("clientRoles"),
    }
    if "attributes" in raw and raw["attributes"] is not None:
        data["profile"] = raw["attributes"]
    return UserDetail.model_validate(data)


def _raw_to_group_brief(raw: RawKeycloakDict) -> GroupBrief:
    """Map Keycloak group dict to GroupBrief.

    Args:
        raw: Raw group dict from Keycloak API.

    Returns:
        GroupBrief instance (id, name, path).
    """
    return GroupBrief(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        path=raw.get("path"),
    )


async def _attach_groups_to_users(
    client: KeycloakClient,
    items: UserDetailList,
) -> UserDetailList:
    """Fetch each user's groups in parallel with throttling and attach to UserDetail.

    Uses semaphore to limit concurrent Keycloak API calls to prevent timeouts.
    Limits concurrent requests to _MAX_CONCURRENT_GROUP_FETCHES (5) to avoid
    overwhelming Keycloak when fetching groups for many users.

    Args:
        client: Keycloak client
        items: List of UserDetail (without groups)

    Returns:
        List of UserDetail with groups populated
    """
    if not items:
        return items

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_GROUP_FETCHES)

    async def fetch_with_throttle(user_id: str) -> RawKeycloakList:
        """Fetch user groups with semaphore throttling.

        Args:
            user_id: Keycloak user ID

        Returns:
            List of group representation dicts
        """
        async with semaphore:
            try:
                return await client.get_user_groups(user_id=user_id, first=0, max_=500)
            except Exception as e:
                logger.warning(
                    "Failed to fetch groups for user",
                    user_id=user_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Return empty list on error to prevent breaking entire request
                return []

    groups_per_user: RawKeycloakListList = await asyncio.gather(
        *[fetch_with_throttle(u.id) for u in items],
    )

    group_briefs_per_user: GroupBriefNestedList = [
        [_raw_to_group_brief(g) for g in gu] for gu in groups_per_user
    ]

    return [
        u.model_copy(update={"groups": gb})
        for u, gb in zip(items, group_briefs_per_user)
    ]


def _build_q_param(phone_number: str | None, main_group: str | None) -> str | None:
    """Build Keycloak q param for custom attributes (phoneNumber, mainGroup).

    Format: space-separated "key:value" pairs. Keycloak 15.1+.
    """
    parts: StringList = []
    if (phone_number or "").strip():
        parts.append(f"phoneNumber:{phone_number.strip()}")
    if (main_group or "").strip():
        parts.append(f"mainGroup:{main_group.strip()}")
    return " ".join(parts) if parts else None


async def list_users_detail(params: UserListParams) -> UserListResponse:
    """Return a paginated list of users with full Keycloak representation.

    Uses Keycloak Admin API (client_credentials). Each item includes id,
    username, firstName, lastName, email, enabled, profile (from attributes),
    requiredActions, realmRoles, clientRoles, createdTimestamp.
    When group_id is set, returns only members of that group (via group members API).
    When include_groups is True, each item includes a groups field.

    Args:
        params: List params (search, username, first_name, last_name, email,
            phone_number, main_group, page, page_size, enabled, group_id, include_groups)

    Returns:
        Paginated response (items + meta)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If group_id is set and group not found
    """
    client = _get_client()
    first = (params.page - 1) * params.page_size
    search = (params.search or "").strip() or None
    username = (params.username or "").strip() or None
    first_name = (params.first_name or "").strip() or None
    last_name = (params.last_name or "").strip() or None
    email = (params.email or "").strip() or None
    q = _build_q_param(params.phone_number, params.main_group)

    if params.group_id:
        try:
            await client.get_group(params.group_id)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                raise NotFoundError(
                    resource="Group",
                    identifier=params.group_id,
                ) from e
            raise KeycloakConnectionError() from e
        users_raw = await client.get_group_members(
            params.group_id,
            first=first,
            max_=params.page_size,
        )
        total_items = _best_effort_total(
            params.page,
            params.page_size,
            len(users_raw),
        )
        items = [_raw_to_user_detail(u) for u in users_raw]
    else:
        users, total_items = await asyncio.gather(
            client.list_users(
                first=first,
                max_=params.page_size,
                search=search,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                q=q,
                enabled=params.enabled,
            ),
            client.count_users(
                search=search,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                q=q,
                enabled=params.enabled,
            ),
        )
        items = [_raw_to_user_detail(u) for u in users]

    if params.include_groups and items:
        items = await _attach_groups_to_users(client, items)

    return UserListResponse.create(
        items=items,
        page=params.page,
        page_size=params.page_size,
        total_items=total_items,
    )


async def get_user_profile(user_id: str) -> UserProfileFlat:
    """Get user profile (attributes and enabled) by user ID as flat dict.

    Args:
        user_id: Keycloak user ID

    Returns:
        UserProfileFlat: attributes and enabled as top-level JSON (no "profile" key)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user not found
    """
    client = _get_client()
    try:
        raw = await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e
    profile: ProfileDict = raw.get("attributes") or {}
    return UserProfileFlat(enabled=raw.get("enabled"), **profile)


async def update_user_profile(user_id: str, body: UserProfileUpdate) -> UserProfileFlat:
    """Update user profile (attributes) by user ID.

    Args:
        user_id: Keycloak user ID
        body: Profile update (profile dict)

    Returns:
        UserProfileFlat: attributes dict as top-level JSON (no "profile" key)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e
    if body.profile is not None:
        await client.update_user(user_id, {"attributes": body.profile})
    return await get_user_profile(user_id)


async def update_user_profile_main_group(
    user_id: str,
    body: UserProfileMainGroupUpdate,
) -> UserProfileFlat:
    """Update mainGroup attribute and/or Keycloak user enabled flag.

    GETs the user, merges mainGroup into attributes and optionally sets enabled,
    PUTs full user so other fields are not wiped. Keycloak has no PATCH; PUT is full replace.

    Args:
        user_id: Keycloak user ID
        body: main_group (mainGroup) to set or clear; enabled to set or leave unchanged

    Returns:
        UserProfileFlat: attributes and enabled as top-level JSON (no "profile" key)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user not found
        ValidationError: If mainGroup is not one of the user's groups
    """
    client = _get_client()
    try:
        raw: RawKeycloakDict = await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    if body.main_group is not None:
        user_groups: RawKeycloakList = await client.get_user_groups(
            user_id, first=0, max_=500
        )
        main_group_value = (body.main_group or "").strip()
        matches = False
        for group in user_groups:
            if not isinstance(group, dict):
                continue
            gid = group.get("id")
            name = group.get("name")
            path = group.get("path")
            if main_group_value in (gid, name, path):
                matches = True
                break
        if not matches:
            raise ValidationError(
                message="mainGroup must be one of the user's groups",
                details={"mainGroup": body.main_group},
            )

    attrs: ProfileDict = {}
    existing = raw.get("attributes")
    if existing and isinstance(existing, dict):
        for k, v in existing.items():
            if isinstance(v, list):
                attrs[k] = list(v)
            else:
                attrs[k] = [str(v)]

    if body.main_group is not None:
        attrs["mainGroup"] = [body.main_group]
    else:
        attrs["mainGroup"] = []

    raw["attributes"] = attrs
    if body.enabled is not None:
        raw["enabled"] = body.enabled
    await client.update_user(user_id, raw)
    return await get_user_profile(user_id)


async def get_user_permission(user_id: str) -> UserPermissionResponse:
    """Get user effective permissions (composite realm roles only).

    Args:
        user_id: Keycloak user ID

    Returns:
        UserPermissionResponse with realm_roles

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    realm_roles_raw = await client.get_user_composite_realm_roles(user_id)
    realm_roles = [role_raw_to_item(r) for r in realm_roles_raw]

    return UserPermissionResponse(realm_roles=realm_roles)


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


async def add_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
) -> UserPermissionResponse:
    """Add realm role mappings to a user.

    Args:
        user_id: Keycloak user ID
        body: Realm role names to add

    Returns:
        User permission response after add

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user or any role not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    if body.realm_roles:
        realm_raw = await _resolve_realm_roles_to_raw(client, body.realm_roles)
        await client.add_user_realm_role_mappings(user_id, realm_raw)

    return await get_user_permission(user_id)


async def remove_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
) -> UserPermissionResponse:
    """Remove realm role mappings from a user.

    Args:
        user_id: Keycloak user ID
        body: Realm role names to remove

    Returns:
        User permission response after remove

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user or any role not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    if body.realm_roles:
        realm_raw = await _resolve_realm_roles_to_raw(client, body.realm_roles)
        await client.delete_user_realm_role_mappings(user_id, realm_raw)

    return await get_user_permission(user_id)


async def set_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
) -> UserPermissionResponse:
    """Set a user's realm role mappings to exactly the provided list.

    This endpoint is exposed as PATCH /auth/users/{user_id}/permissions.
    Keycloak does not provide a PATCH for role mappings, so we implement
    replacement by diffing:
    - remove roles currently assigned but not requested
    - add roles requested but not currently assigned

    Args:
        user_id: Keycloak user ID.
        body: Desired realm role names (final set).

    Returns:
        UserPermissionResponse after the update (effective composite roles).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If user or any requested role is not found.
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    desired_names = {name.strip() for name in body.realm_roles if name.strip()}

    current_raw = await client.get_user_realm_role_mappings(user_id)
    current_name_to_raw: dict[str, RawKeycloakDict] = {}
    for role in current_raw:
        if not isinstance(role, dict):
            continue
        role_name = role.get("name")
        if isinstance(role_name, str):
            current_name_to_raw[role_name] = role
    current_names = set(current_name_to_raw.keys())

    names_to_remove = current_names - desired_names
    names_to_add = desired_names - current_names

    roles_to_remove = [current_name_to_raw[name] for name in names_to_remove]
    if roles_to_remove:
        await client.delete_user_realm_role_mappings(user_id, roles_to_remove)

    if names_to_add:
        role_names_to_add: StringList = sorted(names_to_add)
        roles_to_add = await _resolve_realm_roles_to_raw(client, role_names_to_add)
        await client.add_user_realm_role_mappings(user_id, roles_to_add)

    return await get_user_permission(user_id)


def _best_effort_total(page: int, page_size: int, items_count: int) -> int:
    """Compute best-effort total when backend does not return count.

    If returned items are fewer than page_size, total is (page - 1) * page_size +
    items_count; otherwise page * page_size.

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


async def get_user_groups(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> UserGroupsListResponse:
    """Get groups the user is a member of (paginated).

    Args:
        user_id: Keycloak user ID
        page: Page number (1-based)
        page_size: Items per page (max 100)

    Returns:
        Paginated response (items + meta). Total is best-effort when Keycloak
        does not provide count.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e

    first = (page - 1) * page_size
    groups_raw = await client.get_user_groups(user_id, first=first, max_=page_size)
    items = [
        GroupBrief(
            id=g.get("id", ""),
            name=g.get("name", ""),
            path=g.get("path"),
        )
        for g in groups_raw
    ]
    total_items = _best_effort_total(page, page_size, len(items))
    return UserGroupsListResponse.create(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )


def _parse_csv_values(csv_value: str | None) -> StringList:
    """Parse a comma-separated string into normalized values.

    Args:
        csv_value: Optional comma-separated string.

    Returns:
        Trimmed non-empty values.
    """
    if csv_value is None:
        return []
    return [value.strip() for value in csv_value.split(",") if value.strip()]


def _group_matches_search_terms(
    group: GroupBrief,
    terms: StringList,
    filter_type: str,
) -> bool:
    """Check whether a group matches any search term.

    Args:
        group: Group to evaluate.
        terms: Search terms parsed from CSV.
        filter_type: Matching strategy ("exact" or "contains").

    Returns:
        True if group name/path matches according to strategy.
    """
    if not terms:
        return True

    group_name = (group.name or "").strip().casefold()
    group_path = (group.path or "").strip().casefold()
    normalized_terms = [term.casefold() for term in terms]

    if filter_type == "exact":
        return any(
            term == group_name or term == group_path for term in normalized_terms
        )
    return any(term in group_name or term in group_path for term in normalized_terms)


async def get_user_groups_by_username(
    username: str,
    page: int = 1,
    page_size: int = 20,
    groups: str | None = None,
    filter_type: str = "contains",
) -> UserGroupsListResponse:
    """Get groups by username with optional group-name filtering.

    Args:
        username: Keycloak username (exact match, case-insensitive).
        page: Page number (1-based).
        page_size: Items per page (max 100).
        groups: Optional comma-separated group search values.
        filter_type: Match mode for `groups` ("exact" or "contains").

    Returns:
        Paginated groups response (items + meta).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If no user with the exact username exists.
        ValidationError: If filter_type is invalid.
    """
    normalized_filter_type = (filter_type or "").strip().lower()
    if normalized_filter_type not in {"exact", "contains"}:
        raise ValidationError(
            message="filter_type must be 'exact' or 'contains'",
            details={"filter_type": filter_type},
        )

    normalized_username = username.strip()
    if not normalized_username:
        raise ValidationError(
            message="username cannot be empty",
            details={"username": username},
        )

    client = _get_client()
    users = await client.list_users(first=0, max_=100, username=normalized_username)
    user_id: str | None = None
    for user in users:
        raw_username = user.get("username")
        if (
            isinstance(raw_username, str)
            and raw_username.strip().casefold() == normalized_username.casefold()
        ):
            user_id = user.get("id")
            break

    if not user_id:
        raise NotFoundError(resource="User", identifier=normalized_username)

    search_terms = _parse_csv_values(groups)
    if not search_terms:
        return await get_user_groups(user_id=user_id, page=page, page_size=page_size)

    groups_raw = await client.get_user_groups(user_id=user_id, first=0, max_=500)
    all_items = [
        GroupBrief(
            id=group_raw.get("id", ""),
            name=group_raw.get("name", ""),
            path=group_raw.get("path"),
        )
        for group_raw in groups_raw
    ]
    filtered_items = [
        item
        for item in all_items
        if _group_matches_search_terms(item, search_terms, normalized_filter_type)
    ]

    total_items = len(filtered_items)
    first = (page - 1) * page_size
    paged_items = filtered_items[first : first + page_size]

    return UserGroupsListResponse.create(
        items=paged_items,
        page=page,
        page_size=page_size,
        total_items=total_items,
    )


async def add_user_group(user_id: str, group_id: str) -> UserGroupsListResponse:
    """Add a group to a user.

    Args:
        user_id: Keycloak user ID
        group_id: Keycloak group ID to add

    Returns:
        User groups list response after add (first page)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user or group not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    await client.add_user_to_group(user_id, group_id)
    return await get_user_groups(user_id, page=1, page_size=20)


async def remove_user_group(user_id: str, group_id: str) -> UserGroupsListResponse:
    """Remove a group from a user.

    Args:
        user_id: Keycloak user ID
        group_id: Keycloak group ID to remove

    Returns:
        User groups list response after remove (first page)

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails
        NotFoundError: If user or group not found
    """
    client = _get_client()
    try:
        await client.get_user(user_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="User", identifier=user_id) from e
        raise KeycloakConnectionError() from e
    try:
        await client.get_group(group_id)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            raise NotFoundError(resource="Group", identifier=group_id) from e
        raise KeycloakConnectionError() from e

    await client.remove_user_from_group(user_id, group_id)
    return await get_user_groups(user_id, page=1, page_size=20)
