"""Role schemas for the auth app."""

from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

StringList: TypeAlias = list[str]


class RoleBase(BaseModel):
    """Base role schema shared by role requests and responses."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class RoleCreate(RoleBase):
    """Schema for creating a role."""


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class RoleResponse(RoleBase):
    """Public role response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime | None = None


class RoleInfo(BaseModel):
    """Compact role information for auth dependencies."""

    name: str
    permissions: StringList = Field(default_factory=list)


__all__ = [
    "RoleBase",
    "RoleCreate",
    "RoleInfo",
    "RoleResponse",
    "RoleUpdate",
]
