"""Token and login schemas for local authentication."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for local username/email and password login."""

    identifier: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Schema returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None


class TokenPayload(BaseModel):
    """Validated token payload used by auth utilities."""

    sub: str
    exp: int | None = None
    iss: str | None = None
    aud: str | None = None


__all__ = [
    "LoginRequest",
    "TokenPayload",
    "TokenResponse",
]
