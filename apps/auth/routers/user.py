"""User routes for local authentication."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth import schemas
from apps.auth.dependencies.auth import get_current_user
from apps.auth.dependencies.rbac import require_roles
from apps.auth.helpers.exceptions import UserNotFoundError
from apps.auth.repository.bll import create_user
from apps.auth.repository.dal import get_user_by_id, list_users
from apps.core.db import get_db
from apps.core.utils import PaginatedResponse, PaginationParams

router = APIRouter()

ADMIN_ROLE = "admin"


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description=(
        "Create a local user and default profile. " "Time: O(1) - Space: O(1)"
    ),
    responses={
        409: {"description": "Email or username already exists"},
        422: {"description": "Validation error"},
    },
)
async def register_user(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.UserResponse:
    """Register a local user.

    Args:
        user_data: User creation data.
        db: Database session.

    Returns:
        Created user response.
    """
    user = await create_user(db, user_data)
    return schemas.UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=schemas.UserInfo,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description=(
        "Return the authenticated local user from the bearer token. "
        "Time: O(1) - Space: O(1)"
    ),
    responses={
        401: {"description": "Authentication required or invalid"},
    },
)
async def get_me(
    current_user: schemas.CurrentUser = Depends(get_current_user),
) -> schemas.UserInfo:
    """Return current authenticated user.

    Args:
        current_user: Authenticated user dependency.

    Returns:
        Current user information.
    """
    return current_user


@router.get(
    "/users",
    response_model=PaginatedResponse[schemas.UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description=(
        "Return a paginated list of local users. "
        "Time: O(page_size) - Space: O(page_size)"
    ),
    responses={
        401: {"description": "Authentication required or invalid"},
        403: {"description": "Admin role required"},
    },
)
async def get_users(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_roles(ADMIN_ROLE)),
) -> PaginatedResponse[schemas.UserResponse]:
    """List users for admin callers.

    Args:
        pagination: Pagination parameters.
        db: Database session.
        _: Admin role dependency.

    Returns:
        Paginated user response.
    """
    users, total_items = await list_users(db, pagination)
    items = [schemas.UserResponse.model_validate(user) for user in users]
    return PaginatedResponse.create(
        items=items,
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
    )


@router.get(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description=(
        "Return a local user by ID with related auth data. " "Time: O(1) - Space: O(1)"
    ),
    responses={
        401: {"description": "Authentication required or invalid"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_roles(ADMIN_ROLE)),
) -> schemas.UserResponse:
    """Get user detail for admin callers.

    Args:
        user_id: User identifier.
        db: Database session.
        _: Admin role dependency.

    Returns:
        User response.

    Raises:
        UserNotFoundError: If user does not exist.
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError(user_id=user_id)
    return schemas.UserResponse.model_validate(user)


__all__ = ["router"]
