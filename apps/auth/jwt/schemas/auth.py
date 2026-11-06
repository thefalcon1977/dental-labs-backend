"""Request and response schemas for local JWT authentication."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.auth.keycloak.schemas.user import UserInfo

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,150}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    """Self-registration payload."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "username": "jane.doe",
                "email": "jane@example.com",
                "password": "a-long-passphrase",
                "first_name": "Jane",
                "last_name": "Doe",
            }
        },
    )

    username: str = Field(..., pattern=USERNAME_PATTERN, description="3-150 chars")
    email: str = Field(..., max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str | None = Field(None, max_length=150)
    last_name: str | None = Field(None, max_length=150)

    @field_validator("username", "email")
    @classmethod
    def lowercase(cls, value: str) -> str:
        """Normalize identifiers so uniqueness is case-insensitive.

        Args:
            value: Raw username or email.

        Returns:
            Lowercased value.
        """
        return value.lower()


class LoginRequest(BaseModel):
    """Login payload; ``username`` accepts either the username or the email."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Issued access/refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    refresh_expires_in: int = Field(
        ..., description="Refresh token lifetime in seconds"
    )
    user: UserInfo


class LocalUserResponse(BaseModel):
    """Public view of a local user account."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    created_at: datetime
