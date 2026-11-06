"""Keycloak configuration validation utilities."""

import httpx

from config.logging import get_logger
from config.settings import settings

from ..types import ConfigValidationResult, StringList

logger = get_logger(__name__)


class KeycloakConfigError(Exception):
    """Exception raised for Keycloak configuration errors."""

    pass


async def validate_keycloak_config() -> ConfigValidationResult:
    """Validate Keycloak configuration on startup.

    Checks:
    - Server URL is accessible
    - Realm exists
    - JWKS endpoint is accessible
    - Client ID is configured
    - Client secret is configured (if required)

    Returns:
        Tuple of (is_valid boolean, list of warnings/errors)
    """
    warnings: StringList = []
    is_valid = True

    # Check required settings
    server_url = getattr(settings.keycloak, "SERVER_URL", None)
    realm = getattr(settings.keycloak, "REALM", None)
    client_id = getattr(settings.keycloak, "CLIENT_ID", None)

    if not server_url or server_url == "http://localhost:8080":
        warnings.append(
            "Keycloak SERVER_URL is not configured or using default. "
            "Please set APP_KEYCLOAK__SERVER_URL in your environment."
        )
        is_valid = False

    if not realm or realm == "master":
        warnings.append(
            "Keycloak REALM is using default 'master'. "
            "Consider creating a dedicated realm for your application."
        )

    if not client_id or client_id == "your-client-id":
        warnings.append(
            "Keycloak CLIENT_ID is not configured or using default. "
            "Please set APP_KEYCLOAK__CLIENT_ID in your environment."
        )
        is_valid = False

    # Check JWKS endpoint accessibility
    if server_url and realm:
        try:
            jwks_url = (
                f"{server_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/certs"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(jwks_url)
                if response.status_code == 200:
                    jwks = response.json()
                    keys_count = len(jwks.get("keys", []))
                    if keys_count == 0:
                        warnings.append(
                            "JWKS endpoint returned no keys. "
                            "Keycloak may not be properly configured."
                        )
                    else:
                        logger.debug(
                            "JWKS endpoint validation successful",
                            keys_count=keys_count,
                        )
                else:
                    warnings.append(
                        f"JWKS endpoint returned status {response.status_code}. "
                        "Keycloak may not be accessible."
                    )
                    is_valid = False
        except httpx.TimeoutException:
            warnings.append(
                "Timeout connecting to Keycloak JWKS endpoint. "
                "Keycloak server may be unreachable."
            )
            is_valid = False
        except httpx.ConnectError:
            warnings.append(
                "Cannot connect to Keycloak server. "
                "Please verify SERVER_URL is correct and Keycloak is running."
            )
            is_valid = False
        except Exception as e:
            warnings.append(f"Error validating Keycloak configuration: {str(e)}")
            is_valid = False

    # Check client secret (warn if missing but don't fail)
    client_secret = getattr(settings.keycloak, "CLIENT_SECRET", None)
    if not client_secret or client_secret == "your-client-secret":
        warnings.append(
            "Keycloak CLIENT_SECRET is not configured or using default. "
            "This may be required for confidential clients."
        )

    return is_valid, warnings


def validate_keycloak_config_sync() -> ConfigValidationResult:
    """Synchronous version of configuration validation (for startup).

    Returns:
        Tuple of (is_valid boolean, list of warnings/errors)
    """
    warnings: StringList = []
    is_valid = True

    # Check required settings
    server_url = getattr(settings.keycloak, "SERVER_URL", None)
    realm = getattr(settings.keycloak, "REALM", None)
    client_id = getattr(settings.keycloak, "CLIENT_ID", None)

    if not server_url or server_url == "http://localhost:8080":
        warnings.append(
            "Keycloak SERVER_URL is not configured or using default. "
            "Please set APP_KEYCLOAK__SERVER_URL in your environment."
        )
        is_valid = False

    if not realm or realm == "master":
        warnings.append(
            "Keycloak REALM is using default 'master'. "
            "Consider creating a dedicated realm for your application."
        )

    if not client_id or client_id == "your-client-id":
        warnings.append(
            "Keycloak CLIENT_ID is not configured or using default. "
            "Please set APP_KEYCLOAK__CLIENT_ID in your environment."
        )
        is_valid = False

    # Check client secret (warn if missing but don't fail)
    client_secret = getattr(settings.keycloak, "CLIENT_SECRET", None)
    if not client_secret or client_secret == "your-client-secret":
        warnings.append(
            "Keycloak CLIENT_SECRET is not configured or using default. "
            "This may be required for confidential clients."
        )

    return is_valid, warnings
