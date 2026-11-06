"""Parametrized tests for authentication dependencies."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from apps.auth.keycloak.dependencies.auth import get_current_user, verify_token
from apps.auth.keycloak.helpers.exceptions import InvalidTokenError
from apps.core.exceptions import UnauthorizedError

pytestmark = [pytest.mark.unit]


class TestAuthDependenciesParametrized:
    """Parametrized tests for authentication dependencies."""

    @pytest.fixture
    def request_mock(self) -> Request:
        """Create mock FastAPI request."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "authorization,expected_error",
        [
            (None, UnauthorizedError),
            ("", UnauthorizedError),
            ("InvalidFormat token", UnauthorizedError),
            ("Bearer ", UnauthorizedError),
            ("Bearer invalid-token", UnauthorizedError),
            ("Bearer expired-token", UnauthorizedError),
        ],
    )
    async def test_get_current_user_invalid_inputs(
        self, request_mock: Request, authorization, expected_error
    ):
        """Test get_current_user with various invalid authorization headers."""
        from unittest.mock import patch

        with patch(
            "apps.auth.keycloak.utils.jwt_validator.get_jwt_validator"
        ) as mock_get_validator:
            mock_validator = MagicMock()
            mock_validator.extract_token.side_effect = InvalidTokenError()
            mock_get_validator.return_value = mock_validator

            with pytest.raises(expected_error):
                await get_current_user(request_mock, authorization=authorization)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "authorization,expected_error",
        [
            (None, UnauthorizedError),
            ("", UnauthorizedError),
            ("InvalidFormat token", UnauthorizedError),
            ("Bearer ", UnauthorizedError),
            ("Bearer invalid-token", UnauthorizedError),
        ],
    )
    async def test_verify_token_invalid_inputs(self, authorization, expected_error):
        """Test verify_token with various invalid authorization headers."""
        from unittest.mock import MagicMock, patch

        with patch(
            "apps.auth.keycloak.utils.jwt_validator.get_jwt_validator"
        ) as mock_get_validator:
            mock_validator = MagicMock()
            mock_validator.extract_token.side_effect = InvalidTokenError()
            mock_get_validator.return_value = mock_validator

            with pytest.raises(expected_error):
                await verify_token(authorization=authorization)
