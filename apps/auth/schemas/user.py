"""User schemas for local authentication."""

from datetime import datetime
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator

StringList: TypeAlias = list[str]


class UserBaseSchema(BaseModel):
    """Base user schema shared by user requests and responses."""

    email: str = Field(..., min_length=3, max_length=255)
    username: str = Field(..., min_length=1, max_length=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email values before schema usage.

        Args:
            value: Email value provided by the client or database.

        Returns:
            Lowercase, stripped email value.
        """
        return value.strip().lower()


class UserCreate(UserBaseSchema):
    """Schema for creating a local user."""

    password: str = Field(..., min_length=8, max_length=128)
    group_ids: StringList = Field(default_factory=list)
    role_ids: StringList = Field(default_factory=list)


class UserUpdate(BaseModel):
    """Schema for updating a local user."""

    email: str | None = Field(default=None, min_length=3, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None
    is_verified: bool | None = None
    is_superuser: bool | None = None
    group_ids: StringList | None = None
    role_ids: StringList | None = None

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, value: str | None) -> str | None:
        """Normalize optional email values before schema usage.

        Args:
            value: Optional email value provided by the client.

        Returns:
            Lowercase, stripped email value, or None.
        """
        if value is None:
            return None
        return value.strip().lower()


class PasswordChangeRequest(BaseModel):
    """Schema for changing an authenticated user's password."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBaseSchema):
    """Public user response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime | None = None


class UserInfo(UserResponse):
    """Authenticated user information used by auth dependencies."""

    roles: StringList = Field(default_factory=list)
    groups: StringList = Field(default_factory=list)
    profile: StringList = Field(default_factory=list)


CurrentUser: TypeAlias = UserInfo

__all__ = [
    "CurrentUser",
    "PasswordChangeRequest",
    "UserBaseSchema",
    "UserCreate",
    "UserInfo",
    "UserResponse",
    "UserUpdate",
]
