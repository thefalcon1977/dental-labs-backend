"""Group schemas for the auth app."""

from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

StringList: TypeAlias = list[str]


class GroupBase(BaseModel):
    """Base group schema shared by group requests and responses."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class GroupCreate(GroupBase):
    """Schema for creating a group."""

    role_ids: StringList = Field(default_factory=list)


class GroupUpdate(BaseModel):
    """Schema for updating a group."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    role_ids: StringList | None = None


class GroupResponse(GroupBase):
    """Public group response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime | None = None


class GroupInfo(BaseModel):
    """Compact group information for auth dependencies."""

    name: str
    roles: StringList = Field(default_factory=list)


__all__ = [
    "GroupBase",
    "GroupCreate",
    "GroupInfo",
    "GroupResponse",
    "GroupUpdate",
]
