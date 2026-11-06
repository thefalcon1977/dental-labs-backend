"""Users list and user profile/permissions/groups endpoints."""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_404,
    RESP_422,
    RESP_500,
    RESP_503,
)
from config.logging import get_logger

from ..dependencies.auth import get_current_user_or_system
from ..schemas.groups import UserGroupsListResponse
from ..schemas.roles import PermissionUpdateRequest, UserPermissionResponse
from ..schemas.user import UserInfo
from ..schemas.users import (
    UserGroupUpdateRequest,
    UserListParams,
    UserListResponse,
    UserProfileMainGroupUpdate,
)
from ..services import users_service

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


def get_user_list_params(
    search: str | None = Query(
        None,
        max_length=256,
        description="Search for username, first name, last name, or email.",
    ),
    username: str | None = Query(
        None,
        max_length=256,
        description="Filter by username.",
    ),
    first_name: str | None = Query(
        None,
        max_length=256,
        description="Filter by first name.",
    ),
    last_name: str | None = Query(
        None,
        max_length=256,
        description="Filter by last name.",
    ),
    email: str | None = Query(
        None,
        max_length=256,
        description="Filter by email.",
    ),
    phone_number: str | None = Query(
        None,
        max_length=256,
        description="Filter by phoneNumber (Keycloak custom attribute).",
    ),
    main_group: str | None = Query(
        None,
        max_length=256,
        description="Filter by mainGroup (Keycloak custom attribute).",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    enabled: bool | None = Query(
        None,
        description="Filter by enabled status.",
    ),
    group_id: str | None = Query(
        None,
        description="Filter users by Keycloak group ID (returns only members of this group).",
    ),
    include_groups: bool = Query(
        True,
        description="Include each user's groups in the response (groups field). Set false to omit.",
    ),
) -> UserListParams:
    """Build UserListParams from query parameters.

    Args:
        search: Search for username, first name, last name, or email.
        username: Filter by username.
        first_name: Filter by first name.
        last_name: Filter by last name.
        email: Filter by email.
        phone_number: Filter by phoneNumber (Keycloak custom attribute).
        main_group: Filter by mainGroup (Keycloak custom attribute).
        page: Page number (1-based).
        page_size: Items per page (max 100).
        enabled: Filter by enabled status.
        group_id: Filter users by Keycloak group ID (members only).
        include_groups: Include each user's groups in the response.

    Returns:
        UserListParams instance for list_users.
    """
    return UserListParams(
        search=search,
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        main_group=main_group,
        page=page,
        page_size=page_size,
        enabled=enabled,
        group_id=group_id,
        include_groups=include_groups,
    )


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users (full)",
    description=(
        "Return a paginated list of Keycloak users. Includes id, username, "
        "firstName, lastName, email, enabled, profile (from Keycloak attributes), "
        "requiredActions, realmRoles, clientRoles, createdTimestamp. "
        "Search/filter: search (username/firstName/lastName/email), username, "
        "first_name, last_name, email, phone_number, main_group (custom attributes). "
        "Optional: filter by group_id (returns only members of that group); "
        "set include_groups=true to include each user's groups. "
        "Uses Keycloak Admin API (client credentials)."
    ),
    responses={
        200: {"description": "Paginated list of users"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def list_users(
    params: UserListParams = Depends(get_user_list_params),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserListResponse:
    """List users with full Keycloak user information.

    Args:
        params: Query params (search, username, first_name, last_name, email,
            phone_number, main_group, page, page_size, enabled, group_id, include_groups)
        current_user: Authenticated user (injected)

    Returns:
        Paginated response (items + meta) with full user details
    """
    logger.debug(
        "Listing users",
        page=params.page,
        page_size=params.page_size,
        search=params.search,
        username=params.username,
        first_name=params.first_name,
        last_name=params.last_name,
        email=params.email,
        phone_number=params.phone_number,
        main_group=params.main_group,
    )
    return await users_service.list_users_detail(params)


@router.get(
    "/users/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Get user profile (Keycloak attributes and enabled flag) by user ID. Returns flat object (no 'profile' key).",
    response_class=ORJSONResponse,
    responses={
        200: {"description": "User profile (flat attributes)"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_user_profile(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> ORJSONResponse:
    """Get user profile (attributes) by user ID.

    Returns Keycloak user attributes as a flat JSON object (no "profile" wrapper).

    Args:
        user_id: Keycloak user ID.
        current_user: Authenticated user (injected).

    Returns:
        ORJSONResponse with flat profile dict (attributes as top-level keys).

    Raises:
        NotFoundError: If user not found.
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
    """
    result = await users_service.get_user_profile(user_id)
    return ORJSONResponse(content=result.model_dump())


@router.patch(
    "/users/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    summary="Update user profile (mainGroup and/or enabled)",
    description=(
        "Update mainGroup Keycloak custom attribute and/or user enabled flag. "
        'Body: { "mainGroup": "value" } or { "mainGroup": null } to clear; '
        '"enabled": true | false to allow or deny login. Omit fields to leave unchanged. '
        "Uses GET then PUT so other user fields and attributes are preserved."
    ),
    response_class=ORJSONResponse,
    responses={
        200: {"description": "Updated user profile"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def update_user_profile(
    user_id: str,
    body: UserProfileMainGroupUpdate,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> ORJSONResponse:
    """Update mainGroup attribute and/or enabled flag for the user.

    PATCH body: "mainGroup" to set or clear; "enabled" (bool) to allow or deny login.
    Omit fields to leave unchanged. Other profile attributes and user fields are preserved (GET → merge → PUT).

    Args:
        user_id: Keycloak user ID.
        body: mainGroup and/or enabled; omit to leave unchanged.
        current_user: Authenticated user (injected).

    Returns:
        ORJSONResponse with updated flat profile (attributes + enabled).

    Raises:
        NotFoundError: If user not found.
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
    """
    result = await users_service.update_user_profile_main_group(user_id, body)
    return ORJSONResponse(content=result.model_dump())


def _resolve_user_id(user_id: str, current_user: UserInfo) -> str:
    """Resolve user_id path: 'me' means current user's Keycloak ID."""
    if user_id == "me":
        return current_user.id
    return user_id


@router.get(
    "/users/{user_id}/permissions",
    response_model=UserPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user permissions",
    description="Get user effective permissions (composite realm roles only). Use user_id 'me' for current user.",
    responses={
        200: {"description": "User permissions"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_user_permission(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserPermissionResponse:
    """Get user effective permissions (realm + client roles)."""
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.get_user_permission(resolved_id)


@router.post(
    "/users/{user_id}/permissions",
    response_model=UserPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add user permissions",
    description=(
        "Add realm role mappings to a user. "
        "Body: realm_roles (list of role names). "
        "Use user_id 'me' to add permissions to the current user."
    ),
    responses={
        200: {"description": "User permissions after add"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserPermissionResponse:
    """Add permissions (realm roles) to a user.

    Args:
        user_id: Keycloak user ID (or 'me' for current user).
        body: Realm role names to add.
        current_user: Authenticated user (injected).

    Returns:
        User permission response after add.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If user or any role not found.
    """
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.add_user_permissions(resolved_id, body)


@router.patch(
    "/users/{user_id}/permissions",
    response_model=UserPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Set user permissions",
    description=(
        "Replace the user's realm role mappings with the provided list. "
        "Body: realm_roles (list of role names). "
        "Use user_id 'me' to set permissions for the current user."
    ),
    responses={
        200: {"description": "User permissions after replace"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def set_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserPermissionResponse:
    """Set permissions (realm roles) for a user.

    Args:
        user_id: Keycloak user ID (or 'me' for current user).
        body: Desired realm role names (final set).
        current_user: Authenticated user (injected).

    Returns:
        User permission response after replace.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If user or any role not found.
    """
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.set_user_permissions(resolved_id, body)


@router.delete(
    "/users/{user_id}/permissions",
    response_model=UserPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove user permissions",
    description=(
        "Remove realm role mappings from a user. "
        "Body: realm_roles (list of role names). "
        "Use user_id 'me' to remove permissions from the current user."
    ),
    responses={
        200: {"description": "User permissions after remove"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_user_permissions(
    user_id: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserPermissionResponse:
    """Remove permissions (realm + client roles) from a user."""
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.remove_user_permissions(resolved_id, body)


@router.get(
    "/users/{user_id}/groups",
    response_model=UserGroupsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user groups",
    description="Get groups the user is a member of (paginated).",
    responses={
        200: {"description": "Paginated list of user groups"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_user_groups(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserGroupsListResponse:
    """Get groups the user belongs to (paginated).

    Args:
        user_id: Keycloak user ID (or 'me' for current user).
        page: Page number (1-based).
        page_size: Items per page (max 100).
        current_user: Authenticated user (injected).

    Returns:
        Paginated response (items + meta) with user's groups.
    """
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.get_user_groups(
        user_id=resolved_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/users/by-username/{username}/groups",
    response_model=UserGroupsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user groups by username",
    description=(
        "Get groups for a user identified by username (paginated). "
        "Optional search uses comma-separated `groups` with `filter_type` "
        "set to `exact` or `contains`. "
        "Time: O(g) · Space: O(g), where g = user's groups when search is used."
    ),
    responses={
        200: {"description": "Paginated list of user groups"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_user_groups_by_username(
    username: str,
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    groups: str | None = Query(
        None,
        description="Nullable comma-separated group search terms (e.g. admins,finance).",
    ),
    filter_type: str = Query(
        "contains",
        description="Group search mode: exact or contains.",
    ),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserGroupsListResponse:
    """Get groups by username with optional group search filters.

    Args:
        username: Keycloak username.
        page: Page number (1-based).
        page_size: Items per page (max 100).
        groups: Nullable comma-separated group terms.
        filter_type: Search mode ("exact" or "contains").
        current_user: Authenticated user (injected).

    Returns:
        Paginated response (items + meta) with user's groups.
    """
    return await users_service.get_user_groups_by_username(
        username=username,
        page=page,
        page_size=page_size,
        groups=groups,
        filter_type=filter_type,
    )


@router.post(
    "/users/{user_id}/groups",
    response_model=UserGroupsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Add group to user",
    description="Add a group to a user. Body: group_id. Use user_id 'me' for current user.",
    responses={
        200: {"description": "User groups after add"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_user_group(
    user_id: str,
    body: UserGroupUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserGroupsListResponse:
    """Add a group to a user.

    Args:
        user_id: Keycloak user ID (or 'me' for current user).
        body: Group ID to add.
        current_user: Authenticated user (injected).

    Returns:
        User groups list response after add.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If user or group not found.
    """
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.add_user_group(resolved_id, body.group_id)


@router.delete(
    "/users/{user_id}/groups",
    response_model=UserGroupsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove group from user",
    description="Remove a group from a user. Body: group_id. Use user_id 'me' for current user.",
    responses={
        200: {"description": "User groups after remove"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_user_group(
    user_id: str,
    body: UserGroupUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> UserGroupsListResponse:
    """Remove a group from a user.

    Args:
        user_id: Keycloak user ID (or 'me' for current user).
        body: Group ID to remove.
        current_user: Authenticated user (injected).

    Returns:
        User groups list response after remove.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If user or group not found.
    """
    resolved_id = _resolve_user_id(user_id, current_user)
    return await users_service.remove_user_group(resolved_id, body.group_id)
