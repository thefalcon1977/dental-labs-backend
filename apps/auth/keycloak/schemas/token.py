"""Token validation and refresh schemas."""

from pydantic import BaseModel, ConfigDict

from ..types import AudienceList
from .user import UserInfo


class TokenData(BaseModel):
    """Token payload data."""

    model_config = ConfigDict(from_attributes=True)

    sub: str  # Subject (user ID)
    iss: str  # Issuer
    aud: str | AudienceList  # Audience
    exp: int  # Expiration time
    iat: int  # Issued at
    nbf: int | None = None  # Not before
    jti: str | None = None  # JWT ID
    azp: str | None = None  # Authorized party
    realm_access: dict | None = None  # Realm access (roles)
    resource_access: dict | None = None  # Resource access (client roles)


class TokenValidation(BaseModel):
    """Token validation result."""

    model_config = ConfigDict(from_attributes=True)

    valid: bool
    expired: bool = False
    invalid_reason: str | None = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response schema (tokens and decoded JWT user info)."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    # Decoded JWT user information (id, username, roles, etc.) for client display
    user: UserInfo | None = None


class LoginOtpRequiredResponse(BaseModel):
    """Login response when OTP is required (Step 1). No tokens returned."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    message: str = "OTP sent"
    expires_in: int
    # Only set when OTP_SMS_MOCK_ENABLED=true (mock SMS); never when using real SMS
    dev_otp_code: str | None = None


class VerifyOtpRequest(BaseModel):
    """Verify OTP request (Step 2)."""

    session_id: str
    code: str


class ResendOtpRequest(BaseModel):
    """Resend OTP request (same session from Step 1)."""

    session_id: str


class ResendOtpResponse(BaseModel):
    """Resend OTP response (no tokens)."""

    model_config = ConfigDict(from_attributes=True)

    message: str = "OTP resent"
    expires_in: int
    dev_otp_code: str | None = None
