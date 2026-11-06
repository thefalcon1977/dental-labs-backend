"""Authentication schemas."""

from .groups import (
    GroupBrief,
    GroupCreate,
    GroupDetail,
    GroupListParams,
    GroupListResponse,
    GroupMembersListResponse,
    GroupMemberUpdateRequest,
    UserBrief,
    UserGroupsListResponse,
)
from .identities import IdentityFlat, IdentityListParams, IdentityListResponse
from .roles import (
    GroupPermissionResponse,
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RealmRolesListResponse,
    RoleItem,
    UserPermissionResponse,
)
from .users import (
    UserDetail,
    UserGroupUpdateRequest,
    UserListParams,
    UserListResponse,
    UserProfileFlat,
    UserProfileResponse,
    UserProfileUpdate,
)

__all__ = [
    "IdentityFlat",
    "IdentityListParams",
    "IdentityListResponse",
    "GroupCreate",
    "GroupDetail",
    "GroupListParams",
    "GroupListResponse",
    "GroupMemberUpdateRequest",
    "GroupMembersListResponse",
    "GroupBrief",
    "UserBrief",
    "UserGroupsListResponse",
    "GroupPermissionResponse",
    "PermissionCreateRequest",
    "PermissionUpdateRequest",
    "RealmRolesListResponse",
    "RoleItem",
    "UserPermissionResponse",
    "UserDetail",
    "UserGroupUpdateRequest",
    "UserListParams",
    "UserListResponse",
    "UserProfileFlat",
    "UserProfileResponse",
    "UserProfileUpdate",
]
