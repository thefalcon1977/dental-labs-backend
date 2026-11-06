"""Schemas for Keycloak users list endpoint.

Maps Keycloak Admin API UserRepresentation to Pydantic models for GET /auth/users.
Keycloak 'attributes' is exposed as 'profile'.
"""

from pydantic import BaseModel, ConfigDict, Field

from apps.core.utils.pagination import PaginatedResponse

from ..types import ClientRolesDict, ProfileDict
from .groups import GroupBrief


class UserDetail(BaseModel):
    """Keycloak user representation for list endpoint.

    Exposes id, username, name, email, enabled, profile (from Keycloak attributes),
    requiredActions, realmRoles, clientRoles, createdTimestamp.
    Optional groups (included when include_groups=true).
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str = Field(description="Keycloak user ID")
    username: str | None = Field(default=None, description="Login username")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    email: str | None = Field(default=None)
    email_verified: bool | None = Field(default=None, alias="emailVerified")
    enabled: bool | None = Field(default=None)
    created_timestamp: int | None = Field(default=None, alias="createdTimestamp")
    profile: ProfileDict | None = Field(
        default=None,
        description="User profile data (Keycloak attributes).",
    )
    required_actions: list[str] | None = Field(default=None, alias="requiredActions")
    realm_roles: list[str] | None = Field(default=None, alias="realmRoles")
    client_roles: ClientRolesDict | None = Field(default=None, alias="clientRoles")
    groups: list[GroupBrief] | None = Field(
        default=None,
        description="Groups the user belongs to (included when include_groups=true).",
    )


class UserListParams(BaseModel):
    """Query parameters for listing users with search and pagination."""

    search: str | None = Field(
        default=None,
        max_length=256,
        description="Search for username, first name, last name, or email.",
    )
    username: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by username (exact).",
    )
    first_name: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by first name.",
    )
    last_name: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by last name.",
    )
    email: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by email.",
    )
    phone_number: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by phoneNumber (Keycloak custom attribute).",
    )
    main_group: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by mainGroup (Keycloak custom attribute).",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    )
    enabled: bool | None = Field(
        default=None,
        description="Filter by enabled status.",
    )
    group_id: str | None = Field(
        default=None,
        description="Filter users by Keycloak group ID (returns only members of this group).",
    )
    include_groups: bool = Field(
        default=True,
        description="Include each user's groups in the response (groups field). Set false to omit.",
    )


class UserListResponse(PaginatedResponse[UserDetail]):
    """Paginated response of user details (items + meta)."""


class UserProfileResponse(BaseModel):
    """User profile (Keycloak attributes) for GET /users/{user_id}/profile (nested)."""

    profile: ProfileDict | None = Field(
        default=None,
        description="User profile data (Keycloak attributes).",
    )


class UserProfileFlat(BaseModel):
    """Flat user profile: attributes as top-level keys plus Keycloak enabled flag.

    GET /users/{user_id}/profile returns this (attributes + enabled).
    """

    model_config = ConfigDict(extra="allow")

    enabled: bool | None = Field(
        default=None,
        description="Keycloak user enabled flag (account can log in when true).",
    )


class UserProfileUpdate(BaseModel):
    """Request body for PUT /users/{user_id}/profile (legacy)."""

    profile: ProfileDict | None = Field(
        default=None,
        description="User profile data (Keycloak attributes).",
    )


class UserProfileMainGroupUpdate(BaseModel):
    """Request body for PATCH /users/{user_id}/profile (mainGroup and/or enabled)."""

    model_config = ConfigDict(populate_by_name=True)

    main_group: str | None = Field(
        default=None,
        max_length=256,
        description="Set mainGroup attribute. Use null to clear.",
        alias="mainGroup",
    )
    enabled: bool | None = Field(
        default=None,
        description="Set Keycloak user enabled flag (account can log in when true). Omit to leave unchanged.",
    )


class UserGroupUpdateRequest(BaseModel):
    """Request body to add or remove a group from a user."""

    group_id: str = Field(
        ...,
        min_length=1,
        description="Keycloak group ID to add or remove.",
    )
