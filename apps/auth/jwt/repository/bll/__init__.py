"""Business Logic Layer for local users, profiles, and RBAC (writes)."""

from .profile import update_profile
from .rbac import (
    add_permission_to_role,
    add_role_to_group,
    add_role_to_user,
    add_user_to_group,
    create_group,
    create_permission,
    create_role,
    delete_group,
    delete_permission,
    delete_role,
    ensure_admin_role,
    remove_permission_from_role,
    remove_role_from_group,
    remove_role_from_user,
    remove_user_from_group,
    update_group,
    update_permission,
    update_role,
)
from .user import create_user, record_login

__all__ = [
    "add_permission_to_role",
    "add_role_to_group",
    "add_role_to_user",
    "add_user_to_group",
    "create_group",
    "create_permission",
    "create_role",
    "create_user",
    "delete_group",
    "delete_permission",
    "delete_role",
    "ensure_admin_role",
    "record_login",
    "remove_permission_from_role",
    "remove_role_from_group",
    "remove_role_from_user",
    "remove_user_from_group",
    "update_group",
    "update_permission",
    "update_profile",
    "update_role",
]
