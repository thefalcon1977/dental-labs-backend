"""Unit tests for token service with mocks."""

from unittest.mock import AsyncMock, patch

import pytest

from apps.auth.keycloak.helpers.exceptions import KeycloakConnectionError
from apps.auth.keycloak.schemas.token import RefreshTokenResponse
from apps.auth.keycloak.services import token_service

pytestmark = [pytest.mark.unit]


class TestTokenServiceUnit:
    """Unit tests for token_service with mocked dependencies."""

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_refresh_access_token_success(self, mock_get_client):
        """Test successful token refresh with mocked client."""
        # Arrange
        mock_client = AsyncMock()
        mock_token_data = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 300,
            "token_type": "Bearer",
        }
        mock_client.refresh_token = AsyncMock(return_value=mock_token_data)
        mock_get_client.return_value = mock_client

        # Act
        result = await token_service.refresh_access_token("refresh-token")

        # Assert
        assert isinstance(result, RefreshTokenResponse)
        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"
        assert result.expires_in == 300
        assert result.token_type == "Bearer"
        mock_client.refresh_token.assert_called_once_with("refresh-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_refresh_access_token_no_new_refresh_token(self, mock_get_client):
        """Test token refresh when Keycloak doesn't return new refresh token."""
        # Arrange
        mock_client = AsyncMock()
        mock_token_data = {
            "access_token": "new-access-token",
            "expires_in": 300,
            "token_type": "Bearer",
            # No refresh_token in response
        }
        mock_client.refresh_token = AsyncMock(return_value=mock_token_data)
        mock_get_client.return_value = mock_client

        # Act
        result = await token_service.refresh_access_token("old-refresh-token")

        # Assert
        assert result.access_token == "new-access-token"
        # Should use old refresh token if new one not provided
        assert result.refresh_token == "old-refresh-token"

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_refresh_access_token_keycloak_error(self, mock_get_client):
        """Test token refresh when Keycloak fails."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.refresh_token = AsyncMock(
            side_effect=KeycloakConnectionError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await token_service.refresh_access_token("refresh-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_introspect_token_success(self, mock_get_client):
        """Test successful token introspection with mocked client."""
        # Arrange
        mock_client = AsyncMock()
        mock_introspection = {
            "active": True,
            "sub": "user-123",
            "exp": 1234567890,
        }
        mock_client.introspect_token = AsyncMock(return_value=mock_introspection)
        mock_get_client.return_value = mock_client

        # Act
        result = await token_service.introspect_token("access-token")

        # Assert
        assert result["active"] is True
        assert result["sub"] == "user-123"
        mock_client.introspect_token.assert_called_once_with("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_introspect_token_inactive(self, mock_get_client):
        """Test token introspection with inactive token."""
        # Arrange
        mock_client = AsyncMock()
        mock_introspection = {"active": False}
        mock_client.introspect_token = AsyncMock(return_value=mock_introspection)
        mock_get_client.return_value = mock_client

        # Act
        result = await token_service.introspect_token("access-token")

        # Assert
        assert result["active"] is False

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_introspect_token_keycloak_error(self, mock_get_client):
        """Test token introspection when Keycloak fails."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.introspect_token = AsyncMock(
            side_effect=KeycloakConnectionError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await token_service.introspect_token("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_revoke_token_success(self, mock_get_client):
        """Test successful token revocation with mocked dependencies."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.revoke_token = AsyncMock(return_value=None)
        mock_get_client.return_value = mock_client

        # Act
        await token_service.revoke_token("access-token")

        # Assert
        mock_client.revoke_token.assert_called_once_with("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.token_service.get_keycloak_client")
    async def test_revoke_token_keycloak_error(self, mock_get_client):
        """Test token revocation when Keycloak fails."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.revoke_token = AsyncMock(
            side_effect=KeycloakConnectionError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await token_service.revoke_token("access-token")
