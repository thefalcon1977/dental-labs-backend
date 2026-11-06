"""Admin endpoints for permissions (JWT mode)."""

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
from ..services.rbac_service import PermissionPage

router = APIRouter(prefix="/permissions", dependencies=[Depends(require_admin)])

AUTH_ERRORS = {401: RESP_401, 403: RESP_403, 500: RESP_500}


@router.get(
    "",
    response_model=PermissionPage,
    status_code=status.HTTP_200_OK,
    summary="List permissions",
    description=(
        "Paginated permissions ordered by code. Requires the admin permission. "
        "Time: O(log n + page_size), n = permissions · Space: O(page_size)"
    ),
    responses={200: {"description": "Permissions"}, 422: RESP_422, **AUTH_ERRORS},
)
async def list_permissions(
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, max_length=150, description="Code prefix"),
    db: AsyncSession = Depends(get_db),
) -> PermissionPage:
    """List permissions.

    Args:
        pagination: Page parameters.
        search: Optional code prefix.
        db: Database session (injected).

    Returns:
        A page of permissions.
    """
    return await rbac_service.list_permissions(db, pagination, search)


@router.post(
    "",
    response_model=schemas.PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create permission",
    description=(
        "Create a permission such as `orders:read`. Requires the admin "
        "permission. Time: O(log n) unique check · Space: O(1)"
    ),
    responses={
        201: {"description": "Permission created"},
        409: RESP_409,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def create_permission(
    data: schemas.PermissionCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionResponse:
    """Create a permission.

    Args:
        data: Permission data.
        db: Database session (injected).

    Returns:
        The created permission.

    Raises:
        ResourceAlreadyExistsError: If the code is taken (409).
    """
    return await rbac_service.create_permission(db, data)


@router.patch(
    "/{permission_id}",
    response_model=schemas.PermissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update permission",
    description=(
        "Update a permission's description; the code cannot change. "
        "Requires the admin permission. Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "Permission updated"},
        404: RESP_404,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def update_permission(
    permission_id: str,
    data: schemas.PermissionUpdate,
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionResponse:
    """Update a permission.

    Args:
        permission_id: Permission identifier.
        data: Fields to change.
        db: Database session (injected).

    Returns:
        The updated permission.

    Raises:
        NotFoundError: If it does not exist (404).
    """
    return await rbac_service.update_permission(db, permission_id, data)


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete permission",
    description=(
        "Delete a permission and remove it from every role. The admin "
        "permission cannot be deleted. Requires the admin permission. "
        "Time: O(r), r = roles holding it · Space: O(1)"
    ),
    responses={
        204: {"description": "Permission deleted"},
        404: RESP_404,
        409: RESP_409,
        **AUTH_ERRORS,
    },
)
async def delete_permission(
    permission_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a permission.

    Args:
        permission_id: Permission identifier.
        db: Database session (injected).

    Raises:
        NotFoundError: If it does not exist (404).
        ProtectedResourceError: If it is the admin permission (409).
    """
    await rbac_service.delete_permission(db, permission_id)
