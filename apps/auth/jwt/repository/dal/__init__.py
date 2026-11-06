"""Data Access Layer for local users, profiles, and RBAC (reads)."""

from .profile import get_profile_by_user_id
from .rbac import (
    get_group,
    get_group_by_name,
    get_permission,
    get_permission_by_code,
    get_role,
    get_role_by_name,
    get_roles_by_names,
    get_user_access,
    get_user_direct_role_names,
    list_group_members,
    list_groups,
    list_permissions,
    list_roles,
)
from .user import (
    get_conflicting_field,
    get_user_by_id,
    get_user_by_login,
    list_users,
    user_exists,
)

__all__ = [
    "get_conflicting_field",
    "get_group",
    "get_group_by_name",
    "get_permission",
    "get_permission_by_code",
    "get_profile_by_user_id",
    "get_role",
    "get_role_by_name",
    "get_roles_by_names",
    "get_user_access",
    "get_user_by_id",
    "get_user_by_login",
    "get_user_direct_role_names",
    "list_group_members",
    "list_groups",
    "list_permissions",
    "list_roles",
    "list_users",
    "user_exists",
]
