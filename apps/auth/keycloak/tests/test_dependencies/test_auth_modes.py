"""Tests for SSO-only authentication behavior."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from apps.auth.keycloak.dependencies import auth as auth_dependency
from apps.auth.keycloak.helpers.exceptions import AuthDisabledError
from apps.auth.keycloak.schemas.user import UserInfo, UserPermissions, UserRoles
from apps.auth.keycloak.services import auth_service
from apps.auth.keycloak.types import TokenDataDict
from apps.auth.keycloak.utils import keycloak_client


@pytest.fixture
def request_mock() -> Request:
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.mark.asyncio
async def test_get_current_user_returns_synthetic_user_when_auth_disabled(
    request_mock: Request,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure explicit auth disable bypasses SSO token validation."""
    monkeypatch.setattr(auth_dependency, "is_auth_enabled", lambda: False)

    user = await auth_dependency.get_current_user(request_mock, authorization=None)

    assert user.id == "auth:disabled"
    assert user.claims["auth_disabled"] is True


@pytest.mark.asyncio
async def test_get_current_user_or_system_delegates_to_sso_user(
    request_mock: Request,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure compatibility wrapper still uses Keycloak bearer auth."""

    async def fake_get_current_user(
        request: Request,
        authorization: str | None = None,
    ) -> UserInfo:
        """Return a fake Keycloak user from the bearer dependency."""
        assert request is request_mock
        assert authorization == "Bearer token"
        return UserInfo(
            id="user-1",
            username="sso-user",
            roles=UserRoles(realm_roles=["user"], client_roles={}),
            permissions=UserPermissions(permissions=[]),
            groups=[],
            claims={},
        )

    monkeypatch.setattr(auth_dependency, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth_dependency, "get_current_user", fake_get_current_user)

    user = await auth_dependency.get_current_user_or_system(
        request_mock,
        authorization="Bearer token",
    )

    assert user.id == "user-1"
    assert user.username == "sso-user"


@pytest.mark.asyncio
async def test_login_user_rejects_when_sso_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure SSO login does not contact Keycloak when SSO is disabled."""
    monkeypatch.setattr(auth_service, "is_sso_enabled", lambda: False)

    with pytest.raises(AuthDisabledError):
        await auth_service.login_user("user", "password")


@pytest.mark.asyncio
async def test_login_user_uses_keycloak_when_sso_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure SSO login delegates username/password auth to Keycloak."""

    class FakeKeycloakClient:
        """Fake Keycloak client for SSO login delegation."""

        async def login_with_password(
            self,
            username: str,
            password: str,
        ) -> TokenDataDict:
            """Return fake token data for matching credentials."""
            assert username == "user"
            assert password == "password"
            return {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_in": 300,
                "token_type": "Bearer",
            }

    monkeypatch.setattr(auth_service, "is_sso_enabled", lambda: True)
    monkeypatch.setattr(keycloak_client, "get_keycloak_client", FakeKeycloakClient)

    result = await auth_service.login_user("user", "password")

    assert result["access_token"] == "access"
    assert result["refresh_token"] == "refresh"
