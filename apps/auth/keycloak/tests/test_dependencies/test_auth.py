"""Tests for authentication dependencies."""

import pytest
from fastapi import Request

from apps.auth.keycloak.dependencies.auth import (
    get_current_user,
    get_optional_user,
    verify_token,
)
from apps.core.exceptions import UnauthorizedError

pytestmark = [pytest.mark.integration, pytest.mark.keycloak_required]


class TestAuthDependencies:
    """Test cases for authentication dependencies."""

    @pytest.fixture
    def request_mock(self) -> Request:
        """Create mock FastAPI request."""
        from unittest.mock import MagicMock

        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(
        self, request_mock: Request, access_token: str
    ) -> None:
        """Test getting current user with valid token."""
        result = await get_current_user(
            request_mock, authorization=f"Bearer {access_token}"
        )

        assert result.id is not None
        assert result.username is not None

    @pytest.mark.asyncio
    async def test_get_current_user_missing_token(self, request_mock: Request) -> None:
        """Test getting current user with missing token."""
        with pytest.raises(UnauthorizedError, match="Invalid or expired"):
            await get_current_user(request_mock, authorization=None)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, request_mock: Request) -> None:
        """Test getting current user with invalid token."""
        with pytest.raises(UnauthorizedError, match="Invalid or expired"):
            await get_current_user(
                request_mock, authorization="Bearer invalid-token-12345"
            )

    @pytest.mark.asyncio
    async def test_get_current_user_exception(self, request_mock: Request) -> None:
        """Test getting current user with unexpected exception."""
        # Malformed token will likely raise InvalidTokenError, which gets wrapped
        # Expect UnauthorizedError with user-friendly message
        with pytest.raises(UnauthorizedError):
            await get_current_user(request_mock, authorization="Bearer malformed-token")

    @pytest.mark.asyncio
    async def test_get_optional_user_with_token(
        self, request_mock: Request, access_token: str
    ) -> None:
        """Test getting optional user with valid token."""
        result = await get_optional_user(
            request_mock, authorization=f"Bearer {access_token}"
        )

        assert result is not None
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_get_optional_user_no_token(self, request_mock: Request) -> None:
        """Test getting optional user without token."""
        result = await get_optional_user(request_mock, authorization=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_invalid_token(self, request_mock: Request) -> None:
        """Test getting optional user with invalid token."""
        result = await get_optional_user(
            request_mock, authorization="Bearer invalid-token-12345"
        )

        # Should return None instead of raising exception
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, access_token: str) -> None:
        """Test verifying valid token."""
        result = await verify_token(authorization=f"Bearer {access_token}")

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_token_missing(self) -> None:
        """Test verifying missing token."""
        with pytest.raises(UnauthorizedError, match="Invalid or expired"):
            await verify_token(authorization=None)

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self) -> None:
        """Test verifying invalid token."""
        with pytest.raises(UnauthorizedError, match="Invalid or expired"):
            await verify_token(authorization="Bearer invalid-token-12345")

    @pytest.mark.asyncio
    async def test_verify_token_exception(self) -> None:
        """Test verifying token with unexpected exception."""
        # Expect UnauthorizedError with user-friendly message
        with pytest.raises(UnauthorizedError):
            await verify_token(authorization="Bearer malformed-token")
