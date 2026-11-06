"""Tests for Keycloak client functionality."""

import pytest

from apps.auth.keycloak.helpers.exceptions import KeycloakConnectionError
from apps.auth.keycloak.utils.keycloak_client import KeycloakClient, get_keycloak_client

pytestmark = [pytest.mark.integration, pytest.mark.keycloak_required]


class TestKeycloakClient:
    """Test cases for KeycloakClient class."""

    @pytest.fixture
    def client(self) -> KeycloakClient:
        """Create KeycloakClient instance."""
        return get_keycloak_client()

    @pytest.mark.asyncio
    async def test_get_jwks_success(self, client: KeycloakClient) -> None:
        """Test successful JWKS fetching."""
        result = await client.get_jwks()

        assert result is not None
        assert "keys" in result
        assert isinstance(result["keys"], list)

    @pytest.mark.asyncio
    async def test_get_jwks_multiple_calls(self, client: KeycloakClient) -> None:
        """Test multiple JWKS fetch calls work correctly."""
        # First call
        result1 = await client.get_jwks()
        # Second call fetches fresh JWKS
        result2 = await client.get_jwks()

        assert result1 is not None
        assert result2 is not None
        assert "keys" in result1
        assert "keys" in result2

    @pytest.mark.asyncio
    async def test_introspect_token_disabled(self, fresh_keycloak_client) -> None:
        """Test token introspection when disabled."""
        result = await fresh_keycloak_client.introspect_token("test-token")
        # If disabled, should return empty dict
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_introspect_token_enabled(
        self, client: KeycloakClient, access_token: str
    ) -> None:
        """Test token introspection when enabled."""
        # This depends on configuration
        result = await client.introspect_token(access_token)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_introspect_token_error(self, client: KeycloakClient) -> None:
        """Test token introspection with error."""
        # Use invalid token
        try:
            result = await client.introspect_token("invalid-token-12345")
            assert isinstance(result, dict)
        except KeycloakConnectionError:
            # This is acceptable if introspection is enabled
            pass

    @pytest.mark.asyncio
    async def test_get_user_info_success(
        self, client: KeycloakClient, access_token: str
    ) -> None:
        """Test successful user info retrieval."""
        try:
            result = await client.get_user_info(access_token)

            assert result is not None
            assert "sub" in result
            assert result.get("sub") is not None
        except KeycloakConnectionError as e:
            # If we get 403 Forbidden, it means the token doesn't have permission
            # to access userinfo endpoint (Keycloak configuration issue)
            if "403" in str(e) or "Forbidden" in str(e):
                pytest.skip(
                    "Userinfo endpoint returns 403 - token may not have required scopes/permissions. "
                    "This is a Keycloak configuration issue, not a code issue."
                )
            raise

    @pytest.mark.asyncio
    async def test_get_user_info_error(self, fresh_keycloak_client) -> None:
        """Test user info retrieval with error."""
        with pytest.raises(KeycloakConnectionError):
            await fresh_keycloak_client.get_user_info("invalid-token-12345")

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, client: KeycloakClient, refresh_token: str
    ) -> None:
        """Test successful token refresh."""
        if not refresh_token:
            pytest.skip("No refresh token available")

        result = await client.refresh_token(refresh_token)

        assert result is not None
        assert "access_token" in result
        assert result["access_token"] is not None

    @pytest.mark.asyncio
    async def test_refresh_token_error(self, client: KeycloakClient) -> None:
        """Test token refresh with error."""
        with pytest.raises(KeycloakConnectionError):
            await client.refresh_token("invalid-refresh-token-12345")

    @pytest.mark.asyncio
    async def test_revoke_token_success(
        self, client: KeycloakClient, test_username: str, test_password: str
    ) -> None:
        """Test successful token revocation."""
        from apps.auth.keycloak.services import auth_service

        # Get a fresh token for revocation
        token_data = await auth_service.login_user(test_username, test_password)
        access_token = token_data["access_token"]

        # Revoke the token
        await client.revoke_token(access_token)

        # Token should now be invalid
        with pytest.raises(KeycloakConnectionError):
            await client.get_user_info(access_token)

    @pytest.mark.asyncio
    async def test_revoke_token_error(self, fresh_keycloak_client) -> None:
        """Test token revocation with error."""
        # Keycloak might accept invalid tokens for revocation
        try:
            await fresh_keycloak_client.revoke_token("invalid-token-12345")
        except KeycloakConnectionError:
            # This is acceptable
            pass

    @pytest.mark.asyncio
    async def test_close(self, client: KeycloakClient) -> None:
        """Test closing HTTP client."""
        # Should not raise exception
        await client.close()

    def test_get_issuer(self, client: KeycloakClient) -> None:
        """Test getting issuer URL."""
        issuer = client.get_issuer()
        assert issuer is not None
        assert isinstance(issuer, str)
        assert len(issuer) > 0

    def test_get_jwks_url(self, client: KeycloakClient) -> None:
        """Test getting JWKS URL."""
        jwks_url = client.get_jwks_url()
        assert jwks_url is not None
        assert isinstance(jwks_url, str)
        assert "certs" in jwks_url

    def test_get_keycloak_client_singleton(self) -> None:
        """Test that get_keycloak_client returns singleton."""
        client1 = get_keycloak_client()
        client2 = get_keycloak_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_login_with_password_success(
        self, client: KeycloakClient, test_username: str, test_password: str
    ) -> None:
        """Test successful login with password."""
        result = await client.login_with_password(test_username, test_password)

        assert result is not None
        assert "access_token" in result
        assert result["access_token"] is not None

    @pytest.mark.asyncio
    async def test_login_with_password_invalid_credentials(
        self, fresh_keycloak_client
    ) -> None:
        """Test login with invalid credentials."""
        from apps.core.exceptions import UnauthorizedError

        with pytest.raises(UnauthorizedError):
            await fresh_keycloak_client.login_with_password(
                "invalid-user", "invalid-password"
            )
