"""Authentication provider configuration shared by SSO and local JWT modes."""

from enum import StrEnum

from config.settings import settings

from .keycloak.schemas.user import UserInfo, UserPermissions, UserRoles


class AuthMode(StrEnum):
    """Supported authentication providers."""

    SSO = "sso"
    JWT = "jwt"


def is_auth_enabled() -> bool:
    """Return whether authentication enforcement is enabled.

    Returns:
        True when auth dependencies should validate bearer tokens.
    """
    return bool(getattr(settings.auth, "ENABLED", True))


def get_auth_mode() -> AuthMode:
    """Return the configured authentication provider.

    Returns:
        ``AuthMode.SSO`` for Keycloak or ``AuthMode.JWT`` for local accounts.
    """
    return AuthMode(str(getattr(settings.auth, "MODE", AuthMode.SSO)).lower())


def is_sso_mode() -> bool:
    """Return whether Keycloak SSO is the active provider.

    Returns:
        True when auth is enabled and ``auth.MODE`` is ``sso``.
    """
    return is_auth_enabled() and get_auth_mode() is AuthMode.SSO


def is_jwt_mode() -> bool:
    """Return whether local JWT accounts are the active provider.

    Returns:
        True when auth is enabled and ``auth.MODE`` is ``jwt``.
    """
    return is_auth_enabled() and get_auth_mode() is AuthMode.JWT


def build_auth_disabled_user() -> UserInfo:
    """Build a user object for explicit auth-disabled deployments.

    Returns:
        Synthetic user used only when ``auth.ENABLED`` is false.
    """
    return UserInfo(
        id="auth:disabled",
        username="auth_disabled",
        email=None,
        first_name=None,
        last_name=None,
        full_name="Authentication Disabled",
        roles=UserRoles(realm_roles=["auth_disabled"], client_roles={}),
        permissions=UserPermissions(permissions=[]),
        groups=[],
        client_id=None,
        realm=None,
        claims={"auth_disabled": True},
    )


__all__ = [
    "AuthMode",
    "build_auth_disabled_user",
    "get_auth_mode",
    "is_auth_enabled",
    "is_jwt_mode",
    "is_sso_mode",
]
