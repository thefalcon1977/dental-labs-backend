"""Login endpoint for user authentication (including OTP two-step flow)."""

from fastapi import APIRouter, Depends, status

from apps.common.openapi_responses import (
    RESP_401,
    RESP_403,
    RESP_422,
    RESP_429,
    RESP_500,
    RESP_503,
)
from apps.core.exceptions import UnauthorizedError
from config.logging import get_logger

from ..dependencies.redis import get_redis
from ..helpers.config import is_sso_enabled
from ..helpers.exceptions import (
    AuthDisabledError,
    KeycloakConnectionError,
    OtpWindowNotExpiredError,
)
from ..schemas.token import (
    LoginOtpRequiredResponse,
    LoginRequest,
    LoginResponse,
    ResendOtpRequest,
    ResendOtpResponse,
    VerifyOtpRequest,
)
from ..schemas.user import UserInfo
from ..services import auth_service, otp_login_service
from ..utils.jwt_validator import get_jwt_validator

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


async def _decode_user_from_access_token(access_token: str) -> UserInfo | None:
    """Decode Keycloak access token and return user info for the login response.

    Validates the token and extracts user information. Returns None on any failure
    so the login response can still return tokens without decoded info.

    Args:
        access_token: Keycloak access token string.

    Returns:
        UserInfo if token is valid, None otherwise.
    """
    if not access_token:
        return None
    try:
        validator = get_jwt_validator()
        payload = await validator.validate_token(access_token)
        return validator.get_user_from_token(payload)
    except Exception as e:
        logger.debug(
            "Could not decode Keycloak token for login response user info",
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


@router.post(
    "/login",
    response_model=LoginResponse | LoginOtpRequiredResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description=(
        "Authenticate with username and password. "
        "Uses Keycloak SSO when authentication is enabled. "
        "When OTP is enabled: returns session_id and message (no tokens); complete login via POST /auth/login/verify-otp. "
        "Another OTP cannot be requested until the previous one's validity window (e.g. 2 minutes) has expired (429 with retry_after_seconds). "
        "When OTP is disabled: returns access and refresh tokens plus decoded SSO user info immediately. "
        "Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "Login successful (tokens or OTP required)"},
        401: RESP_401,
        422: RESP_422,
        429: RESP_429,
        500: RESP_500,
        503: RESP_503,
    },
)
async def login(
    request_body: LoginRequest,
    redis=Depends(get_redis),
) -> LoginResponse | LoginOtpRequiredResponse:
    """Login user endpoint.

    When OTP is enabled: validates credentials with Keycloak, creates OTP session,
    sends OTP (mock or SMS), returns session_id and expires_in (no tokens).
    When OTP is disabled: returns tokens as before.

    Args:
        request_body: Login request with username and password
        redis: Redis client from app state (optional)

    Returns:
        LoginResponse (tokens) or LoginOtpRequiredResponse (session_id) when OTP required

    Raises:
        UnauthorizedError: If credentials are invalid
        KeycloakConnectionError: If Keycloak unavailable
        RedisUnavailableError: If OTP enabled and Redis unavailable
    """
    if not is_sso_enabled():
        raise AuthDisabledError()

    logger.debug("Login attempt", username=request_body.username)
    if otp_login_service._otp_enabled():
        try:
            result = await otp_login_service.login_with_otp(
                username=request_body.username,
                password=request_body.password,
                redis=redis,
            )
            return LoginOtpRequiredResponse(
                session_id=result["session_id"],
                message=result["message"],
                expires_in=result["expires_in"],
                dev_otp_code=result.get("dev_otp_code"),
            )
        except UnauthorizedError:
            raise
        except KeycloakConnectionError:
            raise
        except OtpWindowNotExpiredError:
            raise
        except Exception as e:
            logger.error(
                "Failed to login user (OTP flow)",
                error=str(e),
                error_type=type(e).__name__,
                username=request_body.username,
            )
            raise
    try:
        token_data = await auth_service.login_user(
            username=request_body.username, password=request_body.password
        )
        user = await _decode_user_from_access_token(token_data.get("access_token", ""))
        response = LoginResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_in=token_data.get("expires_in", 300),
            token_type=token_data.get("token_type", "Bearer"),
            user=user,
        )
        logger.info("User logged in successfully", username=request_body.username)
        return response
    except UnauthorizedError:
        raise
    except KeycloakConnectionError:
        raise
    except Exception as e:
        logger.error(
            "Failed to login user",
            error=str(e),
            error_type=type(e).__name__,
            username=request_body.username,
        )
        raise


@router.post(
    "/otp/verify",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and get tokens",
    description=(
        "Step 2 of OTP login: submit session_id and OTP code from Step 1. "
        "Returns access and refresh tokens plus decoded SSO user info (id, username, roles, etc.) on success; invalidates session (one-time use). "
        "Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "OTP verified; tokens returned"},
        401: RESP_401,
        403: RESP_403,
        422: RESP_422,
        503: RESP_503,
    },
)
async def verify_otp(
    request_body: VerifyOtpRequest,
    redis=Depends(get_redis),
) -> LoginResponse:
    """Verify OTP and return tokens.

    Args:
        request_body: Session id from login and OTP code
        redis: Redis client from app state

    Returns:
        Login response with access token, refresh token, expiration info

    Raises:
        OtpSessionInvalidError: Invalid or expired session or wrong OTP (401)
        OtpSessionLockedError: Too many failed attempts (403)
        RedisUnavailableError: Redis unavailable (503)
    """
    token_data = await otp_login_service.verify_otp(
        session_id=request_body.session_id,
        code=request_body.code,
        redis=redis,
    )
    user = await _decode_user_from_access_token(token_data.get("access_token", ""))
    return LoginResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", ""),
        expires_in=token_data.get("expires_in", 300),
        token_type=token_data.get("token_type", "Bearer"),
        user=user,
    )


@router.post(
    "/otp/resend",
    response_model=ResendOtpResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend OTP",
    description=(
        "Resend OTP for the same session from Step 1 (login). "
        "A new OTP can only be requested after the previous one's validity window (e.g. 2 minutes) has expired (429 with retry_after_seconds). "
        "Returns new message and expires_in; dev_otp_code when OTP_SMS_MOCK_ENABLED is true. "
        "Time: O(1) · Space: O(1)"
    ),
    responses={
        200: {"description": "OTP resent"},
        401: RESP_401,
        429: RESP_429,
        503: RESP_503,
    },
)
async def resend_otp(
    request_body: ResendOtpRequest,
    redis=Depends(get_redis),
) -> ResendOtpResponse:
    """Resend OTP for an existing OTP session.

    Args:
        request_body: Contains session_id from login response.
        redis: Redis client from app state.

    Returns:
        ResendOtpResponse with message, expires_in; dev_otp_code when OTP_SMS_MOCK_ENABLED is true.

    Raises:
        OtpSessionInvalidError: Invalid or expired session (401).
        OtpWindowNotExpiredError: Previous OTP still valid; retry after retry_after_seconds (429).
        RedisUnavailableError: Redis unavailable (503).
    """
    result = await otp_login_service.resend_otp(
        session_id=request_body.session_id,
        redis=redis,
    )
    return ResendOtpResponse(
        message=result["message"],
        expires_in=result["expires_in"],
        dev_otp_code=result.get("dev_otp_code"),
    )
