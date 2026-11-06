"""Test factories for creating test data objects."""

from typing import Any

from apps.auth.keycloak.schemas.user import UserInfo, UserPermissions, UserRoles
from apps.auth.keycloak.types import ClientRolesDict, StringList, TokenPayloadDict


def create_user_roles(
    realm_roles: StringList | None = None,
    client_roles: ClientRolesDict | None = None,
) -> UserRoles:
    """Create a UserRoles instance for testing.

    Args:
        realm_roles: List of realm role names (None defaults to ["user"], empty list stays empty)
        client_roles: Dictionary mapping client IDs to role lists (None defaults to {}, empty dict stays empty)

    Returns:
        UserRoles instance
    """
    if realm_roles is None:
        realm_roles = ["user"]
    if client_roles is None:
        client_roles = {}
    return UserRoles(
        realm_roles=realm_roles,
        client_roles=client_roles,
    )


def create_user_permissions(permissions: StringList | None = None) -> UserPermissions:
    """Create a UserPermissions instance for testing.

    Args:
        permissions: List of permission names (None defaults to ["read"], empty list stays empty)

    Returns:
        UserPermissions instance
    """
    if permissions is None:
        permissions = ["read"]
    return UserPermissions(permissions=permissions)


def create_user_info(
    id: str = "test-user-id",
    username: str = "testuser",
    email: str | None = "testuser@example.com",
    first_name: str | None = "Test",
    last_name: str | None = "User",
    full_name: str | None = None,
    realm_roles: StringList | None = None,
    client_roles: ClientRolesDict | None = None,
    permissions: StringList | None = None,
    groups: StringList | None = None,
    client_id: str | None = "test-client",
    realm: str | None = "test-realm",
    claims: TokenPayloadDict | None = None,
) -> UserInfo:
    """Create a UserInfo instance for testing.

    Args:
        id: User ID
        username: Username
        email: User email
        first_name: First name
        last_name: Last name
        full_name: Full name (if None, will be constructed from first/last)
        realm_roles: List of realm role names
        client_roles: Dictionary mapping client IDs to role lists
        permissions: List of permission names
        groups: List of group names
        client_id: Client ID
        realm: Realm name
        claims: Additional JWT claims

    Returns:
        UserInfo instance
    """
    if full_name is None and first_name and last_name:
        full_name = f"{first_name} {last_name}"

    return UserInfo(
        id=id,
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        roles=create_user_roles(realm_roles=realm_roles, client_roles=client_roles),
        permissions=create_user_permissions(permissions=permissions),
        groups=groups or [],
        client_id=client_id,
        realm=realm,
        claims=claims or {},
    )


def create_admin_user_info() -> UserInfo:
    """Create an admin UserInfo instance for testing.

    Returns:
        UserInfo instance with admin roles
    """
    return create_user_info(
        id="admin-user-id",
        username="admin",
        email="admin@example.com",
        realm_roles=["admin", "user"],
        permissions=["read", "write", "delete", "admin"],
    )


def create_regular_user_info() -> UserInfo:
    """Create a regular user UserInfo instance for testing.

    Returns:
        UserInfo instance with basic user roles
    """
    return create_user_info(
        id="regular-user-id",
        username="regularuser",
        email="regularuser@example.com",
        realm_roles=["user"],
        permissions=["read"],
    )


def create_token_payload(
    sub: str = "test-user-id",
    username: str = "testuser",
    email: str | None = "testuser@example.com",
    realm_roles: StringList | None = None,
    client_roles: ClientRolesDict | None = None,
    permissions: StringList | None = None,
    **kwargs: Any,
) -> TokenPayloadDict:
    """Create a JWT token payload for testing.

    Args:
        sub: Subject (user ID)
        username: Username
        email: User email
        realm_roles: List of realm role names
        client_roles: Dictionary mapping client IDs to role lists
        permissions: List of permission names
        **kwargs: Additional claims

    Returns:
        Dictionary representing JWT payload
    """
    payload: TokenPayloadDict = {
        "sub": sub,
        "preferred_username": username,
        "email": email,
        "realm_access": {
            "roles": realm_roles or ["user"],
        },
        "resource_access": {
            client_id: {"roles": roles}
            for client_id, roles in (client_roles or {}).items()
        },
        **kwargs,
    }

    if permissions:
        payload["authorization"] = {
            "permissions": [{"rsname": perm} for perm in permissions]
        }

    return payload
