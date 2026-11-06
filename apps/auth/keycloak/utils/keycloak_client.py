"""Async HTTP client for Keycloak API operations."""

import time
from urllib.parse import quote

import httpx

from apps.core.exceptions import ConflictError
from config.logging import get_logger, get_request_id
from config.settings import settings

from ..helpers.exceptions import KeycloakConnectionError
from ..types import (
    IntrospectionDict,
    JWKSDict,
    ParamsDict,
    QueryParamsStrDict,
    RawKeycloakDict,
    RawKeycloakList,
    TokenDataDict,
    UserInfoDict,
)

logger = get_logger(__name__)

# Admin API token cache TTL (seconds); keep short to avoid stale tokens
_ADMIN_TOKEN_CACHE_TTL = 55.0


async def _add_request_id_header(request: httpx.Request) -> None:
    """Add X-Request-ID to outbound request when present in context (observability)."""
    request_id = get_request_id()
    if request_id:
        request.headers["X-Request-ID"] = request_id


class KeycloakClient:
    """Async HTTP client for Keycloak API operations.

    Handles JWKS fetching, token introspection, user info retrieval,
    and token refresh operations.
    """

    def __init__(self) -> None:
        """Initialize Keycloak client with configuration."""
        server_url = settings.keycloak.SERVER_URL.rstrip("/")

        # Ensure server URL has a protocol
        if not server_url.startswith(("http://", "https://")):
            # Default to http:// if no protocol specified
            logger.warning(
                "Keycloak SERVER_URL missing protocol, defaulting to http://",
                server_url=server_url,
            )
            server_url = f"http://{server_url}"

        self.server_url = server_url
        self.realm = settings.keycloak.REALM
        self.client_id = settings.keycloak.CLIENT_ID
        self.client_secret = getattr(settings.keycloak, "CLIENT_SECRET", None)
        # Optional: dedicated client for Admin API (client_credentials); if not set, use CLIENT_ID/CLIENT_SECRET
        self.admin_client_id = getattr(settings.keycloak, "ADMIN_CLIENT_ID", None)
        self.admin_client_secret = getattr(
            settings.keycloak, "ADMIN_CLIENT_SECRET", None
        )
        self.introspection_enabled = getattr(
            settings.keycloak, "TOKEN_INTROSPECTION_ENABLED", False
        )

        # Build URLs
        self.realm_url = f"{self.server_url}/realms/{self.realm}"
        self.jwks_url = f"{self.realm_url}/protocol/openid-connect/certs"
        self.issuer = f"{self.realm_url}"
        self.introspection_url = (
            f"{self.realm_url}/protocol/openid-connect/token/introspect"
        )
        self.userinfo_url = f"{self.realm_url}/protocol/openid-connect/userinfo"
        self.token_url = f"{self.realm_url}/protocol/openid-connect/token"
        # Admin REST API base (requires client with realm-management roles)
        self.admin_url = f"{self.server_url}/admin/realms/{self.realm}"
        self._admin_token: str | None = None
        self._admin_token_expires_at: float = 0.0

        # HTTP client with connection pooling
        # Store these for potential client recreation.
        # Defaults allow for slow TLS through proxies (e.g. JWKS fetch).
        self.http_timeout = getattr(settings.keycloak, "HTTP_TIMEOUT", 25.0)
        self.http_connect_timeout = getattr(
            settings.keycloak, "HTTP_CONNECT_TIMEOUT", 15.0
        )
        self.http_max_connections = getattr(
            settings.keycloak, "HTTP_MAX_CONNECTIONS", 100
        )
        self.http_max_keepalive = getattr(
            settings.keycloak, "HTTP_MAX_KEEPALIVE_CONNECTIONS", 20
        )
        self.http_keepalive_expiry = getattr(
            settings.keycloak, "HTTP_KEEPALIVE_EXPIRY", 30.0
        )

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=self.http_timeout,
                connect=self.http_connect_timeout,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=self.http_max_keepalive,
                max_connections=self.http_max_connections,
                keepalive_expiry=self.http_keepalive_expiry,
            ),
            follow_redirects=True,
            event_hooks={"request": [_add_request_id_header]},
        )

    async def get_jwks(self) -> JWKSDict:
        """Fetch JWKS (JSON Web Key Set) from Keycloak.

        Returns:
            JWKS dictionary with public keys

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        from config.metrics.keycloak import (
            keycloak_jwks_fetches_total,
            keycloak_request_duration_seconds,
        )

        start_time = time.time()
        try:
            logger.debug("Fetching JWKS from Keycloak", url=self.jwks_url)
            response = await self.client.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()

            # Track metrics
            duration = time.time() - start_time
            keycloak_jwks_fetches_total.labels(status="success").inc()
            keycloak_request_duration_seconds.labels(endpoint="jwks").observe(duration)

            logger.debug(
                "JWKS fetched successfully", keys_count=len(jwks.get("keys", []))
            )
            return jwks
        except httpx.HTTPError as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_jwks_fetches_total.labels(status="error").inc()
            keycloak_request_duration_seconds.labels(endpoint="jwks").observe(duration)

            logger.error(
                "Failed to fetch JWKS from Keycloak",
                url=self.jwks_url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def introspect_token(self, token: str) -> IntrospectionDict:
        """Introspect token to check if it's still valid.

        Args:
            token: Access token to introspect

        Returns:
            Token introspection response

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        from config.metrics.keycloak import (
            keycloak_request_duration_seconds,
            keycloak_token_introspections_total,
        )

        if not self.introspection_enabled:
            logger.debug("Token introspection is disabled")
            return {}

        start_time = time.time()
        try:
            logger.debug("Introspecting token")
            data = {
                "token": token,
                "client_id": self.client_id,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await self.client.post(
                self.introspection_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            result = response.json()

            # Track metrics
            duration = time.time() - start_time
            status = "active" if result.get("active", False) else "inactive"
            keycloak_token_introspections_total.labels(status=status).inc()
            keycloak_request_duration_seconds.labels(endpoint="introspect").observe(
                duration
            )

            logger.debug(
                "Token introspection completed",
                active=result.get("active", False),
            )
            return result
        except httpx.HTTPError as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_token_introspections_total.labels(status="error").inc()
            keycloak_request_duration_seconds.labels(endpoint="introspect").observe(
                duration
            )

            logger.error(
                "Failed to introspect token",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user_info(self, token: str) -> UserInfoDict:
        """Get user information from Keycloak.

        Args:
            token: Access token

        Returns:
            User information dictionary

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        from config.metrics.keycloak import (
            keycloak_errors_total,
            keycloak_request_duration_seconds,
            keycloak_requests_total,
        )

        start_time = time.time()
        try:
            logger.debug("Fetching user info from Keycloak")
            response = await self.client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            user_info = response.json()

            # Track metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="userinfo", status="success").inc()
            keycloak_request_duration_seconds.labels(endpoint="userinfo").observe(
                duration
            )

            logger.debug(
                "User info fetched",
                user_id=user_info.get("sub"),
                username=user_info.get("preferred_username"),
            )
            return user_info
        except httpx.HTTPError as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="userinfo", status="error").inc()
            keycloak_errors_total.labels(
                endpoint="userinfo", error_type=type(e).__name__
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="userinfo").observe(
                duration
            )

            logger.error(
                "Failed to fetch user info",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def refresh_token(self, refresh_token: str) -> TokenDataDict:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Token response with new access and refresh tokens

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        from config.metrics.keycloak import (
            keycloak_errors_total,
            keycloak_request_duration_seconds,
            keycloak_requests_total,
        )

        start_time = time.time()
        try:
            logger.debug("Refreshing access token")
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()

            # Track metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(
                endpoint="refresh_token", status="success"
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="refresh_token").observe(
                duration
            )

            logger.info("Token refreshed successfully")
            return token_data
        except httpx.HTTPError as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(
                endpoint="refresh_token", status="error"
            ).inc()
            keycloak_errors_total.labels(
                endpoint="refresh_token", error_type=type(e).__name__
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="refresh_token").observe(
                duration
            )

            logger.error(
                "Failed to refresh token",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def login_with_password(self, username: str, password: str) -> TokenDataDict:
        """Login with username and password to get tokens.

        Args:
            username: Username for authentication
            password: Password for authentication

        Returns:
            Token response with access and refresh tokens

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
            UnauthorizedError: If credentials are invalid
        """
        from config.metrics.keycloak import (
            keycloak_errors_total,
            keycloak_request_duration_seconds,
            keycloak_requests_total,
        )

        start_time = time.time()
        try:
            logger.debug(
                "Logging in with username and password",
                username=username,
                token_url=self.token_url,
                client_id=self.client_id,
            )
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": self.client_id,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            logger.debug(
                "Sending token request",
                url=self.token_url,
                grant_type="password",
                client_id=self.client_id,
            )

            # Retry logic for 502 Bad Gateway (connection pooling issues)
            max_retries = 2
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    response = await self.client.post(
                        self.token_url,
                        data=data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    logger.debug(
                        "Token request response",
                        status_code=response.status_code,
                        url=str(response.url),
                        attempt=attempt + 1,
                    )

                    # If we get a 502, try to reset connection and retry
                    if response.status_code == 502 and attempt < max_retries:
                        logger.warning(
                            "Received 502 Bad Gateway, resetting connection and retrying",
                            attempt=attempt + 1,
                            max_retries=max_retries + 1,
                        )
                        # Close and recreate the client to reset connections
                        await self.client.aclose()
                        self.client = httpx.AsyncClient(
                            timeout=httpx.Timeout(
                                timeout=self.http_timeout,
                                connect=self.http_connect_timeout,
                            ),
                            limits=httpx.Limits(
                                max_keepalive_connections=self.http_max_keepalive,
                                max_connections=self.http_max_connections,
                                keepalive_expiry=self.http_keepalive_expiry,
                            ),
                            follow_redirects=True,
                            event_hooks={"request": [_add_request_id_header]},
                        )
                        continue

                    # Break out of retry loop if successful or non-502 error
                    break

                except httpx.HTTPStatusError as e:
                    # If 502 and we have retries left, reset connection and retry
                    if e.response.status_code == 502 and attempt < max_retries:
                        logger.warning(
                            "Received 502 Bad Gateway exception, resetting connection and retrying",
                            attempt=attempt + 1,
                            max_retries=max_retries + 1,
                            error=str(e),
                        )
                        # Close and recreate the client to reset connections
                        await self.client.aclose()
                        self.client = httpx.AsyncClient(
                            timeout=httpx.Timeout(
                                timeout=self.http_timeout,
                                connect=self.http_connect_timeout,
                            ),
                            limits=httpx.Limits(
                                max_keepalive_connections=self.http_max_keepalive,
                                max_connections=self.http_max_connections,
                                keepalive_expiry=self.http_keepalive_expiry,
                            ),
                            follow_redirects=True,
                            event_hooks={"request": [_add_request_id_header]},
                        )
                        last_exception = e
                        continue
                    # Re-raise if not 502 or no retries left
                    raise
                except Exception as e:
                    # For other exceptions, don't retry
                    last_exception = e
                    raise

            # If we exhausted retries, raise the last exception
            if last_exception:
                raise last_exception

            # Handle authentication errors
            if response.status_code == 401:
                duration = time.time() - start_time
                keycloak_requests_total.labels(
                    endpoint="login", status="unauthorized"
                ).inc()
                keycloak_request_duration_seconds.labels(endpoint="login").observe(
                    duration
                )
                logger.warning(
                    "Login failed: invalid credentials",
                    username=username,
                )
                from apps.core.exceptions import UnauthorizedError

                raise UnauthorizedError("Invalid username or password")

            response.raise_for_status()
            token_data = response.json()

            # Track metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="login", status="success").inc()
            keycloak_request_duration_seconds.labels(endpoint="login").observe(duration)

            logger.info("Login successful", username=username)
            return token_data
        except httpx.HTTPStatusError as e:
            duration = time.time() - start_time
            if e.response.status_code == 401:
                keycloak_requests_total.labels(
                    endpoint="login", status="unauthorized"
                ).inc()
                logger.warning(
                    "Login failed: invalid credentials",
                    username=username,
                )
                from apps.core.exceptions import UnauthorizedError

                raise UnauthorizedError("Invalid username or password") from e
            keycloak_requests_total.labels(endpoint="login", status="error").inc()
            keycloak_errors_total.labels(
                endpoint="login", error_type=type(e).__name__
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="login").observe(duration)

            logger.error(
                "Failed to login",
                error=str(e),
                error_type=type(e).__name__,
                status_code=e.response.status_code if hasattr(e, "response") else None,
                token_url=self.token_url,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="login", status="error").inc()
            keycloak_errors_total.labels(
                endpoint="login", error_type=type(e).__name__
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="login").observe(duration)
            logger.error(
                "Failed to login",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def revoke_token(self, token: str) -> None:
        """Revoke token (logout).

        Args:
            token: Token to revoke (can be access or refresh token)

        Raises:
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        from config.metrics.keycloak import (
            keycloak_errors_total,
            keycloak_request_duration_seconds,
            keycloak_requests_total,
        )

        start_time = time.time()
        try:
            logger.debug("Revoking token")
            revoke_url = f"{self.realm_url}/protocol/openid-connect/logout"
            data = {
                "token": token,
                "client_id": self.client_id,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            response = await self.client.post(
                revoke_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            # Track metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="revoke", status="success").inc()
            keycloak_request_duration_seconds.labels(endpoint="revoke").observe(
                duration
            )

            logger.info("Token revoked successfully")
        except httpx.HTTPError as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_requests_total.labels(endpoint="revoke", status="error").inc()
            keycloak_errors_total.labels(
                endpoint="revoke", error_type=type(e).__name__
            ).inc()
            keycloak_request_duration_seconds.labels(endpoint="revoke").observe(
                duration
            )

            logger.error(
                "Failed to revoke token",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def _get_admin_token(self) -> str:
        """Obtain and cache Bearer token for Admin REST API (client_credentials).

        Uses ADMIN_CLIENT_ID and ADMIN_CLIENT_SECRET if set; otherwise
        CLIENT_ID and CLIENT_SECRET. The client must have Client authentication
        ON and Service accounts enabled in Keycloak, plus realm-management roles.

        Returns:
            Access token for Admin API

        Raises:
            KeycloakConnectionError: If token request fails (e.g. 401 = wrong
                credentials or client not allowed for client_credentials).
        """
        now = time.time()
        if self._admin_token is not None and self._admin_token_expires_at > now + 10.0:
            return self._admin_token

        admin_id = self.admin_client_id if self.admin_client_id else self.client_id
        admin_secret = (
            self.admin_client_secret if self.admin_client_secret else self.client_secret
        )
        if not admin_secret:
            raise KeycloakConnectionError()
        data = {
            "grant_type": "client_credentials",
            "client_id": admin_id,
            "client_secret": admin_secret,
        }
        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise KeycloakConnectionError()
            expires_in = token_data.get("expires_in", 60)
            self._admin_token = access_token
            self._admin_token_expires_at = now + min(
                float(expires_in) * 0.9, _ADMIN_TOKEN_CACHE_TTL
            )
            return access_token
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to obtain admin token",
                error=str(e),
                error_type=type(e).__name__,
                status_code=e.response.status_code if e.response else None,
            )
            if e.response is not None and e.response.status_code == 401:
                raise KeycloakConnectionError() from e
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to obtain admin token",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def list_users(
        self,
        first: int = 0,
        max_: int = 20,
        search: str | None = None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        q: str | None = None,
        enabled: bool | None = None,
    ) -> RawKeycloakList:
        """List realm users with pagination and optional search/filter.

        Args:
            first: Pagination offset
            max_: Maximum number of users to return
            search: Search for username, first name, last name, or email
            username: Filter by username (exact)
            first_name: Filter by first name (Keycloak: firstName)
            last_name: Filter by last name (Keycloak: lastName)
            email: Filter by email
            q: Custom attribute filter (e.g. "phoneNumber:value mainGroup:value")
            enabled: Filter by enabled status

        Returns:
            List of user representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        params: ParamsDict = {"first": first, "max": max_}
        if search:
            params["search"] = search
        if username:
            params["username"] = username
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        if email:
            params["email"] = email
        if q:
            params["q"] = q
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        url = f"{self.admin_url}/users"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list users from Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def count_users(
        self,
        search: str | None = None,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        q: str | None = None,
        enabled: bool | None = None,
    ) -> int:
        """Return total user count with optional filters.

        Args:
            search: Search filter (same as list_users)
            username: Filter by username (exact)
            first_name: Filter by first name (Keycloak: firstName)
            last_name: Filter by last name (Keycloak: lastName)
            email: Filter by email
            q: Custom attribute filter (e.g. "phoneNumber:value mainGroup:value")
            enabled: Filter by enabled status

        Returns:
            Total number of users

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        params: QueryParamsStrDict = {}
        if search:
            params["search"] = search
        if username:
            params["username"] = username
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        if email:
            params["email"] = email
        if q:
            params["q"] = q
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        url = f"{self.admin_url}/users/count"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params or None,
            )
            response.raise_for_status()
            return int(response.json())
        except httpx.HTTPError as e:
            logger.error(
                "Failed to count users in Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def list_groups(
        self,
        first: int = 0,
        max_: int = 20,
        search: str | None = None,
    ) -> RawKeycloakList:
        """List realm groups (top-level) with pagination and optional search.

        Args:
            first: Pagination offset
            max_: Maximum number of groups to return
            search: Filter by group name

        Returns:
            List of group representation dicts (top-level only)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        params: ParamsDict = {"first": first, "max": max_}
        if search:
            params["search"] = search
        url = f"{self.admin_url}/groups"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list groups from Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def count_groups(self, search: str | None = None) -> int:
        """Return total group count (top-level) with optional search.

        Args:
            search: Filter by group name

        Returns:
            Total number of groups

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        params: QueryParamsStrDict = {}
        if search:
            params["search"] = search
        url = f"{self.admin_url}/groups/count"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params or None,
            )
            response.raise_for_status()
            data = response.json()
            # Keycloak may return {"count": N} or a number
            if isinstance(data, dict) and "count" in data:
                return int(data["count"])
            return int(data)
        except httpx.HTTPError as e:
            logger.error(
                "Failed to count groups in Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def create_group(self, body: RawKeycloakDict) -> RawKeycloakDict:
        """Create a top-level realm group.

        Sends POST to Keycloak Admin API /groups with GroupRepresentation body.
        Returns the created group representation (fetched by ID from Location).

        Args:
            body: Group representation (name required; path, description optional).
                  Keys: name (str), path (str | None), description (str | None).

        Returns:
            Created group representation dict (id, name, path, etc.)

        Raises:
            KeycloakConnectionError: If Admin API request fails
            ConflictError: If group with same name/path already exists (409)
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups"
        payload: RawKeycloakDict = {"name": body.get("name", "")}
        try:
            response = await self.client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code == 409:
                raise ConflictError(
                    message="Group with this name or path already exists",
                    details={"name": body.get("name")},
                )
            response.raise_for_status()
            location = response.headers.get("Location")
            if location:
                # Location is like .../admin/realms/{realm}/groups/{id}
                group_id = location.rstrip("/").split("/")[-1]
                if group_id and group_id != "groups":
                    return await self.get_group(group_id)
            # Fallback: find by name
            name = payload.get("name", "")
            found = await self.find_group_by_name(name)
            if found is not None:
                return found
            raise KeycloakConnectionError()
        except ConflictError:
            raise
        except httpx.HTTPError as e:
            logger.error(
                "Failed to create group in Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user(self, user_id: str) -> RawKeycloakDict:
        """Get a single user by ID.

        Args:
            user_id: Keycloak user ID

        Returns:
            User representation dict

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                raise
            logger.error(
                "Failed to get user from Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get user from Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def update_user(self, user_id: str, body: RawKeycloakDict) -> None:
        """Update a user (e.g. attributes for profile).

        Args:
            user_id: Keycloak user ID
            body: Partial user representation (e.g. {"attributes": {...}})

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}"
        try:
            response = await self.client.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to update user in Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user_groups(
        self,
        user_id: str,
        first: int = 0,
        max_: int = 100,
    ) -> RawKeycloakList:
        """Get groups the user is a member of.

        Args:
            user_id: Keycloak user ID
            first: Pagination offset
            max_: Maximum number of groups to return

        Returns:
            List of group representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/groups"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params={"first": first, "max": max_},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get user groups from Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user_realm_role_mappings(self, user_id: str) -> RawKeycloakList:
        """Get realm role mappings for a user.

        Args:
            user_id: Keycloak user ID

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/realm"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get user realm roles from Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user_composite_realm_roles(self, user_id: str) -> RawKeycloakList:
        """Get effective (composite) realm role mappings for a user.

        Args:
            user_id: Keycloak user ID

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/realm/composite"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get user composite realm roles from Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_clients(self) -> RawKeycloakList:
        """Get realm clients (for client role mappings).

        Returns:
            List of client representation dicts (id, clientId, etc.)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/clients"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params={"max": 1000},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list clients from Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_user_client_role_mappings(
        self, user_id: str, client_uuid: str
    ) -> RawKeycloakList:
        """Get client role mappings for a user.

        Args:
            user_id: Keycloak user ID
            client_uuid: Keycloak client UUID (not clientId)

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get user client roles from Keycloak",
                user_id=user_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_realm_role_by_name(self, role_name: str) -> RawKeycloakDict | None:
        """Get a realm role by name.

        Args:
            role_name: Realm role name

        Returns:
            Role representation dict or None if not found

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        encoded = quote(role_name, safe="")
        url = f"{self.admin_url}/roles/{encoded}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            logger.error(
                "Failed to get realm role by name from Keycloak",
                role_name=role_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get realm role by name from Keycloak",
                role_name=role_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def add_user_realm_role_mappings(
        self, user_id: str, roles: RawKeycloakList
    ) -> None:
        """Add realm-level role mappings to a user.

        Args:
            user_id: Keycloak user ID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/realm"
        try:
            response = await self.client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add realm role mappings in Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_user_realm_role_mappings(
        self, user_id: str, roles: RawKeycloakList
    ) -> None:
        """Remove realm-level role mappings from a user.

        Args:
            user_id: Keycloak user ID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/realm"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete realm role mappings in Keycloak",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_client_roles(self, client_uuid: str) -> RawKeycloakList:
        """List roles for a client.

        Args:
            client_uuid: Keycloak client UUID (not clientId)

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/clients/{client_uuid}/roles"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list client roles from Keycloak",
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_client_role_by_name(
        self, client_uuid: str, role_name: str
    ) -> RawKeycloakDict | None:
        """Get a client role by name.

        Args:
            client_uuid: Keycloak client UUID
            role_name: Role name

        Returns:
            Role representation dict or None if not found

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        encoded = quote(role_name, safe="")
        url = f"{self.admin_url}/clients/{client_uuid}/roles/{encoded}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            logger.error(
                "Failed to get client role by name from Keycloak",
                client_uuid=client_uuid,
                role_name=role_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get client role by name from Keycloak",
                client_uuid=client_uuid,
                role_name=role_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def add_user_client_role_mappings(
        self, user_id: str, client_uuid: str, roles: RawKeycloakList
    ) -> None:
        """Add client-level role mappings to a user.

        Args:
            user_id: Keycloak user ID
            client_uuid: Keycloak client UUID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add client role mappings in Keycloak",
                user_id=user_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_user_client_role_mappings(
        self, user_id: str, client_uuid: str, roles: RawKeycloakList
    ) -> None:
        """Remove client-level role mappings from a user.

        Args:
            user_id: Keycloak user ID
            client_uuid: Keycloak client UUID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete client role mappings in Keycloak",
                user_id=user_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_group_composite_realm_roles(self, group_id: str) -> RawKeycloakList:
        """Get effective (composite) realm role mappings for a group.

        Args:
            group_id: Keycloak group ID

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/realm/composite"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get group composite realm roles from Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_group_client_role_mappings(
        self, group_id: str, client_uuid: str
    ) -> RawKeycloakList:
        """Get client role mappings for a group.

        Args:
            group_id: Keycloak group ID
            client_uuid: Keycloak client UUID (not clientId)

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get group client roles from Keycloak",
                group_id=group_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_group(self, group_id: str) -> RawKeycloakDict:
        """Get a single group by ID.

        Args:
            group_id: Keycloak group ID

        Returns:
            Group representation dict

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                raise
            logger.error(
                "Failed to get group from Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get group from Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def update_group(self, group_id: str, body: RawKeycloakDict) -> None:
        """Update a Keycloak group.

        Args:
            group_id: Keycloak group ID.
            body: Group representation payload (may contain only changed fields).

        Raises:
            KeycloakConnectionError: If Admin API request fails.
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}"
        try:
            response = await self.client.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to update group in Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_group(self, group_id: str) -> None:
        """Delete a Keycloak group by ID.

        Args:
            group_id: Keycloak group ID.

        Raises:
            KeycloakConnectionError: If Admin API request fails.
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete group in Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def get_group_members(
        self,
        group_id: str,
        first: int = 0,
        max_: int = 100,
    ) -> RawKeycloakList:
        """Get members of a group.

        Args:
            group_id: Keycloak group ID
            first: Pagination offset
            max_: Maximum number of members to return

        Returns:
            List of user representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/members"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params={"first": first, "max": max_},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to get group members from Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """Add a user to a group.

        Args:
            user_id: Keycloak user ID
            group_id: Keycloak group ID

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/groups/{group_id}"
        try:
            response = await self.client.put(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add user to group in Keycloak",
                user_id=user_id,
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def remove_user_from_group(self, user_id: str, group_id: str) -> None:
        """Remove a user from a group.

        Args:
            user_id: Keycloak user ID
            group_id: Keycloak group ID

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/users/{user_id}/groups/{group_id}"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to remove user from group in Keycloak",
                user_id=user_id,
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def add_group_realm_role_mappings(
        self, group_id: str, roles: RawKeycloakList
    ) -> None:
        """Add realm-level role mappings to a group.

        Args:
            group_id: Keycloak group ID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/realm"
        try:
            response = await self.client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add realm role mappings to group in Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_group_realm_role_mappings(
        self, group_id: str, roles: RawKeycloakList
    ) -> None:
        """Remove realm-level role mappings from a group.

        Args:
            group_id: Keycloak group ID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/realm"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete realm role mappings from group in Keycloak",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def add_group_client_role_mappings(
        self, group_id: str, client_uuid: str, roles: RawKeycloakList
    ) -> None:
        """Add client-level role mappings to a group.

        Args:
            group_id: Keycloak group ID
            client_uuid: Keycloak client UUID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to add client role mappings to group in Keycloak",
                group_id=group_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_group_client_role_mappings(
        self, group_id: str, client_uuid: str, roles: RawKeycloakList
    ) -> None:
        """Remove client-level role mappings from a group.

        Args:
            group_id: Keycloak group ID
            client_uuid: Keycloak client UUID
            roles: List of role representation dicts (id, name)

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        if not roles:
            return
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups/{group_id}/role-mappings/clients/{client_uuid}"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=roles,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete client role mappings from group in Keycloak",
                group_id=group_id,
                client_uuid=client_uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def find_group_by_name(self, name: str) -> RawKeycloakDict | None:
        """Find a top-level or nested group by exact name match.

        Searches groups and returns the first group whose name equals the given
        name (case-sensitive). Does not search nested subgroups recursively.

        Args:
            name: Group name to find

        Returns:
            Group representation dict or None if not found

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/groups"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params={"search": name, "max": 100},
            )
            response.raise_for_status()
            groups = response.json()

            def find_in_list(glist: RawKeycloakList) -> RawKeycloakDict | None:
                for g in glist:
                    if g.get("name") == name:
                        return g
                    subs = g.get("subGroups") or []
                    found = find_in_list(subs)
                    if found is not None:
                        return found
                return None

            return find_in_list(groups)
        except httpx.HTTPError as e:
            logger.error(
                "Failed to find group by name in Keycloak",
                name=name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def list_realm_roles(
        self,
        first: int = 0,
        max_: int = 100,
        search: str | None = None,
    ) -> RawKeycloakList:
        """List realm roles.

        Args:
            first: Pagination offset
            max_: Maximum number of roles to return
            search: Optional filter by role name

        Returns:
            List of role representation dicts

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        params: ParamsDict = {"first": first, "max": max_}
        if search is not None and search.strip():
            params["search"] = search.strip()
        url = f"{self.admin_url}/roles"
        try:
            response = await self.client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list realm roles from Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def create_realm_role(self, role: RawKeycloakDict) -> RawKeycloakDict:
        """Create a realm role.

        Args:
            role: Role representation (name required, description optional)

        Returns:
            Created role is not returned by Keycloak; fetch by name. Returns input.

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        url = f"{self.admin_url}/roles"
        try:
            response = await self.client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=role,
            )
            response.raise_for_status()
            return role
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 409:
                name = role.get("name", "")
                raise ConflictError(
                    message=f"Realm role already exists: {name}",
                    details={"name": name},
                ) from e
            logger.error(
                "Failed to create realm role in Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e
        except httpx.HTTPError as e:
            logger.error(
                "Failed to create realm role in Keycloak",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def delete_realm_role_by_name(self, role_name: str) -> None:
        """Delete a realm role by name.

        Args:
            role_name: Realm role name

        Raises:
            KeycloakConnectionError: If Admin API request fails
        """
        token = await self._get_admin_token()
        encoded = quote(role_name, safe="")
        url = f"{self.admin_url}/roles/{encoded}"
        try:
            response = await self.client.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to delete realm role in Keycloak",
                role_name=role_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    def get_issuer(self) -> str:
        """Get issuer URL.

        Returns:
            Issuer URL
        """
        return self.issuer

    def get_jwks_url(self) -> str:
        """Get JWKS URL.

        Returns:
            JWKS URL
        """
        return self.jwks_url


# Global client instance
_client_instance: KeycloakClient | None = None


def get_keycloak_client() -> KeycloakClient | None:
    """Get global Keycloak client instance.

    Returns:
        Global KeycloakClient instance if Keycloak is enabled, None otherwise
    """
    global _client_instance

    # Check if Keycloak is enabled
    if not hasattr(settings, "keycloak"):
        return None

    if not getattr(settings.keycloak, "ENABLED", False):
        return None

    if _client_instance is None:
        _client_instance = KeycloakClient()
    return _client_instance
