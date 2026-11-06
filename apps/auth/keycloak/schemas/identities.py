"""Schemas for flat users-and-groups (identities) list endpoint."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.core.utils.pagination import PaginatedResponse


class IdentityFlat(BaseModel):
    """Single identity (user or group) in a flat structure.

    Same shape for both users and groups; type and optional fields
    distinguish them.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Keycloak ID (user or group)")
    name: str = Field(
        description="Display name: username for users, group name for groups"
    )
    username: str | None = Field(
        default=None,
        description="Login/account name (users only; null for groups)",
    )
    type: Literal["user", "group"] = Field(description="Identity type")
    email: str | None = Field(
        default=None,
        description="Email (users only; null for groups)",
    )
    path: str | None = Field(
        default=None,
        description="Group path (groups only; null for users)",
    )
    enabled: bool | None = Field(
        default=None,
        description="Enabled flag (users only; null for groups)",
    )


class IdentityListParams(BaseModel):
    """Query parameters for listing identities with search and pagination."""

    type_filter: Literal["user", "group", "all"] = Field(
        default="all",
        alias="type",
        description="Filter by type: user, group, or all (both).",
    )
    search: str | None = Field(
        default=None,
        max_length=256,
        description="Search term for name/username/email.",
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
        description="Filter users by enabled status (ignored for groups).",
    )


class IdentityListResponse(PaginatedResponse[IdentityFlat]):
    """Paginated response of flat identities."""
