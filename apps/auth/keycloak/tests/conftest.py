"""Shared fixtures for authentication tests."""

import asyncio
import os
from collections.abc import Generator

import pytest

from apps.auth.keycloak.services import auth_service
from apps.auth.keycloak.types import TokensDict
from apps.auth.keycloak.utils.jwt_validator import get_jwt_validator
from apps.auth.keycloak.utils.keycloak_client import get_keycloak_client
from config.settings import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped async fixtures.

    Yields:
        asyncio.AbstractEventLoop: Event loop for the test session.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    # Clean up any pending tasks
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    finally:
        loop.close()


@pytest.fixture(scope="session")
def test_username() -> str:
    """Get test username from dynaconf settings or environment variable.

    Checks in order:
    1. settings.test.USERNAME (from .env with APP_TEST__USERNAME or settings.toml)
    2. TEST_USERNAME environment variable (for backward compatibility)

    Returns:
        Test username

    Raises:
        pytest.skip: If test username is not set
    """
    username = None

    # Try dynaconf first (supports APP_TEST__USERNAME env var or settings.toml)
    try:
        if hasattr(settings, "test"):
            username = getattr(settings.test, "USERNAME", None)
            if username:
                return username
    except (AttributeError, KeyError):
        pass

    # Fallback to direct environment variables for backward compatibility
    # Check APP_TEST__USERNAME (dynaconf format)
    username = os.getenv("APP_TEST__USERNAME")
    if username:
        return username

    # Check TEST_USERNAME (legacy format)
    username = os.getenv("TEST_USERNAME")
    if username:
        return username

    # No username found
    pytest.skip(
        "Test username not set. Set one of:\n"
        "  - APP_TEST__USERNAME environment variable (recommended)\n"
        "  - TEST_USERNAME environment variable (legacy)\n"
        "  - settings.test.USERNAME in settings.toml"
    )
    return ""  # type: ignore[unreachable]  # Never reached, pytest.skip raises


@pytest.fixture(scope="session")
def test_password() -> str:
    """Get test password from dynaconf settings or environment variable.

    Checks in order:
    1. settings.test.PASSWORD (from .env with APP_TEST__PASSWORD or settings.toml)
    2. TEST_PASSWORD environment variable (for backward compatibility)

    Returns:
        Test password

    Raises:
        pytest.skip: If test password is not set
    """
    password = None

    # Try dynaconf first (supports APP_TEST__PASSWORD env var or settings.toml)
    try:
        if hasattr(settings, "test"):
            password = getattr(settings.test, "PASSWORD", None)
            if password:
                return password
    except (AttributeError, KeyError):
        pass

    # Fallback to direct environment variables for backward compatibility
    # Check APP_TEST__PASSWORD (dynaconf format)
    password = os.getenv("APP_TEST__PASSWORD")
    if password:
        return password

    # Check TEST_PASSWORD (legacy format)
    password = os.getenv("TEST_PASSWORD")
    if password:
        return password

    # No password found
    pytest.skip(
        "Test password not set. Set one of:\n"
        "  - APP_TEST__PASSWORD environment variable (recommended)\n"
        "  - TEST_PASSWORD environment variable (legacy)\n"
        "  - settings.test.PASSWORD in settings.toml"
    )
    return ""  # type: ignore[unreachable]  # Never reached, pytest.skip raises


@pytest.fixture(scope="session")
def authenticated_tokens(
    event_loop, test_username: str, test_password: str
) -> Generator[TokensDict, None, None]:
    """Get authenticated tokens from Keycloak.

    Args:
        event_loop: Event loop for async operations
        test_username: Test username
        test_password: Test password

    Yields:
        Dictionary with access_token and refresh_token

    Raises:
        pytest.skip: If authentication fails
    """
    try:
        # Use the event loop to run async operation
        token_data = event_loop.run_until_complete(
            auth_service.login_user(test_username, test_password)
        )
        tokens = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
        }
        yield tokens
    except Exception as e:
        pytest.skip(f"Failed to authenticate test user: {str(e)}")
    finally:
        # Ensure event loop is still open for cleanup if needed
        pass


