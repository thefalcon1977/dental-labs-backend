"""Permissions (realm roles) list and create/delete endpoint.

Renamed from /roles to /permissions. Use GET /auth/users/{user_id}/permissions
with user_id 'me' or a specific ID for get/add/remove permissions for a user or self.
"""

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
from ..schemas.roles import PermissionCreateRequest, RealmRolesListResponse, RoleItem
from ..schemas.user import UserInfo
from ..services import roles_service

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


@router.get(
    "/permissions",
    response_model=RealmRolesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List permissions (realm roles)",
    description=(
        "Return a paginated list of available realm roles (permissions) from Keycloak. "
        "To get, add, or remove permissions for a user (or self), use "
        "GET/POST/DELETE /auth/users/{user_id}/permissions with user_id 'me' for current user."
    ),
    responses={
        200: {"description": "Paginated list of realm roles"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def list_permissions(
    search: str | None = Query(
        None,
        max_length=256,
        description="Filter by role name.",
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    ),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> RealmRolesListResponse:
    """List available permissions (realm roles) paginated.

    Returns a paginated list of realm roles from Keycloak.

    Args:
        search: Optional filter by role name.
        page: Page number (1-based).
        page_size: Items per page (max 100).
        current_user: Authenticated user (injected).

    Returns:
        Paginated response (items + meta) with realm roles.

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        UnauthorizedError: If token is missing or invalid.
    """
    return await roles_service.list_realm_roles(
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/permissions",
    response_model=RoleItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create permission (realm role)",
    description="Create a new realm role (permission) in Keycloak. Name must be unique.",
    responses={
        201: {"description": "Permission created"},
        401: RESP_401,
        403: RESP_403,
        409: RESP_409,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def create_permission(
    body: PermissionCreateRequest,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> RoleItem:
    """Create a new realm role (permission).

    Args:
        body: Name and optional description.
        current_user: Authenticated user (injected).

    Returns:
        Created role (RoleItem).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
        ConflictError: If a role with the same name already exists.
    """
    return await roles_service.create_realm_role(body)


@router.delete(
    "/permissions/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete permission (realm role)",
    description="Delete a realm role (permission) by name from Keycloak.",
    responses={
        204: {"description": "Permission deleted"},
        401: RESP_401,
        403: RESP_403,
        404: RESP_404,
        500: RESP_500,
        503: RESP_503,
    },
)
async def delete_permission(
    role_name: str,
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> None:
    """Delete a realm role (permission) by name.

    Args:
        role_name: Realm role name (path; URL-encoded if needed).
        current_user: Authenticated user (injected).

    Raises:
        KeycloakConnectionError: If Keycloak is disabled or Admin API fails.
    """
    await roles_service.delete_realm_role(role_name)
