"""Keycloak SSO configuration helpers."""

from apps.auth.config import build_auth_disabled_user, is_auth_enabled, is_sso_mode


def is_sso_enabled() -> bool:
    """Return whether Keycloak SSO endpoints are enabled.

    Returns:
        True when auth is enabled and ``auth.MODE`` is ``sso``.
    """
    return is_sso_mode()


__all__ = [
    "build_auth_disabled_user",
    "is_auth_enabled",
    "is_sso_enabled",
]