@pytest.fixture(scope="session")
def access_token(authenticated_tokens: TokensDict) -> str:
    """Get access token from authenticated tokens.

    Args:
        authenticated_tokens: Dictionary with tokens

    Returns:
        Access token string
    """
    return authenticated_tokens["access_token"]


@pytest.fixture(scope="session")
def refresh_token(authenticated_tokens: TokensDict) -> str:
    """Get refresh token from authenticated tokens.

    Args:
        authenticated_tokens: Dictionary with tokens

    Returns:
        Refresh token string
    """
    return authenticated_tokens.get("refresh_token", "")


@pytest.fixture(scope="session")
def authenticated_user_info(event_loop, access_token: str) -> dict | None:
    """Get authenticated user info from Keycloak.

    Args:
        event_loop: Event loop for async operations
        access_token: Access token

    Returns:
        User info dictionary or None if userinfo endpoint is not available

    Note:
        This fixture may return None if the Keycloak userinfo endpoint
        returns 403 Forbidden or is otherwise unavailable. Tests should
        handle this gracefully by extracting user info from the token
        payload instead.
    """
    try:
        return event_loop.run_until_complete(auth_service.get_user_info(access_token))
    except Exception:
        # Userinfo endpoint may not be available (e.g., 403 Forbidden)
        # Return None to allow tests to proceed by extracting info from token
        return None


@pytest.fixture(scope="session")
def jwt_validator():
    """Get JWT validator instance.

    Returns:
        JWTValidator: Global JWT validator instance.
    """
    return get_jwt_validator()


@pytest.fixture(scope="session")
def keycloak_client():
    """Get Keycloak client instance.

    Returns:
        KeycloakClient | None: Global Keycloak client or None if disabled.
    """
    return get_keycloak_client()


@pytest.fixture(scope="function", autouse=True)
def reset_keycloak_client():
    """Reset Keycloak client singleton before each test.

    This ensures each test gets a fresh client instance created in its own
    event loop, preventing "bound to a different event loop" errors.

    Note: We don't close the client here to avoid "client has been closed" errors
    in subsequent tests. The client will be cleaned up at the end of the test session.

    Yields:
        None: Control returns to test; cleanup runs after yield.
    """
    from apps.auth.keycloak.utils import keycloak_client as keycloak_client_module

    # Store old instance to restore after test
    old_instance = keycloak_client_module._client_instance

    # Reset singleton to None so a new instance is created for this test
    keycloak_client_module._client_instance = None

    yield

    # Don't close the new instance - let it remain for potential reuse
    # Just restore the old instance (which may be None or the previous instance)
    keycloak_client_module._client_instance = old_instance


@pytest.fixture(scope="function")
def request_mock():
    """Create a mock FastAPI request object.

    Returns:
        MagicMock: Mock FastAPI Request with client.host set.
    """
    from unittest.mock import MagicMock

    from fastapi import Request

    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture(scope="function")
def fresh_keycloak_client():
    """Get a fresh Keycloak client instance for the current test.

    This ensures the client is created in the test's event loop context.

    Yields:
        KeycloakClient | None: Fresh client instance; previous instance restored after test.
    """
    from apps.auth.keycloak.utils import keycloak_client as keycloak_client_module

    # Store the old instance
    old_instance = keycloak_client_module._client_instance

    # Reset the singleton to get a fresh instance
    keycloak_client_module._client_instance = None

    # Get a new client instance (will be created in current event loop)
    client = get_keycloak_client()

    yield client

    # Clean up: close the new instance
    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # If loop is running, schedule close
            asyncio.create_task(client.close())
        except RuntimeError:
            # No running loop, try to get event loop
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    if loop.is_running():
                        # Schedule close if loop is running
                        asyncio.create_task(client.close())
                    else:
                        # Run close if loop is not running
                        loop.run_until_complete(client.close())
            except (RuntimeError, Exception):
                # Ignore errors during cleanup (event loop might be closed)
                pass
    except Exception:
        # Ignore all errors during cleanup
        pass

    # Restore old instance
    keycloak_client_module._client_instance = old_instance
