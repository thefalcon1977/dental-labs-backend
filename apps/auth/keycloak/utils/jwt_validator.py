"""JWT token validation and user extraction utilities."""

import time
from urllib.parse import urlparse

from jose import JWTError, jwt

from config.logging import get_logger
from config.settings import settings

from ..helpers.exceptions import (
    InvalidTokenError,
    KeycloakConnectionError,
    TokenExpiredError,
    TokenRevokedError,
)
from ..schemas.user import UserInfo, UserPermissions, UserRoles
from ..types import ClientRolesDict, JWKSDict, StringList, TokenPayloadDict
from .keycloak_client import get_keycloak_client

logger = get_logger(__name__)


def _normalize_issuer(issuer: str) -> str:
    """Normalize issuer URL to handle localhost/127.0.0.1 differences.

    Converts 127.0.0.1 to localhost in issuer URLs for consistent comparison.

    Args:
        issuer: Issuer URL string

    Returns:
        Normalized issuer URL with localhost instead of 127.0.0.1
    """
    try:
        parsed = urlparse(issuer)
        if parsed.hostname == "127.0.0.1":
            # Replace 127.0.0.1 with localhost
            normalized = issuer.replace("127.0.0.1", "localhost")
            return normalized
        return issuer
    except Exception:
        # If parsing fails, return as-is
        return issuer


