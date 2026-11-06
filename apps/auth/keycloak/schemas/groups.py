"""Schemas for Keycloak groups list endpoint.

Maps Keycloak Admin API GroupRepresentation to Pydantic models for GET /auth/groups.
"""

from pydantic import BaseModel, ConfigDict, Field

from apps.core.utils.pagination import PaginatedResponse

from ..types import ClientRolesDict


class GroupDetail(BaseModel):
    """Keycloak group representation for list endpoint.

    Exposes id, name, path, description, parentId, subGroups, subGroupCount,
    realmRoles, clientRoles. Does not include attributes or access.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str = Field(description="Keycloak group ID")
    name: str = Field(description="Group name")
    path: str | None = Field(default=None)
    description: str | None = Field(default=None)
    parent_id: str | None = Field(default=None, alias="parentId")
    sub_groups: list["GroupDetail"] | None = Field(default=None, alias="subGroups")
    sub_group_count: int | None = Field(default=None, alias="subGroupCount")
    realm_roles: list[str] | None = Field(default=None, alias="realmRoles")
    client_roles: ClientRolesDict | None = Field(default=None, alias="clientRoles")


GroupDetail.model_rebuild()


class GroupCreate(BaseModel):
    """Request body for creating a Keycloak group (top-level)."""

    name: str = Field(..., min_length=1, max_length=256, description="Group name.")


class GroupUpdate(BaseModel):
    """Request body for updating a Keycloak group.

    This is used by PATCH /auth/groups/{group_id}. Only provided fields are updated.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="New group name. Omit to leave unchanged.",
    )
    description: str | None = Field(
        default=None,
        max_length=1024,
        description="New group description. Use null to clear; omit to leave unchanged.",
    )


class GroupListParams(BaseModel):
    """Query parameters for listing groups with search and pagination."""

    search: str | None = Field(
        default=None,
        max_length=256,
        description="Filter by group name.",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100).",
    )


class GroupListResponse(PaginatedResponse[GroupDetail]):
    """Paginated response of group details (items + meta)."""


class GroupBrief(BaseModel):
    """Brief group representation (id, name, path)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str = Field(description="Keycloak group ID")
    name: str = Field(description="Group name")
    path: str | None = Field(default=None)


class UserBrief(BaseModel):
    """Brief user representation for group members list."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: str = Field(description="Keycloak user ID")
    username: str | None = Field(default=None)
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    email: str | None = Field(default=None)
    enabled: bool | None = Field(default=None)


class UserGroupsListResponse(PaginatedResponse[GroupBrief]):
    """Paginated response of groups the user belongs to."""


class GroupMembersListResponse(PaginatedResponse[UserBrief]):
    """Paginated response of group members (users)."""


class GroupMemberUpdateRequest(BaseModel):
    """Request body to add or remove a user (member) from a group."""

    user_id: str = Field(
        ..., min_length=1, description="Keycloak user ID to add or remove."
    )
