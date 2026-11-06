"""Parametrized tests for authentication service."""

import pytest

from apps.auth.keycloak.helpers.exceptions import InvalidTokenError
from apps.auth.keycloak.services import auth_service
from apps.core.exceptions import UnauthorizedError

pytestmark = [pytest.mark.unit]


class TestAuthServiceParametrized:
    """Parametrized tests for auth_service."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "token,expected_error",
        [
            ("invalid-token", InvalidTokenError),
            ("expired-token", InvalidTokenError),
            ("malformed.token", InvalidTokenError),
        ],
    )
    async def test_validate_user_token_variations(self, token, expected_error):
        """Test token validation with various invalid inputs."""
        from unittest.mock import AsyncMock, MagicMock, patch

        with patch(
            "apps.auth.keycloak.services.auth_service.get_jwt_validator"
        ) as mock_get_validator:
            mock_validator = MagicMock()
            mock_validator.validate_token = AsyncMock(
                side_effect=InvalidTokenError("Invalid token")
            )
            mock_get_validator.return_value = mock_validator

            with pytest.raises(expected_error):
                await auth_service.validate_user_token(token)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "username,password,should_succeed",
        [
            ("valid-user", "valid-password", True),
            ("invalid-user", "password", False),
            ("user", "invalid-password", False),
            ("", "password", False),
            ("user", "", False),
        ],
    )
    async def test_login_user_credentials_variations(
        self, username, password, should_succeed
    ):
        """Test login with various credential combinations."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "apps.auth.keycloak.utils.keycloak_client.get_keycloak_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            if should_succeed:
                mock_client.login_with_password = AsyncMock(
                    return_value={
                        "access_token": "token",
                        "token_type": "Bearer",
                    }
                )
            else:
                mock_client.login_with_password = AsyncMock(
                    side_effect=UnauthorizedError("Invalid credentials")
                )
            mock_get_client.return_value = mock_client

            if should_succeed:
                result = await auth_service.login_user(username, password)
                assert "access_token" in result
            else:
                with pytest.raises(UnauthorizedError):
                    await auth_service.login_user(username, password)
