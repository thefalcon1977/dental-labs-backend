"""Unit tests for authentication service with mocks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.auth.keycloak.helpers.exceptions import (
    InvalidTokenError,
    KeycloakConnectionError,
)
from apps.auth.keycloak.services import auth_service
from apps.core.exceptions import UnauthorizedError

pytestmark = [pytest.mark.unit]


class TestAuthServiceUnit:
    """Unit tests for auth_service with mocked dependencies."""

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.auth_service.get_jwt_validator")
    async def test_validate_user_token_success(self, mock_get_validator):
        """Test successful token validation with mocked validator."""
        # Arrange
        mock_validator = MagicMock()
        mock_payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
        }
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        mock_validator.validate_token = AsyncMock(return_value=mock_payload)
        mock_validator.get_user_from_token.return_value = mock_user
        mock_get_validator.return_value = mock_validator

        # Act
        result = await auth_service.validate_user_token("valid-token")

        # Assert
        assert result.id == "user-123"
        assert result.username == "testuser"
        mock_validator.validate_token.assert_called_once_with("valid-token")
        mock_validator.get_user_from_token.assert_called_once_with(mock_payload)

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.auth_service.get_jwt_validator")
    async def test_validate_user_token_invalid(self, mock_get_validator):
        """Test token validation with invalid token."""
        # Arrange
        mock_validator = MagicMock()
        mock_validator.validate_token = AsyncMock(
            side_effect=InvalidTokenError("Invalid token")
        )
        mock_get_validator.return_value = mock_validator

        # Act & Assert
        with pytest.raises(InvalidTokenError):
            await auth_service.validate_user_token("invalid-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.utils.keycloak_client.get_keycloak_client")
    async def test_login_user_success(self, mock_get_client):
        """Test successful user login with mocked Keycloak client."""
        # Arrange
        mock_client = AsyncMock()
        mock_token_data = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-123",
            "token_type": "Bearer",
            "expires_in": 300,
        }
        mock_client.login_with_password = AsyncMock(return_value=mock_token_data)
        mock_get_client.return_value = mock_client

        # Act
        result = await auth_service.login_user("testuser", "password123")

        # Assert
        assert result["access_token"] == "access-token-123"
        assert result["refresh_token"] == "refresh-token-123"
        mock_client.login_with_password.assert_called_once_with(
            "testuser", "password123"
        )

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.utils.keycloak_client.get_keycloak_client")
    async def test_login_user_invalid_credentials(self, mock_get_client):
        """Test login with invalid credentials."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.login_with_password = AsyncMock(
            side_effect=UnauthorizedError("Invalid credentials")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(UnauthorizedError):
            await auth_service.login_user("invalid", "wrong")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.utils.keycloak_client.get_keycloak_client")
    async def test_login_user_keycloak_error(self, mock_get_client):
        """Test login when Keycloak is unavailable."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.login_with_password = AsyncMock(
            side_effect=KeycloakConnectionError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await auth_service.login_user("testuser", "password123")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.utils.keycloak_client.get_keycloak_client")
    async def test_get_user_info_success(self, mock_get_client):
        """Test successful user info retrieval with mocked client."""
        # Arrange
        mock_client = AsyncMock()
        mock_user_info = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
        }
        mock_client.get_user_info = AsyncMock(return_value=mock_user_info)
        mock_get_client.return_value = mock_client

        # Act
        result = await auth_service.get_user_info("access-token")

        # Assert
        assert result["sub"] == "user-123"
        assert result["preferred_username"] == "testuser"
        mock_client.get_user_info.assert_called_once_with("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.utils.keycloak_client.get_keycloak_client")
    async def test_get_user_info_keycloak_error(self, mock_get_client):
        """Test user info retrieval when Keycloak fails."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.get_user_info = AsyncMock(
            side_effect=KeycloakConnectionError("Connection failed")
        )
        mock_get_client.return_value = mock_client

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await auth_service.get_user_info("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.auth_service.revoke_token")
    async def test_logout_user_success(self, mock_revoke_token):
        """Test successful logout with mocked token revocation."""
        # Arrange
        mock_revoke_token.return_value = None

        # Act
        await auth_service.logout_user("access-token", "refresh-token")

        # Assert
        assert mock_revoke_token.call_count == 2
        mock_revoke_token.assert_any_call("access-token")
        mock_revoke_token.assert_any_call("refresh-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.auth_service.revoke_token")
    async def test_logout_user_access_token_only(self, mock_revoke_token):
        """Test logout with only access token."""
        # Arrange
        mock_revoke_token.return_value = None

        # Act
        await auth_service.logout_user("access-token", None)

        # Assert
        mock_revoke_token.assert_called_once_with("access-token")

    @pytest.mark.asyncio
    @patch("apps.auth.keycloak.services.auth_service.revoke_token")
    async def test_logout_user_revocation_error(self, mock_revoke_token):
        """Test logout when token revocation fails."""
        # Arrange
        mock_revoke_token.side_effect = KeycloakConnectionError("Revocation failed")

        # Act & Assert
        with pytest.raises(KeycloakConnectionError):
            await auth_service.logout_user("access-token", "refresh-token")
