"""Flat users-and-groups (identities) list endpoint."""

from fastapi import APIRouter, Depends, Query, status

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_422,
    RESP_500,
    RESP_503,
)
from config.logging import get_logger

from ..dependencies.auth import get_current_user_or_system
from ..schemas.identities import IdentityListParams, IdentityListResponse
from ..schemas.user import UserInfo
from ..services import identities_service

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


def get_identity_list_params(
    type_filter: str = Query(
        "all",
        alias="type",
        description="Filter by type: user, group, or all (both).",
    ),
    search: str | None = Query(
        None,
        max_length=256,
        description="Search term for name/username/email.",
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
        description="Filter users by enabled status (ignored for groups).",
    ),
) -> IdentityListParams:
    """Build IdentityListParams from query parameters.

    Args:
        type_filter: Filter by type (user, group, or all).
        search: Search term for name/username/email.
        page: Page number (1-based).
        page_size: Items per page (max 100).
        enabled: Filter users by enabled status (ignored for groups).

    Returns:
        IdentityListParams instance for list_identities.
    """
    type_val: str = "all"
    if type_filter in ("user", "group", "all"):
        type_val = type_filter
    return IdentityListParams(
        type_filter=type_val,
        search=search,
        page=page,
        page_size=page_size,
        enabled=enabled,
    )


@router.get(
    "/identities",
    response_model=IdentityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users and groups (flat)",
    description=(
        "Return a flat, paginated list of Keycloak users and/or groups (identities) "
        "in a single structure. Uses Keycloak Admin API (client credentials). "
        "Response shape matches standard list endpoints (items + meta). "
        "Time: O(page_size) · Space: O(page_size)"
    ),
    responses={
        200: {"description": "Paginated list of identities (users and/or groups)"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def list_identities(
    params: IdentityListParams = Depends(get_identity_list_params),
    current_user: UserInfo = Depends(get_current_user_or_system),
) -> IdentityListResponse:
    """List users and groups (identities) in a flat structure with search and pagination.

    Same response shape for users and groups; each item has type 'user' or
    'group'. Efficient: parallel Keycloak requests when type=all.

    Args:
        params: Query params (type, search, page, page_size)
        current_user: Authenticated user (injected)

    Returns:
        Paginated response with items and meta.
    """
    logger.debug(
        "Listing identities",
        type_filter=params.type_filter,
        page=params.page,
        page_size=params.page_size,
    )
    return await identities_service.get_identities_flat(params)
