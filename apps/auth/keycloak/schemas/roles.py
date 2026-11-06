"""Schemas for Keycloak roles and role mappings."""

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from apps.core.utils.pagination import PaginatedResponse

from ..types import RawKeycloakDict

RoleItemList: TypeAlias = list["RoleItem"]


class RoleItem(BaseModel):
    """Keycloak role representation (id, name, description)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str | None = Field(default=None)
    name: str = Field(description="Role name")
    description: str | None = Field(default=None)
    composite: bool | None = Field(default=None)
    client_role: bool | None = Field(default=None, alias="clientRole")
    container_id: str | None = Field(default=None, alias="containerId")


class UserPermissionResponse(BaseModel):
    """User permission: effective realm roles only."""

    realm_roles: RoleItemList = Field(
        default_factory=list,
        description="Effective realm roles for the user.",
    )


class GroupPermissionResponse(BaseModel):
    """Group permission: effective realm roles only."""

    realm_roles: RoleItemList = Field(
        default_factory=list,
        description="Effective realm roles for the group.",
    )


class RealmRolesListResponse(PaginatedResponse[RoleItem]):
    """Paginated response of realm roles."""


class PermissionUpdateRequest(BaseModel):
    """Request body to add or remove permissions (realm roles only) for a user or group."""

    realm_roles: list[str] = Field(
        default_factory=list,
        description="Realm role names to add or remove.",
    )


class PermissionCreateRequest(BaseModel):
    """Request body to create a new realm role (permission)."""

    name: str = Field(..., min_length=1, max_length=255, description="Role name.")
    description: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional role description.",
    )


def role_raw_to_item(raw: RawKeycloakDict) -> RoleItem:
    """Map Keycloak role dict to RoleItem.

    Args:
        raw: Raw role dict from Keycloak API.

    Returns:
        RoleItem instance (id, name, description).
    """
    return RoleItem.model_validate(raw)
