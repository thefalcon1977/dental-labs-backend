"""Local JWT token creation, validation, and user extraction utilities."""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, TypeAlias

from config.logging import get_logger
from config.settings import settings

from ..helpers.exceptions import InvalidTokenError, TokenExpiredError
from ..schemas.user import UserInfo
from ..types import StringList, TokenPayloadDict

JsonDict: TypeAlias = dict[str, Any]

logger = get_logger(__name__)


def _base64url_encode(value: bytes) -> str:
    """Encode bytes using unpadded base64url encoding.

    Args:
        value: Raw bytes to encode.

    Returns:
        Unpadded base64url string.
    """
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    """Decode an unpadded base64url string.

    Args:
        value: Base64url string to decode.

    Returns:
        Decoded bytes.
    """
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _json_dumps(value: JsonDict) -> bytes:
    """Serialize a JSON object for JWT signing.

    Args:
        value: JSON dictionary to serialize.

    Returns:
        UTF-8 encoded canonical JSON bytes.
    """
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _string_list(value: object) -> StringList:
    """Normalize token list claims into strings.

    Args:
        value: Raw claim value.

    Returns:
        List of string values.
    """
    if isinstance(value, str):
        return [item for item in value.split() if item]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


class JWTValidator:
    """JWT validator for locally signed access tokens."""

    def __init__(self) -> None:
        """Initialize JWT validator with local auth settings."""
        self.secret_key = settings.SECRET_KEY
        self.algorithm = getattr(settings.auth, "ALGORITHM", "HS256")
        self.issuer = getattr(settings.auth, "ISSUER", settings.SERVICE_NAME)
        self.audience = getattr(settings.auth, "AUDIENCE", None)
        self.access_token_expire_minutes = getattr(
            settings.auth,
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            30,
        )

        if self.algorithm != "HS256":
            raise InvalidTokenError("Unsupported token algorithm")

    def extract_token(self, authorization: str | None) -> str:
        """Extract a bearer token from an Authorization header.

        Args:
            authorization: Authorization header value.

        Returns:
            Extracted token string.

        Raises:
            InvalidTokenError: If token is missing or malformed.
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

    def create_access_token(
        self,
        subject: str,
        extra_claims: TokenPayloadDict | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a locally signed access token.

        Args:
            subject: User identifier to store in the `sub` claim.
            extra_claims: Additional non-sensitive claims to include.
            expires_delta: Optional custom expiration duration.

        Returns:
            Signed JWT access token.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )

        payload: JsonDict = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
        }
        if self.audience:
            payload["aud"] = self.audience
        if extra_claims:
            payload.update(extra_claims)
            payload["sub"] = subject
            payload["exp"] = int(expires_at.timestamp())
            payload["iss"] = self.issuer

        header = {"alg": self.algorithm, "typ": "JWT"}
        signing_input = (
            f"{_base64url_encode(_json_dumps(header))}."
            f"{_base64url_encode(_json_dumps(payload))}"
        )
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()

        return f"{signing_input}.{_base64url_encode(signature)}"

    async def validate_token(self, token: str) -> TokenPayloadDict:
        """Validate a locally signed JWT token.

        Args:
            token: JWT token to validate.

        Returns:
            Decoded token payload.

        Raises:
            InvalidTokenError: If token is invalid.
            TokenExpiredError: If token is expired.
        """
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
        except ValueError as exc:
            logger.warning("Malformed JWT token")
            raise InvalidTokenError() from exc

        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_signature = _base64url_decode(signature_segment)
        if not hmac.compare_digest(expected_signature, actual_signature):
            logger.warning("JWT signature validation failed")
            raise InvalidTokenError()

        try:
            header = json.loads(_base64url_decode(header_segment))
            payload = json.loads(_base64url_decode(payload_segment))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("JWT payload decode failed", error=str(exc))
            raise InvalidTokenError() from exc

        if not isinstance(header, dict) or header.get("alg") != self.algorithm:
            logger.warning("Invalid JWT algorithm")
            raise InvalidTokenError()
        if not isinstance(payload, dict):
            logger.warning("Invalid JWT payload type")
            raise InvalidTokenError()

        now = int(time.time())
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int):
            logger.warning("JWT missing exp claim")
            raise InvalidTokenError()
        if expires_at < now:
            logger.warning("JWT token expired")
            raise TokenExpiredError()

        not_before = payload.get("nbf")
        if isinstance(not_before, int) and not_before > now:
            logger.warning("JWT token not valid yet")
            raise InvalidTokenError()

        if payload.get("iss") != self.issuer:
            logger.warning("JWT issuer mismatch")
            raise InvalidTokenError()

        if self.audience and payload.get("aud") != self.audience:
            logger.warning("JWT audience mismatch")
            raise InvalidTokenError()

        if not payload.get("sub"):
            logger.warning("JWT missing subject")
            raise InvalidTokenError()

        return payload

    def get_user_from_token(self, payload: TokenPayloadDict) -> UserInfo:
        """Extract authenticated user information from token payload.

        Args:
            payload: Decoded JWT payload.

        Returns:
            UserInfo object with token user information.
        """
        issued_at = payload.get("iat")
        created_at = datetime.now(timezone.utc)
        if isinstance(issued_at, int):
            created_at = datetime.fromtimestamp(issued_at, tz=timezone.utc)

        user_info = UserInfo(
            id=str(payload["sub"]),
            username=str(payload.get("username") or payload["sub"]),
            email=str(payload.get("email") or f"{payload['sub']}@local.invalid"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            is_active=bool(payload.get("is_active", True)),
            is_verified=bool(payload.get("is_verified", False)),
            is_superuser=bool(payload.get("is_superuser", False)),
            created_at=created_at,
            updated_at=None,
            roles=self.get_roles_from_token(payload),
            permissions=self.get_permissions_from_token(payload),
            groups=self.get_groups_from_token(payload),
        )

        logger.debug(
            "User info extracted from local token",
            user_id=user_info.id,
            username=user_info.username,
            roles_count=len(user_info.roles),
        )
        return user_info

    def get_roles_from_token(self, payload: TokenPayloadDict) -> StringList:
        """Extract role names from token payload.

        Args:
            payload: Decoded JWT payload.

        Returns:
            List of role names.
        """
        return _string_list(payload.get("roles", []))

    def get_permissions_from_token(self, payload: TokenPayloadDict) -> StringList:
        """Extract permission names from token payload.

        Args:
            payload: Decoded JWT payload.

        Returns:
            List of permission names.
        """
        permissions = _string_list(payload.get("permissions", []))
        scopes = _string_list(payload.get("scope", []))
        return sorted(set(permissions + scopes))

    def get_groups_from_token(self, payload: TokenPayloadDict) -> StringList:
        """Extract group names from token payload.

        Args:
            payload: Decoded JWT payload.

        Returns:
            List of group names.
        """
        return _string_list(payload.get("groups", []))


_validator_instance: JWTValidator | None = None


def get_jwt_validator() -> JWTValidator:
    """Get the process-local JWT validator instance.

    Returns:
        JWT validator instance.
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = JWTValidator()
    return _validator_instance


__all__ = [
    "JWTValidator",
    "get_jwt_validator",
]
