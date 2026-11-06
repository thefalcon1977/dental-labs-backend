"""Admin endpoints for roles and their permissions (JWT mode)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_404,
    RESP_409,
    RESP_422,
    RESP_500,
)
from apps.core.db import get_db
from apps.core.utils import PaginationParams

from .. import schemas
from ..dependencies.admin import require_admin
from ..services import rbac_service
from ..services.rbac_service import RolePage

router = APIRouter(prefix="/roles", dependencies=[Depends(require_admin)])

AUTH_ERRORS = {401: RESP_401, 403: RESP_403, 500: RESP_500}


@router.get(
    "",
    response_model=RolePage,
    status_code=status.HTTP_200_OK,
    summary="List roles",
    description=(
        "Paginated roles ordered by name. Requires the admin permission. "
        "Time: O(log n + page_size), n = roles · Space: O(page_size)"
    ),
    responses={200: {"description": "Roles"}, 422: RESP_422, **AUTH_ERRORS},
)
async def list_roles(
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, max_length=100, description="Name prefix"),
    db: AsyncSession = Depends(get_db),
) -> RolePage:
    """List roles.

    Args:
        pagination: Page parameters.
        search: Optional name prefix.
        db: Database session (injected).

    Returns:
        A page of roles.
    """
    return await rbac_service.list_roles(db, pagination, search)


@router.post(
    "",
    response_model=schemas.RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description=(
        "Create a role. Requires the admin permission. "
        "Time: O(log n) unique check · Space: O(1)"
    ),
    responses={
        201: {"description": "Role created"},
        409: RESP_409,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def create_role(
    data: schemas.RoleCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleResponse:
    """Create a role.

    Args:
        data: Role data.
        db: Database session (injected).

    Returns:
        The created role.

    Raises:
        ResourceAlreadyExistsError: If the name is taken (409).
    """
    return await rbac_service.create_role(db, data)


@router.get(
    "/{role_id}",
    response_model=schemas.RoleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get role",
    description=(
        "Get a role and its permissions. Requires the admin permission. "
        "Time: O(p), p = permissions on the role · Space: O(p)"
    ),
    responses={200: {"description": "Role"}, 404: RESP_404, **AUTH_ERRORS},
)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleDetailResponse:
    """Get a role.

    Args:
        role_id: Role identifier.
        db: Database session (injected).

    Returns:
        The role and its permissions.

    Raises:
        NotFoundError: If it does not exist (404).
    """
    return await rbac_service.get_role(db, role_id)


@router.patch(
    "/{role_id}",
    response_model=schemas.RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update role",
    description=(
        "Rename or re-describe a role. The admin role cannot be renamed. "
        "Requires the admin permission. Time: O(log n) unique check · Space: O(1)"
    ),
    responses={
        200: {"description": "Role updated"},
        404: RESP_404,
        409: RESP_409,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def update_role(
    role_id: str,
    data: schemas.RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleResponse:
    """Update a role.

    Args:
        role_id: Role identifier.
        data: Fields to change.
        db: Database session (injected).

    Returns:
        The updated role.

    Raises:
        NotFoundError: If it does not exist (404).
        ResourceAlreadyExistsError: If the new name is taken (409).
        ProtectedResourceError: If renaming the admin role (409).
    """
    return await rbac_service.update_role(db, role_id, data)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    description=(
        "Delete a role and revoke it from all users and groups. The admin "
        "role cannot be deleted. Requires the admin permission. "
        "Time: O(k), k = links to the role · Space: O(1)"
    ),
    responses={
        204: {"description": "Role deleted"},
        404: RESP_404,
        409: RESP_409,
        **AUTH_ERRORS,
    },
)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a role.

    Args:
        role_id: Role identifier.
        db: Database session (injected).

    Raises:
        NotFoundError: If it does not exist (404).
        ProtectedResourceError: If it is the admin role (409).
    """
    await rbac_service.delete_role(db, role_id)


@router.put(
    "/{role_id}/permissions/{permission_id}",
    response_model=schemas.RoleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Grant permission to role",
    description=(
        "Grant a permission to a role. Idempotent: granting twice is a no-op. "
        "Requires the admin permission. "
        "Time: O(p), p = permissions on the role (response) · Space: O(p)"
    ),
    responses={
        200: {"description": "Role with permissions"},
        404: RESP_404,
        **AUTH_ERRORS,
    },
)
async def add_permission_to_role(
    role_id: str,
    permission_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleDetailResponse:
    """Grant a permission to a role.

    Args:
        role_id: Role identifier.
        permission_id: Permission identifier.
        db: Database session (injected).

    Returns:
        The role with its permissions.

    Raises:
        NotFoundError: If the role or permission does not exist (404).
    """
    return await rbac_service.add_permission_to_role(db, role_id, permission_id)


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=schemas.RoleDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke permission from role",
    description=(
        "Revoke a permission from a role. Idempotent. The admin permission "
        "cannot be removed from the admin role. Requires the admin permission. "
        "Time: O(p), p = permissions on the role (response) · Space: O(p)"
    ),
    responses={
        200: {"description": "Role with permissions"},
        404: RESP_404,
        409: RESP_409,
        **AUTH_ERRORS,
    },
)
async def remove_permission_from_role(
    role_id: str,
    permission_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.RoleDetailResponse:
    """Revoke a permission from a role.

    Args:
        role_id: Role identifier.
        permission_id: Permission identifier.
        db: Database session (injected).

    Returns:
        The role with its permissions.

    Raises:
        NotFoundError: If the role or permission does not exist (404).
        ProtectedResourceError: If it would strip admin access (409).
    """
    return await rbac_service.remove_permission_from_role(db, role_id, permission_id)
