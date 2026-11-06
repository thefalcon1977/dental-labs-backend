"""Schemas for managing groups, roles, and permissions (JWT mode)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..types import NameList

PERMISSION_CODE_PATTERN = r"^[a-z0-9][a-z0-9_.:-]{0,149}$"
ROLE_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$"
GROUP_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,149}$"


# Permissions


class PermissionCreate(BaseModel):
    """Create a permission."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {"code": "orders:read", "description": "Read orders"}
        },
    )

    code: str = Field(
        ...,
        pattern=PERMISSION_CODE_PATTERN,
        description="Lowercase code, e.g. `orders:read`",
    )
    description: str | None = Field(None, max_length=255)


class PermissionUpdate(BaseModel):
    """Update a permission's description (the code is immutable)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = Field(None, max_length=255)


class PermissionResponse(BaseModel):
    """A permission."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    description: str | None = None
    created_at: datetime


# Roles


class RoleCreate(BaseModel):
    """Create a role."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {"name": "order-manager", "description": "Manage orders"}
        },
    )

    name: str = Field(..., pattern=ROLE_NAME_PATTERN)
    description: str | None = Field(None, max_length=255)


class RoleUpdate(BaseModel):
    """Partially update a role."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, pattern=ROLE_NAME_PATTERN)
    description: str | None = Field(None, max_length=255)


class RoleResponse(BaseModel):
    """A role (without its permissions)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    created_at: datetime


class RoleDetailResponse(RoleResponse):
    """A role with its permissions."""

    permissions: list[PermissionResponse] = []


# Groups


class GroupCreate(BaseModel):
    """Create a group."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {"name": "Support Team", "description": "Tier-1 support"}
        },
    )

    name: str = Field(..., pattern=GROUP_NAME_PATTERN)
    description: str | None = Field(None, max_length=255)


class GroupUpdate(BaseModel):
    """Partially update a group."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, pattern=GROUP_NAME_PATTERN)
    description: str | None = Field(None, max_length=255)


class GroupResponse(BaseModel):
    """A group (without its roles)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    created_at: datetime


class GroupDetailResponse(GroupResponse):
    """A group with the roles granted to it."""

    roles: list[RoleResponse] = []


# Users


class UserSummaryResponse(BaseModel):
    """A local user as seen by administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    created_at: datetime


class UserAccessResponse(BaseModel):
    """A user's direct grants and resulting effective access."""

    user_id: str
    direct_roles: NameList = Field(description="Roles granted to the user directly")
    groups: NameList = Field(description="Groups the user belongs to")
    effective_roles: NameList = Field(description="Direct roles plus group roles")
    permissions: NameList = Field(description="Permissions from effective roles")