class JWTValidator:
    """JWT token validator for Keycloak tokens.

    Handles token extraction, signature verification, claim validation,
    and user/role extraction.
    """

    def __init__(self) -> None:
        """Initialize JWT validator with configuration."""
        self.keycloak_client = get_keycloak_client()
        if self.keycloak_client is None:
            raise KeycloakConnectionError()
        # Normalize issuer to handle localhost/127.0.0.1 differences
        self.issuer = _normalize_issuer(self.keycloak_client.get_issuer())

        # Build list of acceptable audiences (normalized to stripped strings)
        # Token must contain at least one of these
        configured_audience = getattr(settings.keycloak, "AUDIENCE", None)
        client_id = getattr(settings.keycloak, "CLIENT_ID", None)
        # Default False: skip audience validation unless explicitly enabled (avoids env/parsing issues)
        audience_validation_enabled = getattr(
            settings.keycloak, "AUDIENCE_VALIDATION_ENABLED", False
        )

        # Coerce to bool: .env often loads as string "true"/"false"
        if isinstance(audience_validation_enabled, str):
            self._audience_validation_enabled = (
                audience_validation_enabled.strip().lower() in ("true", "1", "yes")
            )
        else:
            self._audience_validation_enabled = bool(audience_validation_enabled)

        self.acceptable_audiences: StringList = []

        def _add_audience(value: str | StringList | None) -> None:
            if value is None:
                return
            if isinstance(value, list):
                for v in value:
                    if v is not None and str(v).strip():
                        s = str(v).strip()
                        if s not in self.acceptable_audiences:
                            self.acceptable_audiences.append(s)
                return
            s = str(value).strip()
            if s and s not in self.acceptable_audiences:
                self.acceptable_audiences.append(s)

        _add_audience(configured_audience)
        _add_audience(client_id)
        # "account" is a standard Keycloak audience for account management
        if "account" not in self.acceptable_audiences:
            self.acceptable_audiences.append("account")

        # If no audiences configured, set to None to skip validation
        self.audience = (
            self.acceptable_audiences[0] if self.acceptable_audiences else None
        )
        self.algorithms = getattr(settings.keycloak, "ALGORITHMS", ["RS256"])
        self.introspection_enabled = getattr(
            settings.keycloak, "TOKEN_INTROSPECTION_ENABLED", False
        )

    def extract_token(self, authorization: str | None) -> str:
        """Extract Bearer token from Authorization header.

        Args:
            authorization: Authorization header value

        Returns:
            Extracted token string

        Raises:
            InvalidTokenError: If token is missing or malformed
        """
        if not authorization:
            logger.warning("Missing Authorization header")
            raise InvalidTokenError()

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Invalid Authorization header format")
            raise InvalidTokenError()

        token = parts[1]
        if not token:
            logger.warning("Empty token in Authorization header")
            raise InvalidTokenError()

        return token

    async def _get_public_key(self, token: str) -> JWKSDict:
        """Get public key for token verification.

        Args:
            token: JWT token (to extract kid from header)

        Returns:
            Public key dictionary

        Raises:
            KeycloakConnectionError: If unable to fetch JWKS
        """
        # Decode header to get kid (key ID)
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
        except JWTError as e:
            logger.error("Failed to decode token header", error=str(e))
            raise InvalidTokenError() from e

        if not kid:
            logger.error("Token missing kid (key ID) in header")
            raise InvalidTokenError()

        # Fetch JWKS
        try:
            jwks = await self.keycloak_client.get_jwks()
        except KeycloakConnectionError:
            raise
        except Exception as e:
            logger.error(
                "Failed to fetch JWKS",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise KeycloakConnectionError() from e

        # Find the key with matching kid
        keys = jwks.get("keys", [])
        key = None
        for k in keys:
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            logger.error("Key not found in JWKS", kid=kid)
            raise InvalidTokenError()

        # Return the key dictionary - jwt.decode will handle it
        # The jose library can decode JWTs directly with JWK keys
        return key

    async def validate_token(self, token: str) -> TokenPayloadDict:
        """Validate JWT token.

        Validates signature, expiry, issuer, audience, and not-before claims.

        Args:
            token: JWT token to validate

        Returns:
            Decoded token payload

        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token is expired
            KeycloakConnectionError: If unable to connect to Keycloak
        """
        # Track metrics
        from config.metrics.keycloak import (
            keycloak_token_validation_duration_seconds,
            keycloak_token_validations_total,
        )

        start_time = time.time()

        try:
            # Get public key
            public_key = await self._get_public_key(token)

            # Decode and verify token
            try:
                from jose import jwk

                # Construct the public key from JWK
                rsa_key = jwk.construct(public_key)
                public_key_pem = rsa_key.public_key()

                # Decode token first to get issuer for normalization without validation.
                unverified_payload = jwt.get_unverified_claims(token)
                token_issuer = unverified_payload.get("iss", "")

                # Normalize token issuer to handle localhost/127.0.0.1 differences
                normalized_token_issuer = _normalize_issuer(token_issuer)

                # Use normalized issuer for validation if it matches our expected issuer
                # Otherwise, try with original token issuer
                validation_issuer = self.issuer
                if normalized_token_issuer == self.issuer:
                    validation_issuer = normalized_token_issuer
                elif token_issuer == self.issuer:
                    validation_issuer = token_issuer
                else:
                    # Issuer doesn't match even after normalization
                    logger.warning(
                        "Issuer mismatch",
                        token_issuer=token_issuer,
                        normalized_token_issuer=normalized_token_issuer,
                        expected_issuer=self.issuer,
                    )
                    raise InvalidTokenError()

                # Decode with verification using appropriate issuer
                payload = jwt.decode(
                    token,
                    public_key_pem,
                    algorithms=self.algorithms,
                    audience=None,  # We'll validate audience manually
                    issuer=validation_issuer,
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_iss": True,
                        "verify_aud": False,  # Disable automatic audience validation
                        "verify_nbf": True,
                    },
                )

                # Manual audience validation: only run when explicitly enabled and we have
                # configured audiences. When enabled, token must contain at least one of
                # acceptable_audiences (from AUDIENCE/CLIENT_ID) or "account".
                _run_audience_check = (
                    self._audience_validation_enabled and self.acceptable_audiences
                )

                if _run_audience_check:
                    token_aud = payload.get("aud")
                    if isinstance(token_aud, str):
                        token_audiences = [str(token_aud).strip()]
                    elif isinstance(token_aud, list):
                        token_audiences = [
                            str(a).strip() for a in token_aud if a is not None
                        ]
                    else:
                        token_audiences = []
                    azp = payload.get("azp")
                    if azp and isinstance(azp, str):
                        azp_str = azp.strip()
                        if azp_str and azp_str not in token_audiences:
                            token_audiences = token_audiences + [azp_str]
                    acceptable_set = {str(a).strip() for a in self.acceptable_audiences}
                    if not any(
                        str(aud).strip() in acceptable_set for aud in token_audiences
                    ):
                        logger.warning(
                            "Invalid audience",
                            token_audience=token_aud,
                            token_audiences_normalized=token_audiences,
                            token_azp=azp,
                            expected_audiences=list(self.acceptable_audiences),
                            acceptable_set=list(acceptable_set),
                        )
                        raise InvalidTokenError()
                    logger.debug(
                        "Audience validated",
                        token_audiences=token_audiences,
                        acceptable_set=list(acceptable_set),
                    )
            except jwt.ExpiredSignatureError as e:
                logger.warning("Token expired", error=str(e))
                raise TokenExpiredError() from e
            except InvalidTokenError:
                # Re-raise InvalidTokenError from audience validation
                raise
            except JWTError as e:
                error_msg = str(e).lower()
                if "issuer" in error_msg or "iss" in error_msg:
                    logger.warning("Invalid issuer", error=str(e))
                    raise InvalidTokenError() from e
                else:
                    logger.warning("Token validation failed", error=str(e))
                    raise InvalidTokenError() from e

            # Optional: Check token introspection if enabled
            if self.introspection_enabled:
                try:
                    introspection = await self.keycloak_client.introspect_token(token)
                    if not introspection.get("active", False):
                        logger.warning("Token is not active (revoked)")
                        raise TokenRevokedError()
                except KeycloakConnectionError:
                    # If introspection fails, log but don't fail validation
                    # (token might still be valid, just introspection unavailable)
                    logger.warning(
                        "Token introspection failed, continuing with validation"
                    )

            logger.debug("Token validated successfully", sub=payload.get("sub"))

            # Track metrics
            duration = time.time() - start_time
            keycloak_token_validations_total.labels(status="success").inc()
            keycloak_token_validation_duration_seconds.observe(duration)

            return payload

        except (InvalidTokenError, TokenExpiredError, KeycloakConnectionError) as e:
            # Track error metrics
            duration = time.time() - start_time
            if isinstance(e, TokenExpiredError):
                keycloak_token_validations_total.labels(status="expired").inc()
            else:
                keycloak_token_validations_total.labels(status="error").inc()
            keycloak_token_validation_duration_seconds.observe(duration)
            raise
        except Exception as e:
            # Track error metrics
            duration = time.time() - start_time
            keycloak_token_validations_total.labels(status="error").inc()
            keycloak_token_validation_duration_seconds.observe(duration)
            logger.error(
                "Unexpected error during token validation",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise InvalidTokenError() from e

    def get_user_from_token(self, payload: TokenPayloadDict) -> UserInfo:
        """Extract user information from validated token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            UserInfo object with user information
        """
        # Extract basic user info
        user_id = payload.get("sub", "")
        username = payload.get("preferred_username") or payload.get("username", "")
        email = payload.get("email")
        first_name = payload.get("given_name")
        last_name = payload.get("family_name")
        full_name = payload.get("name")
        client_id = payload.get("azp") or payload.get("aud")
        realm = (
            payload.get("iss", "").split("/realms/")[-1]
            if "/realms/" in payload.get("iss", "")
            else None
        )

        # Extract roles
        roles = self.get_roles_from_token(payload)

        # Extract permissions
        permissions = self.get_permissions_from_token(payload)

        # Extract groups
        groups = self.get_groups_from_token(payload)

        # Get all claims for additional info
        claims = {k: v for k, v in payload.items()}

        user_info = UserInfo(
            id=user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            roles=roles,
            permissions=permissions,
            groups=groups,
            client_id=client_id,
            realm=realm,
            claims=claims,
        )

        logger.debug(
            "User info extracted from token",
            user_id=user_id,
            username=username,
            roles_count=len(roles.realm_roles)
            + sum(len(r) for r in roles.client_roles.values()),
        )

        return user_info

    def get_roles_from_token(self, payload: TokenPayloadDict) -> UserRoles:
        """Extract roles from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            UserRoles object with realm and client roles
        """
        realm_roles: StringList = []
        client_roles: ClientRolesDict = {}

        # Extract realm roles
        realm_access = payload.get("realm_access", {})
        if isinstance(realm_access, dict):
            realm_roles = realm_access.get("roles", [])

        # Extract client roles
        resource_access = payload.get("resource_access", {})
        if isinstance(resource_access, dict):
            for client_id, access_info in resource_access.items():
                if isinstance(access_info, dict):
                    roles = access_info.get("roles", [])
                    if roles:
                        client_roles[client_id] = roles

        return UserRoles(
            realm_roles=realm_roles,
            client_roles=client_roles,
        )

    def get_permissions_from_token(self, payload: TokenPayloadDict) -> UserPermissions:
        """Extract permissions from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            UserPermissions object with permissions
        """
        permissions: StringList = []

        # Extract permissions from authorization claim (if present)
        authorization = payload.get("authorization", {})
        if isinstance(authorization, dict):
            permissions_list = authorization.get("permissions", [])
            if isinstance(permissions_list, list):
                # Permissions can be strings or objects with 'rsname' field
                for perm in permissions_list:
                    if isinstance(perm, str):
                        permissions.append(perm)
                    elif isinstance(perm, dict) and "rsname" in perm:
                        permissions.append(perm["rsname"])

        # Also check for scope claim
        scope = payload.get("scope", "")
        if scope:
            permissions.extend(scope.split())

        return UserPermissions(permissions=list(set(permissions)))

    def get_groups_from_token(self, payload: TokenPayloadDict) -> StringList:
        """Extract groups from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            List of group names
        """
        groups: StringList = []

        # Extract groups from groups claim
        token_groups = payload.get("groups", [])
        if isinstance(token_groups, list):
            # Groups can be in format "/group-name" or "group-name"
            # Normalize by removing leading slashes
            groups = [
                group.lstrip("/") if isinstance(group, str) else str(group)
                for group in token_groups
            ]
        elif isinstance(token_groups, str):
            groups = [token_groups.lstrip("/")]

        return groups


# Global validator instance
_validator_instance: JWTValidator | None = None


def get_jwt_validator() -> JWTValidator:
    """Get global JWT validator instance.

    Returns:
        Global JWTValidator instance
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = JWTValidator()
    return _validator_instance
