"""Admin endpoints for groups, their roles, and members (JWT mode)."""

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
from ..services.rbac_service import GroupPage, UserPage

router = APIRouter(prefix="/groups", dependencies=[Depends(require_admin)])

AUTH_ERRORS = {401: RESP_401, 403: RESP_403, 500: RESP_500}


@router.get(
    "",
    response_model=GroupPage,
    status_code=status.HTTP_200_OK,
    summary="List groups",
    description=(
        "Paginated groups ordered by name. Requires the admin permission. "
        "Time: O(log n + page_size), n = groups · Space: O(page_size)"
    ),
    responses={200: {"description": "Groups"}, 422: RESP_422, **AUTH_ERRORS},
)
async def list_groups(
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, max_length=150, description="Name prefix"),
    db: AsyncSession = Depends(get_db),
) -> GroupPage:
    """List groups.

    Args:
        pagination: Page parameters.
        search: Optional name prefix.
        db: Database session (injected).

    Returns:
        A page of groups.
    """
    return await rbac_service.list_groups(db, pagination, search)


@router.post(
    "",
    response_model=schemas.GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create group",
    description=(
        "Create a group. Requires the admin permission. "
        "Time: O(log n) unique check · Space: O(1)"
    ),
    responses={
        201: {"description": "Group created"},
        409: RESP_409,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def create_group(
    data: schemas.GroupCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.GroupResponse:
    """Create a group.

    Args:
        data: Group data.
        db: Database session (injected).

    Returns:
        The created group.

    Raises:
        ResourceAlreadyExistsError: If the name is taken (409).
    """
    return await rbac_service.create_group(db, data)


@router.get(
    "/{group_id}",
    response_model=schemas.GroupDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group",
    description=(
        "Get a group and the roles granted to it. Requires the admin "
        "permission. Time: O(r), r = roles on the group · Space: O(r)"
    ),
    responses={200: {"description": "Group"}, 404: RESP_404, **AUTH_ERRORS},
)
async def get_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.GroupDetailResponse:
    """Get a group.

    Args:
        group_id: Group identifier.
        db: Database session (injected).

    Returns:
        The group and its roles.

    Raises:
        NotFoundError: If it does not exist (404).
    """
    return await rbac_service.get_group(db, group_id)


@router.patch(
    "/{group_id}",
    response_model=schemas.GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Update group",
    description=(
        "Rename or re-describe a group. Requires the admin permission. "
        "Time: O(log n) unique check · Space: O(1)"
    ),
    responses={
        200: {"description": "Group updated"},
        404: RESP_404,
        409: RESP_409,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def update_group(
    group_id: str,
    data: schemas.GroupUpdate,
    db: AsyncSession = Depends(get_db),
) -> schemas.GroupResponse:
    """Update a group.

    Args:
        group_id: Group identifier.
        data: Fields to change.
        db: Database session (injected).

    Returns:
        The updated group.

    Raises:
        NotFoundError: If it does not exist (404).
        ResourceAlreadyExistsError: If the new name is taken (409).
    """
    return await rbac_service.update_group(db, group_id, data)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete group",
    description=(
        "Delete a group; its members lose the group's roles. Requires the "
        "admin permission. Time: O(k), k = members + roles · Space: O(1)"
    ),
    responses={204: {"description": "Group deleted"}, 404: RESP_404, **AUTH_ERRORS},
)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a group.

    Args:
        group_id: Group identifier.
        db: Database session (injected).

    Raises:
        NotFoundError: If it does not exist (404).
    """
    await rbac_service.delete_group(db, group_id)


@router.put(
    "/{group_id}/roles/{role_id}",
    response_model=schemas.GroupDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Grant role to group",
    description=(
        "Grant a role to a group; all members inherit it. Idempotent. "
        "Requires the admin permission. "
        "Time: O(r), r = roles on the group (response) · Space: O(r)"
    ),
    responses={200: {"description": "Group with roles"}, 404: RESP_404, **AUTH_ERRORS},
)
async def add_role_to_group(
    group_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.GroupDetailResponse:
    """Grant a role to a group.

    Args:
        group_id: Group identifier.
        role_id: Role identifier.
        db: Database session (injected).

    Returns:
        The group with its roles.

    Raises:
        NotFoundError: If the group or role does not exist (404).
    """
    return await rbac_service.add_role_to_group(db, group_id, role_id)


@router.delete(
    "/{group_id}/roles/{role_id}",
    response_model=schemas.GroupDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke role from group",
    description=(
        "Revoke a role from a group. Idempotent. Requires the admin "
        "permission. Time: O(r), r = roles on the group (response) · Space: O(r)"
    ),
    responses={200: {"description": "Group with roles"}, 404: RESP_404, **AUTH_ERRORS},
)
async def remove_role_from_group(
    group_id: str,
    role_id: str,
    db: AsyncSession = Depends(get_db),
) -> schemas.GroupDetailResponse:
    """Revoke a role from a group.

    Args:
        group_id: Group identifier.
        role_id: Role identifier.
        db: Database session (injected).

    Returns:
        The group with its roles.

    Raises:
        NotFoundError: If the group or role does not exist (404).
    """
    return await rbac_service.remove_role_from_group(db, group_id, role_id)


@router.get(
    "/{group_id}/members",
    response_model=UserPage,
    status_code=status.HTTP_200_OK,
    summary="List group members",
    description=(
        "Paginated members of a group ordered by username. Requires the admin "
        "permission. Time: O(log n + page_size) · Space: O(page_size)"
    ),
    responses={
        200: {"description": "Members"},
        404: RESP_404,
        422: RESP_422,
        **AUTH_ERRORS,
    },
)
async def list_group_members(
    group_id: str,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> UserPage:
    """List a group's members.

    Args:
        group_id: Group identifier.
        pagination: Page parameters.
        db: Database session (injected).

    Returns:
        A page of members.

    Raises:
        NotFoundError: If the group does not exist (404).
    """
    return await rbac_service.list_group_members(db, group_id, pagination)


@router.put(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Add user to group",
    description=(
        "Add a user to a group. Idempotent. Requires the admin permission. "
        "Time: O(1) · Space: O(1)"
    ),
    responses={204: {"description": "User added"}, 404: RESP_404, **AUTH_ERRORS},
)
async def add_user_to_group(
    group_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Add a user to a group.

    Args:
        group_id: Group identifier.
        user_id: User identifier.
        db: Database session (injected).

    Raises:
        NotFoundError: If the group or user does not exist (404).
    """
    await rbac_service.add_user_to_group(db, group_id, user_id)


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from group",
    description=(
        "Remove a user from a group. Idempotent. Requires the admin "
        "permission. Time: O(1) · Space: O(1)"
    ),
    responses={204: {"description": "User removed"}, 404: RESP_404, **AUTH_ERRORS},
)
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a user from a group.

    Args:
        group_id: Group identifier.
        user_id: User identifier.
        db: Database session (injected).

    Raises:
        NotFoundError: If the group or user does not exist (404).
    """
    await rbac_service.remove_user_from_group(db, group_id, user_id)
