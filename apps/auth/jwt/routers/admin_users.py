"""Admin endpoints for users' roles and effective access (JWT mode)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_404,
    RESP_422,
    RESP_500,
)
from apps.core.db import get_db
from apps.core.utils import PaginationParams

from .. import schemas
from ..dependencies.admin import require_admin
from ..services import rbac_service
from ..services.rbac_service import UserPage

router = APIRouter(prefix="/users", dependencies=[Depends(require_admin)])

AUTH_ERRORS = {401: RESP_401, 403: RESP_403, 500: RESP_500}


@router.get(
    "",
    response_model=UserPage,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description=(
        "Paginated local users ordered by username, optionally filtered by "
        "username/email prefix. Requires the admin permission. "
        "Time: O(log n + page_size), n = users · Space: O(page_size)"
    ),
    responses={200: {"description": "Users"}, 422: RESP_422, **AUTH_ERRORS},
)
async def list_users(
    pagination: PaginationParams = Depends(),
    search: str | None = Query(
        None, max_length=255, description="Username or email prefix"
    ),
    db: AsyncSession = Depends(get_db),
) -> UserPage:
    """List local users.

    Args:
        pagination: Page parameters.
        search: Optional username/email prefix.
        db: Database session (injected).

    Returns:
        A page of users.
    """
    return await rbac_service.list_users(db, pagination, search)


@router.get(
    "/{user_id}/access",
    response_model=schemas.UserAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user access",
    description=(
        "A user's direct roles, groups, effective roles (direct + group), and "
        "permissions. Requires the admin permission. "
        "Time: O(g + r + p) for the user's groups, roles, permissions · "
        "Space: O(g + r + p)"
    ),
    responses={200: {"description": "User access"}, 404: RESP_404, **AUTH_ERRORS},
)
async def get_user_access(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.UserAccessResponse:
    """Get a user's access.

    Args:
        user_id: User identifier.
        db: Database session (injected).

    Returns:
        Direct and effective access.

    Raises:
        NotFoundError: If the user does not exist (404).
    """
    return await rbac_service.get_user_access(db, user_id)


@router.put(
    "/{user_id}/roles/{role_id}",
    response_model=schemas.UserAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Grant role to user",
    description=(
        "Grant a role to a user directly. Idempotent. Takes effect from the "
        "user's next token (login or refresh). Requires the admin permission. "
        "Time: O(g + r + p) (response) · Space: O(g + r + p)"
    ),
    responses={200: {"description": "User access"}, 404: RESP_404, **AUTH_ERRORS},
)
async def add_role_to_user(
    user_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.UserAccessResponse:
    """Grant a role to a user.

    Args:
        user_id: User identifier.
        role_id: Role identifier.
        db: Database session (injected).

    Returns:
        The user's updated access.

    Raises:
        NotFoundError: If the user or role does not exist (404).
    """
    return await rbac_service.add_role_to_user(db, user_id, role_id)


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=schemas.UserAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke role from user",
    description=(
        "Revoke a directly granted role. Roles inherited from groups are not "
        "affected. Idempotent. Requires the admin permission. "
        "Time: O(g + r + p) (response) · Space: O(g + r + p)"
    ),
    responses={200: {"description": "User access"}, 404: RESP_404, **AUTH_ERRORS},
)
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.UserAccessResponse:
    """Revoke a role from a user.

    Args:
        user_id: User identifier.
        role_id: Role identifier.
        db: Database session (injected).

    Returns:
        The user's updated access.

    Raises:
        NotFoundError: If the user or role does not exist (404).
    """
    return await rbac_service.remove_role_from_user(db, user_id, role_id)
