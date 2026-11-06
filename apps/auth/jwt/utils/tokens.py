"""Issue and validate locally signed JWTs.

Access-token claims follow Keycloak's layout (``preferred_username``,
``realm_access.roles``, ``groups``) plus a ``permissions`` claim, so both auth
modes produce the same ``UserInfo``.
"""

import time
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError, jwt

from apps.auth.keycloak.helpers.exceptions import InvalidTokenError, TokenExpiredError
from apps.auth.keycloak.schemas.user import UserInfo, UserPermissions, UserRoles
from config.settings import settings

from ..models import LocalUser
from ..types import IssuedToken, TokenClaimsDict, UserAccess

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
BEARER_PREFIX = "bearer "


def _secret_key() -> str:
    """Return the signing key (``auth.JWT_SECRET_KEY`` or ``SECRET_KEY``).

    Returns:
        HMAC signing secret.
    """
    return str(getattr(settings.auth, "JWT_SECRET_KEY", None) or settings.SECRET_KEY)


def _algorithm() -> str:
    """Return the configured signing algorithm.

    Returns:
        JWS algorithm name, e.g. ``HS256``.
    """
    return str(settings.auth.JWT_ALGORITHM)


def _issuer() -> str:
    """Return the ``iss`` claim value.

    Returns:
        Issuer string.
    """
    return str(settings.auth.JWT_ISSUER)


def access_token_ttl_seconds() -> int:
    """Return the access token lifetime.

    Returns:
        Lifetime in seconds.
    """
    return int(settings.auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES) * 60


def refresh_token_ttl_seconds() -> int:
    """Return the refresh token lifetime.

    Returns:
        Lifetime in seconds.
    """
    return int(settings.auth.JWT_REFRESH_TOKEN_EXPIRE_DAYS) * 86400


def _encode(claims: TokenClaimsDict, token_type: str, ttl: int) -> IssuedToken:
    """Sign a token with standard claims added.

    Args:
        claims: Provider-specific claims.
        token_type: ``access`` or ``refresh``.
        ttl: Lifetime in seconds.

    Returns:
        Tuple of (encoded token, lifetime in seconds).
    """
    now = int(time.time())
    payload = {
        **claims,
        "iss": _issuer(),
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        "jti": str(uuid4()),
        "typ": token_type,
    }
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm()), ttl


def create_access_token(user: LocalUser, access: UserAccess) -> IssuedToken:
    """Issue an access token carrying identity, roles, groups, and permissions.

    Access changes made by an admin show up in the next token issued
    (login or refresh), i.e. within ``JWT_ACCESS_TOKEN_EXPIRE_MINUTES``.

    Args:
        user: Authenticated local user.
        access: The user's effective access.

    Returns:
        Tuple of (access token, lifetime in seconds).
    """
    full_name = " ".join(p for p in (user.first_name, user.last_name) if p) or None
    claims: TokenClaimsDict = {
        "sub": user.id,
        "preferred_username": user.username,
        "email": user.email,
        "given_name": user.first_name,
        "family_name": user.last_name,
        "name": full_name,
        "realm_access": {"roles": access.roles},
        "groups": access.groups,
        "permissions": access.permissions,
    }
    return _encode(claims, ACCESS_TOKEN_TYPE, access_token_ttl_seconds())


def create_refresh_token(user: LocalUser) -> IssuedToken:
    """Issue a refresh token for the user.

    Args:
        user: Authenticated local user.

    Returns:
        Tuple of (refresh token, lifetime in seconds).
    """
    return _encode({"sub": user.id}, REFRESH_TOKEN_TYPE, refresh_token_ttl_seconds())


def decode_token(token: str, expected_type: str) -> TokenClaimsDict:
    """Verify signature, expiry, issuer, and token type.

    Args:
        token: Encoded JWT.
        expected_type: ``access`` or ``refresh``.

    Returns:
        Verified claims.

    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token is malformed, tampered, or the wrong type.
    """
    try:
        claims = jwt.decode(
            token,
            _secret_key(),
            algorithms=[_algorithm()],
            issuer=_issuer(),
            options={"require_exp": True, "require_sub": True, "verify_aud": False},
        )
    except ExpiredSignatureError as e:
        raise TokenExpiredError() from e
    except JWTError as e:
        raise InvalidTokenError() from e

    if claims.get("typ") != expected_type:
        raise InvalidTokenError()
    return claims


def extract_bearer_token(authorization: str | None) -> str:
    """Extract the token from an ``Authorization: Bearer`` header.

    Args:
        authorization: Raw header value.

    Returns:
        Token string.

    Raises:
        InvalidTokenError: If the header is missing or not a bearer token.
    """
    if not authorization or not authorization.lower().startswith(BEARER_PREFIX):
        raise InvalidTokenError("Missing or invalid Authorization header.")
    token = authorization[len(BEARER_PREFIX) :].strip()
    if not token:
        raise InvalidTokenError("Missing or invalid Authorization header.")
    return token


def user_info_from_claims(claims: TokenClaimsDict) -> UserInfo:
    """Build ``UserInfo`` from verified access-token claims.

    Args:
        claims: Claims returned by ``decode_token``.

    Returns:
        User information in the same shape as Keycloak mode.
    """
    roles = (claims.get("realm_access") or {}).get("roles") or []
    return UserInfo(
        id=claims["sub"],
        username=claims.get("preferred_username") or claims["sub"],
        email=claims.get("email"),
        first_name=claims.get("given_name"),
        last_name=claims.get("family_name"),
        full_name=claims.get("name"),
        roles=UserRoles(realm_roles=list(roles), client_roles={}),
        permissions=UserPermissions(permissions=list(claims.get("permissions") or [])),
        groups=list(claims.get("groups") or []),
        client_id=None,
        realm=None,
        claims={"iss": claims.get("iss"), "jti": claims.get("jti")},
    )
