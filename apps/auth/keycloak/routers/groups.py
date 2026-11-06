"""Groups list and group members endpoints."""

from fastapi import APIRouter, Depends, Query, status

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_404,
    RESP_409,
    RESP_422,
    RESP_500,
    RESP_503,
)
from config.logging import get_logger

from ..dependencies.auth import get_current_user_or_system
from ..schemas.groups import (
    GroupCreate,
    GroupDetail,
    GroupListParams,
    GroupListResponse,
    GroupMembersListResponse,
    GroupMemberUpdateRequest,
    GroupUpdate,
)
from ..schemas.roles import GroupPermissionResponse, PermissionUpdateRequest
from ..schemas.user import UserInfo
from ..services import groups_service

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


def get_group_list_params(
    search: str | None = Query(
        None,
        max_length=256,
        description="Filter by group name.",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
) -> GroupListParams:
    """Build GroupListParams from query parameters.

    Args:
        search: Filter by group name.
        page: Page number (1-based).
        page_size: Items per page (max 100).

    Returns:
        GroupListParams instance for list_groups.
    """
    return GroupListParams(
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/groups",
    response_model=GroupListResponse,
    status_code=status.HTTP_200_OK,
    summary="List groups (full)",
    description=(
        "Return a paginated list of Keycloak groups. Includes id, name, path, "
        "description, parentId, subGroups, subGroupCount, realmRoles, clientRoles. "
        "Uses Keycloak Admin API (client credentials)."
    ),
    responses={
        200: {"description": "Paginated list of groups"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def list_groups(
    params: GroupListParams = Depends(get_group_list_params),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupListResponse:
    """List groups with full Keycloak group information.

    Args:
        params: Query params (search, page, page_size)
        current_user: Authenticated user (injected)

    Returns:
        Paginated response (items + meta) with full group details
    """
    logger.debug(
        "Listing groups",
        page=params.page,
        page_size=params.page_size,
    )
    return await groups_service.list_groups_detail(params)


@router.post(
    "/groups",
    response_model=GroupDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create group",
    description=(
        "Create a top-level Keycloak group. Body: name only. "
        "Uses Keycloak Admin API (client credentials)."
    ),
    responses={
        201: {"description": "Group created"},
        401: RESP_401,
        403: RESP_403,
        409: RESP_409,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def create_group(
    body: GroupCreate,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupDetail:
    """Create a top-level group.

    Args:
        body: Group creation data (name only)
        current_user: Authenticated user (injected)

    Returns:
        Created group (GroupDetail)
    """
    logger.debug("Creating group", name=body.name)
    return await groups_service.create_group(body)


@router.patch(
    "/groups/{group_id}",
    response_model=GroupDetail,
    status_code=status.HTTP_200_OK,
    summary="Update group",
    description=(
        "Update Keycloak group fields by group ID. "
        "Only provided fields are updated (currently: name, description). "
        "Uses GET then PUT so other group fields are preserved."
    ),
    responses={
        200: {"description": "Updated group"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def update_group(
    group_id: str,
    body: GroupUpdate,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupDetail:
    """Update a group by ID.

    Args:
        group_id: Keycloak group ID.
        body: Group update payload (only provided fields are changed).
        current_user: Authenticated user (injected).

    Returns:
        Updated group details.
    """
    logger.debug("Updating group", group_id=group_id)
    return await groups_service.update_group(group_id, body)


@router.patch(
    "/groups/by-name/{group_name}",
    response_model=GroupDetail,
    status_code=status.HTTP_200_OK,
    summary="Update group (by name)",
    description=(
        "Update Keycloak group fields by exact group name. "
        "Only provided fields are updated (currently: name, description)."
    ),
    responses={
        200: {"description": "Updated group"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def update_group_by_name(
    group_name: str,
    body: GroupUpdate,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupDetail:
    """Update a group by exact name."""
    logger.debug("Updating group by name", group_name=group_name)
    return await groups_service.update_group_by_name(group_name, body)


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete group",
    description="Delete a Keycloak group by group ID.",
    responses={
        204: {"description": "Group deleted"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def delete_group(
    group_id: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Delete a group by ID.

    Args:
        group_id: Keycloak group ID.
        current_user: Authenticated user (injected).
    """
    logger.debug("Deleting group", group_id=group_id)
    await groups_service.delete_group(group_id)


@router.delete(
    "/groups/by-name/{group_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete group (by name)",
    description="Delete a Keycloak group by exact group name.",
    responses={
        204: {"description": "Group deleted"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def delete_group_by_name(
    group_name: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Delete a group by exact name."""
    logger.debug("Deleting group by name", group_name=group_name)
    await groups_service.delete_group_by_name(group_name)


@router.get(
    "/groups/{group_id}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group permissions",
    description="Get group effective permissions (composite realm roles only).",
    responses={
        200: {"description": "Group permissions"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_group_permissions(
    group_id: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Get group effective permissions (realm + client roles)."""
    return await groups_service.get_group_permission(group_id)


@router.get(
    "/groups/by-name/{group_name}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group permissions (by name)",
    description="Get group effective permissions (composite realm roles only) by exact group name.",
    responses={
        200: {"description": "Group permissions"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_group_permissions_by_name(
    group_name: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Get group effective permissions (realm + client roles) by group name."""
    return await groups_service.get_group_permission_by_name(group_name)


@router.post(
    "/groups/{group_id}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add group permissions",
    description=(
        "Add realm role mappings to a group. Body: realm_roles (list of role names)."
    ),
    responses={
        200: {"description": "Group permissions after add"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_group_permissions(
    group_id: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Add permissions (realm roles) to a group.

    Args:
        group_id: Keycloak group ID.
        body: Realm role names to add.
        current_user: Authenticated user (injected).

    Returns:
        Group permission response after add.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or any role not found.
    """
    return await groups_service.add_group_permission(group_id, body)


@router.post(
    "/groups/by-name/{group_name}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Add group permissions (by name)",
    description="Add realm role mappings to a group by exact group name. Body: realm_roles (list of role names).",
    responses={
        200: {"description": "Group permissions after add"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_group_permissions_by_name(
    group_name: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Add permissions (realm roles) to a group by group name."""
    return await groups_service.add_group_permission_by_name(group_name, body)


@router.delete(
    "/groups/{group_id}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove group permissions",
    description=(
        "Remove realm role mappings from a group. "
        "Body: realm_roles (list of role names)."
    ),
    responses={
        200: {"description": "Group permissions after remove"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_group_permissions(
    group_id: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Remove permissions (realm roles) from a group.

    Args:
        group_id: Keycloak group ID.
        body: Realm role names to remove.
        current_user: Authenticated user (injected).

    Returns:
        Group permission response after remove.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or any role not found.
    """
    return await groups_service.remove_group_permission(group_id, body)


@router.delete(
    "/groups/by-name/{group_name}/permissions",
    response_model=GroupPermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove group permissions (by name)",
    description="Remove realm role mappings from a group by exact group name. Body: realm_roles (list of role names).",
    responses={
        200: {"description": "Group permissions after remove"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_group_permissions_by_name(
    group_name: str,
    body: PermissionUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupPermissionResponse:
    """Remove permissions (realm roles) from a group by group name."""
    return await groups_service.remove_group_permission_by_name(group_name, body)


@router.get(
    "/groups/{group_id}/members",
    response_model=GroupMembersListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group members by ID",
    description="Get members of a group by Keycloak group ID (paginated).",
    responses={
        200: {"description": "Paginated list of group members"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_group_members_by_id(
    group_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupMembersListResponse:
    """Get group members by group ID (paginated).

    Args:
        group_id: Keycloak group ID.
        page: Page number (1-based).
        page_size: Items per page (max 100).
        current_user: Authenticated user (injected).

    Returns:
        Paginated response (items + meta) with group members.
    """
    return await groups_service.get_group_members_by_id(
        group_id=group_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/groups/{group_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add member to group (by ID)",
    description="Add a user to a group by Keycloak group ID. Body: user_id.",
    responses={
        204: {"description": "Member added"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_group_member_by_id(
    group_id: str,
    body: GroupMemberUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Add a user to a group by group ID.

    Args:
        group_id: Keycloak group ID.
        body: User ID to add.
        current_user: Authenticated user (injected).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or user not found.
    """
    await groups_service.add_group_member_by_id(group_id, body.user_id)


@router.delete(
    "/groups/{group_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from group (by ID)",
    description="Remove a user from a group by Keycloak group ID. Body: user_id.",
    responses={
        204: {"description": "Member removed"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_group_member_by_id(
    group_id: str,
    body: GroupMemberUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Remove a user from a group by group ID.

    Args:
        group_id: Keycloak group ID.
        body: User ID to remove.
        current_user: Authenticated user (injected).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or user not found.
    """
    await groups_service.remove_group_member_by_id(group_id, body.user_id)


@router.get(
    "/groups/by-name/{group_name}/members",
    response_model=GroupMembersListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group members by name",
    description="Get members of a group by exact group name (paginated).",
    responses={
        200: {"description": "Paginated list of group members"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def get_group_members_by_name(
    group_name: str,
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> GroupMembersListResponse:
    """Get group members by group name (paginated).

    Args:
        group_name: Group name (exact match).
        page: Page number (1-based).
        page_size: Items per page (max 100).
        current_user: Authenticated user (injected).

    Returns:
        Paginated response (items + meta) with group members.
    """
    return await groups_service.get_group_members_by_name(
        group_name=group_name,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/groups/by-name/{group_name}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add member to group (by name)",
    description="Add a user to a group by exact group name. Body: user_id.",
    responses={
        204: {"description": "Member added"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def add_group_member_by_name(
    group_name: str,
    body: GroupMemberUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Add a user to a group by group name.

    Args:
        group_name: Group name (exact match).
        body: User ID to add.
        current_user: Authenticated user (injected).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or user not found.
    """
    await groups_service.add_group_member_by_name(group_name, body.user_id)


@router.delete(
    "/groups/by-name/{group_name}/members",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from group (by name)",
    description="Remove a user from a group by exact group name. Body: user_id.",
    responses={
        204: {"description": "Member removed"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def remove_group_member_by_name(
    group_name: str,
    body: GroupMemberUpdateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Remove a user from a group by group name.

    Args:
        group_name: Group name (exact match).
        body: User ID to remove.
        current_user: Authenticated user (injected).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        NotFoundError: If group or user not found.
    """
    await groups_service.remove_group_member_by_name(group_name, body.user_id)
