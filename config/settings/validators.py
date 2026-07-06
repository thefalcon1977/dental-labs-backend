"""Dynaconf validators for settings validation."""

from urllib.parse import urlparse

from dynaconf import Validator


def _is_valid_http_url(value: str) -> bool:
    """Return True if value is a valid http/https URL with host."""
    if not value or not isinstance(value, str):
        return False
    value = value.strip()
    if not value:
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


# Application Settings Validators
validators = [
    # Application Settings
    Validator("SERVICE_NAME", default="microservice-fastapi-template", cast=str),
    Validator("SECRET_KEY", must_exist=True, cast=str, len_min=32),
    Validator("DEBUG", must_exist=True, cast=bool),
    Validator(
        "LOG_LEVEL",
        must_exist=True,
        cast=str,
        is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    ),
    Validator("HOST", must_exist=True, cast=str),
    Validator("PORT", must_exist=True, cast=int, gte=1, lte=65535),
    Validator("ENABLE_METRICS", must_exist=True, cast=bool),
    Validator(
        "OPENAPI_DOCS_ACCESS",
        default="public",
        cast=str,
        is_in=["disabled", "public", "developer_only"],
    ),
    Validator("DEFAULT_TIMEZONE", must_exist=True, cast=str),
    Validator("ALLOWED_HOSTS", must_exist=True, cast=list),
    # CORS Configuration (list from settings.toml, or comma-separated string from .env)
    Validator(
        "cors.ORIGINS", must_exist=True, condition=lambda v: isinstance(v, (list, str))
    ),
    Validator("cors.ALLOW_CREDENTIALS", default=True, cast=bool),
    Validator(
        "cors.ALLOWED_METHODS",
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        cast=list,
    ),
    Validator(
        "cors.ALLOWED_HEADERS",
        default=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "Origin",
            "Cache-Control",
            "Pragma",
            "X-API-Key",
            "X-System-User",
            "X-System-Secret",
        ],
        cast=list,
    ),
    Validator(
        "cors.EXPOSED_HEADERS",
        default=[
            "X-Request-ID",
            "X-Process-Time",
            "Content-Type",
            "Content-Length",
            "X-Estimated-Bytes",
        ],
        cast=list,
    ),
    Validator("cors.MAX_AGE", default=3600, cast=int, gte=0),
    # Logging Configuration (console only)
    Validator(
        "logging.SQLALCHEMY_LOG_LEVEL",
        default="WARNING",
        cast=str,
        is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    ),
    Validator(
        "logging.STARTUP_INFO_MODE",
        default="full",
        cast=str,
        is_in=["full", "minimal", "off"],
    ),
    # Keycloak Configuration (nested for consistency)
    Validator("keycloak.ENABLED", default=False, cast=bool),
    Validator(
        "keycloak.SERVER_URL", default="http://localhost:8080", cast=str, is_type_of=str
    ),
    Validator("keycloak.REALM", default="master", cast=str),
    Validator("keycloak.CLIENT_ID", default="your-client-id", cast=str),
    Validator("keycloak.CLIENT_SECRET", default="your-client-secret", cast=str),
    Validator("keycloak.ADMIN_CLIENT_ID", default=None),
    Validator("keycloak.ADMIN_CLIENT_SECRET", default=None),
    Validator("keycloak.ADMIN_USERNAME", default="admin", cast=str),
    Validator("keycloak.ADMIN_PASSWORD", default="admin", cast=str),
    Validator("keycloak.AUDIENCE", default=None),
    Validator("keycloak.AUDIENCE_VALIDATION_ENABLED", default=False, cast=bool),
    # Database Configuration (Optional)
    Validator("database.ENABLED", default=False, cast=bool),
    Validator("database.DRIVER", default="postgresql+asyncpg", cast=str),
    Validator("database.DB_FIRST", default=True, cast=bool),
    Validator("database.HOST", default="localhost", cast=str),
    Validator("database.PORT", default=5432, cast=int, gte=1, lte=65535),
    Validator("database.NAME", default="app_db", cast=str),
    Validator("database.USER", default="postgres", cast=str),
    Validator("database.PASSWORD", default="postgres", cast=str),
    Validator("database.POOL_SIZE", default=5, cast=int, gte=1),
    Validator("database.MAX_OVERFLOW", default=10, cast=int, gte=0),
    Validator("database.POOL_PRE_PING", default=True, cast=bool),
    Validator("database.POOL_RECYCLE", default=3600, cast=int, gte=1),
    Validator("database.POOL_TIMEOUT", default=30, cast=int, gte=1),
    Validator("database.ECHO", default=False, cast=bool),
    # Uvicorn Configuration
    Validator("uvicorn.WORKERS", default=1, cast=int, gte=1),
    Validator("uvicorn.WORKERS_MAX", default=4, cast=int, gte=1),
    Validator(
        "uvicorn.WORKER_CLASS", default="uvicorn.workers.UvicornWorker", cast=str
    ),
    Validator("uvicorn.TIMEOUT_KEEP_ALIVE", default=5, cast=int, gte=1),
    Validator("uvicorn.LIMIT_CONCURRENCY", default=1000, cast=int, gte=1),
    Validator("uvicorn.LIMIT_MAX_REQUESTS", default=10000, cast=int, gte=1),
    Validator("uvicorn.LIMIT_MAX_REQUESTS_JITTER", default=1000, cast=int, gte=0),
    Validator("uvicorn.BACKLOG", default=2048, cast=int, gte=1),
    # Redis Configuration (Optional)
    Validator("redis.ENABLED", default=False, cast=bool),
    Validator("redis.HOST", default="localhost", cast=str),
    Validator("redis.PORT", default=6379, cast=int, gte=1, lte=65535),
    Validator("redis.DB", default=0, cast=int, gte=0),
    Validator("redis.PASSWORD", default="", cast=str),
    Validator("redis.SSL", default=False, cast=bool),
    Validator("redis.SOCKET_TIMEOUT", default=5, cast=int, gte=1),
    Validator("redis.SOCKET_CONNECT_TIMEOUT", default=5, cast=int, gte=1),
    Validator("redis.RETRY_ON_TIMEOUT", default=True, cast=bool),
    Validator("redis.MAX_CONNECTIONS", default=50, cast=int, gte=1),
    # Auth OTP (two-step login)
    Validator("auth.OTP_ENABLED", default=False, cast=bool),
    Validator("auth.OTP_SESSION_TTL_SECONDS", default=300, cast=int, gte=60, lte=900),
    Validator("auth.OTP_MAX_ATTEMPTS", default=5, cast=int, gte=3, lte=10),
    Validator("auth.OTP_VALIDITY_SECONDS", default=120, cast=int, gte=60, lte=300),
    Validator(
        "auth.OTP_RATE_LIMIT_LOGIN_PER_MIN", default=10, cast=int, gte=1, lte=100
    ),
    Validator(
        "auth.OTP_RATE_LIMIT_VERIFY_PER_MIN", default=20, cast=int, gte=1, lte=100
    ),
    Validator("auth.OTP_RESEND_MAX_PER_SESSION", default=3, cast=int, gte=1, lte=10),
    Validator(
        "auth.OTP_RESEND_WINDOW_SECONDS", default=900, cast=int, gte=60, lte=3600
    ),
    Validator("auth.OTP_SMS_MOCK_ENABLED", default=True, cast=bool),
    Validator(
        "auth.OTP_SMS_URL",
        default="",
        cast=str,
        condition=lambda v: not v or _is_valid_http_url(str(v)),
    ),
    Validator("auth.OTP_PLATFORM_NAME", default="iTicket", cast=str),
    # Security Configuration
    Validator("security.ENABLE_HSTS", default=False, cast=bool),
    Validator("security.HSTS_MAX_AGE", default=31536000, cast=int, gte=0),
    Validator("security.HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool),
    Validator("security.HSTS_PRELOAD", default=False, cast=bool),
    Validator("security.X_FRAME_OPTIONS", default="DENY", cast=str),
    Validator("security.X_XSS_PROTECTION", default="1; mode=block", cast=str),
    Validator(
        "security.REFERRER_POLICY", default="strict-origin-when-cross-origin", cast=str
    ),
    Validator("security.CROSS_ORIGIN_OPENER_POLICY", default="same-origin", cast=str),
    Validator("security.CROSS_ORIGIN_RESOURCE_POLICY", default="same-origin", cast=str),
    Validator("security.ENABLE_RATE_LIMITING", default=True, cast=bool),
    Validator("security.RATE_LIMIT_REQUESTS_PER_MINUTE", default=60, cast=int, gte=1),
    Validator("security.MAX_REQUEST_SIZE_MB", default=10, cast=int, gte=1),
    # Metrics Authentication Configuration
    Validator("metrics.AUTH_ENABLED", default=False, cast=bool),
    Validator(
        "metrics.AUTH_METHOD",
        default="basic",
        cast=str,
        is_in=["basic", "bearer"],
    ),
    Validator("metrics.AUTH_USERNAME", default="prometheus", cast=str),
    Validator("metrics.AUTH_PASSWORD", default="changeme-in-production", cast=str),
    Validator("metrics.AUTH_BEARER_TOKEN", default="", cast=str),
]

__all__ = ["validators"]
