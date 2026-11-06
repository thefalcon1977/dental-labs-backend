"""Schemas for local JWT authentication."""

from .auth import (
    LocalUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from .profile import ProfileResponse, ProfileUpdate
from .rbac import (
    GroupCreate,
    GroupDetailResponse,
    GroupResponse,
    GroupUpdate,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RoleCreate,
    RoleDetailResponse,
    RoleResponse,
    RoleUpdate,
    UserAccessResponse,
    UserSummaryResponse,
)

__all__ = [
    "GroupCreate",
    "GroupDetailResponse",
    "GroupResponse",
    "GroupUpdate",
    "LocalUserResponse",
    "LoginRequest",
    "PermissionCreate",
    "PermissionResponse",
    "PermissionUpdate",
    "ProfileResponse",
    "ProfileUpdate",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RoleCreate",
    "RoleDetailResponse",
    "RoleResponse",
    "RoleUpdate",
    "TokenResponse",
    "UserAccessResponse",
    "UserSummaryResponse",
]
