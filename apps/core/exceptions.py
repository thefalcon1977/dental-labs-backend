"""Hierarchical exception handlers for the application.

This module provides a centralized exception handling system for FastAPI
applications. It includes:

- Base exception class for all API errors
- Standard exception types (NotFound, Validation, Unauthorized, etc.)
- Exception handlers that convert exceptions to consistent JSON responses
- Automatic registration of handlers with FastAPI app

All exceptions follow a consistent structure with message, status code,
and optional details. Exception handlers automatically convert exceptions
to ORJSONResponse format for consistent API error responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from apps.core.types import ExceptionDetailsDict
from config.logging import get_logger, get_request_id

try:  # asyncpg is optional; guard import for safety
    from asyncpg import InvalidPasswordError, PostgresError
except Exception:  # pragma: no cover - asyncpg may not be installed in some envs
    InvalidPasswordError = None  # type: ignore[assignment]
    PostgresError = None  # type: ignore[assignment]

logger = get_logger(__name__)


class BaseAPIException(Exception):
    """Base exception for API errors.

    All application-specific exceptions should inherit from this class to
    ensure consistent error handling and response formatting.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for the error
        details: Additional error context (dict with structured data)

    Example:
        ```python
        class CustomError(BaseAPIException):
            def __init__(self, resource_id: str):
                super().__init__(
                    message=f"Resource {resource_id} not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    details={"resource_id": resource_id},
                )
        ```
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: ExceptionDetailsDict | None = None,
    ) -> None:
        """Initialize base API exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(BaseAPIException):
    """Resource not found exception.

    Raised when a requested resource cannot be found in the system.
    Automatically sets HTTP status code to 404.

    Example:
        ```python
        if not user:
            raise NotFoundError(resource="User", identifier=user_id)
        ```
    """

    def __init__(self, resource: str, identifier: str | None = None) -> None:
        """Initialize not found error.

        Args:
            resource: Type of resource that was not found (e.g., "User", "Order")
            identifier: Optional identifier that was searched for
        """
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class ValidationError(BaseAPIException):
    """Validation error exception.

    Raised when input data fails validation rules. Automatically sets
    HTTP status code to 422 (Unprocessable Entity).

    Example:
        ```python
        if age < 18:
            raise ValidationError(
                message="User must be at least 18 years old",
                details={"age": age, "minimum": 18},
            )
        ```
    """

    def __init__(
        self, message: str, details: ExceptionDetailsDict | None = None
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable validation error message
            details: Optional dictionary with validation error details
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {},
        )


class UnauthorizedError(BaseAPIException):
    """Unauthorized access exception.

    Raised when authentication is required but not provided or invalid.
    Automatically sets HTTP status code to 401 (Unauthorized).

    Example:
        ```python
        if not token:
            raise UnauthorizedError("Authentication token required")
        ```
    """

    def __init__(
        self, message: str = "Unauthorized", details: ExceptionDetailsDict | None = None
    ) -> None:
        """Initialize unauthorized error.

        Args:
            message: Error message (default: "Unauthorized")
            details: Optional dictionary with additional error context
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details or {},
        )


class ForbiddenError(BaseAPIException):
    """Forbidden access exception.

    Raised when the user is authenticated but lacks permission to access
    the requested resource. Automatically sets HTTP status code to 403 (Forbidden).

    Example:
        ```python
        if not user.has_permission("admin"):
            raise ForbiddenError("Admin access required")
        ```
    """

    def __init__(self, message: str = "Forbidden") -> None:
        """Initialize forbidden error.

        Args:
            message: Error message (default: "Forbidden")
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictError(BaseAPIException):
    """Resource conflict exception.

    Raised when a resource operation conflicts with existing state (e.g.,
    duplicate email, concurrent modification). Automatically sets HTTP
    status code to 409 (Conflict).

    Example:
        ```python
        if user_exists:
            raise ConflictError(
                message="User with this email already exists",
                details={"email": email},
            )
        ```
    """

    def __init__(
        self, message: str, details: ExceptionDetailsDict | None = None
    ) -> None:
        """Initialize conflict error.

        Args:
            message: Human-readable conflict error message
            details: Optional dictionary with conflict details
        """
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details or {},
        )


def _error_response(
    status_code: int,
    message: str,
    error_type: str,
    details: ExceptionDetailsDict,
) -> ORJSONResponse:
    """Build error response with request_id for ops correlation.

    Adds X-Request-ID header and request_id in details when available
    so clients and ops can trace the request in logs.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_type: Exception class name
        details: Error details dict (may be mutated to add request_id)

    Returns:
        ORJSONResponse with headers and body set for correlation
    """
    request_id = get_request_id()
    if request_id:
        details = {**details, "request_id": request_id}
    response = ORJSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "details": details,
            }
        },
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


async def base_api_exception_handler(
    request: Request,
    exc: BaseAPIException,
) -> ORJSONResponse:
    """Handle BaseAPIException and convert to JSON response.

    Converts any BaseAPIException (or subclass) to a consistent JSON error
    response format with message, type, and details. Includes request_id
    for ops correlation when available.

    For UnauthorizedError with Basic Auth method, adds WWW-Authenticate header
    to trigger browser Basic Auth dialog.

    Args:
        request: FastAPI request object
        exc: BaseAPIException instance

    Returns:
        ORJSONResponse with error details and appropriate status code
    """
    # Log handled API exceptions for observability (warning for 4xx, error for 5xx)
    request_id = get_request_id()
    log_level = logger.warning
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        log_level = logger.error

    # Extract app name from path (e.g., "/camunda/tickets" -> "camunda")
    app_name = None
    path_parts = request.url.path.strip("/").split("/")
    if path_parts and path_parts[0]:
        app_name = path_parts[0]

    log_level(
        "Handled API exception",
        error_type=exc.__class__.__name__,
        status_code=exc.status_code,
        message=exc.message,
        app=app_name,
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        details=exc.details,
        query_params=dict(request.query_params) if request.query_params else None,
    )

    response = _error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_type=exc.__class__.__name__,
        details=exc.details,
    )

    # Add WWW-Authenticate header for Basic Auth to trigger browser login dialog
    if (
        isinstance(exc, UnauthorizedError)
        and exc.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        auth_method = exc.details.get("method", "")
        if auth_method == "basic":
            response.headers["WWW-Authenticate"] = 'Basic realm="Metrics"'
        elif auth_method == "bearer":
            response.headers["WWW-Authenticate"] = 'Bearer realm="Metrics"'

    return response


async def validation_error_handler(
    request: Request,
    exc: PydanticValidationError,
) -> ORJSONResponse:
    """Handle Pydantic ValidationError and convert to JSON response.

    Formats Pydantic validation errors into a consistent structure with
    field-level error details.

    Args:
        request: FastAPI request object
        exc: Pydantic ValidationError instance

    Returns:
        ORJSONResponse with validation error details (status 422)
    """
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    # Log validation errors as warnings with request context
    request_id = get_request_id()
    logger.warning(
        "Request validation failed",
        error_type="ValidationError",
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        errors=errors,
        query_params=dict(request.query_params) if request.query_params else None,
    )

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        error_type="ValidationError",
        details={"errors": errors},
    )


async def sqlalchemy_error_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> ORJSONResponse:
    """Handle SQLAlchemy errors and convert to JSON response.

    Handles database-related errors from SQLAlchemy. Always returns generic
    error messages to users for security. Detailed error information including
    SQL queries and database type is logged server-side only.

    Args:
        request: FastAPI request object
        exc: SQLAlchemyError instance

    Returns:
        ORJSONResponse with generic database error message (status 500)
    """
    request_id = get_request_id()
    # Log detailed error server-side (includes SQL queries, stack traces, etc.)
    logger.exception(
        "Database error occurred",
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        query_params=dict(request.query_params) if request.query_params else None,
    )

    # Always return generic error message to users (never expose SQL details)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error occurred",
        error_type="DatabaseError",
        details={},
    )


async def postgres_error_handler(
    request: Request,
    exc: PostgresError,  # type: ignore[type-arg]
) -> ORJSONResponse:
    """Handle low-level PostgreSQL asyncpg errors securely.

    This specifically guards against leaking sensitive connection details
    (such as usernames or password hints) that may appear in asyncpg error
    messages, e.g. ``InvalidPasswordError``.

    Args:
        request: FastAPI request object
        exc: asyncpg PostgresError instance

    Returns:
        ORJSONResponse with a generic database error message
    """
    request_id = get_request_id()
    # Avoid logging full error messages that might include credentials or hints.
    if InvalidPasswordError is not None and isinstance(exc, InvalidPasswordError):
        logger.error(
            "Database authentication failed",
            error_type=exc.__class__.__name__,
            path=request.url.path,
            method=request.method,
            request_id=request_id,
        )
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Database connection error",
            error_type="DatabaseAuthenticationError",
            details={},
        )

    logger.exception(
        "PostgreSQL driver error occurred",
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        query_params=dict(request.query_params) if request.query_params else None,
    )

    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error occurred",
        error_type="DatabaseError",
        details={},
    )


async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """Handle general exceptions and convert to JSON response.

    Catches all unhandled exceptions and converts them to error responses.
    Always returns generic error messages to users for security. Detailed
    error information including stack traces is logged server-side only.

    Args:
        request: FastAPI request object
        exc: Exception instance

    Returns:
        ORJSONResponse with generic error message (status 500)
    """
    request_id = get_request_id()
    # Log detailed error server-side (includes stack traces, etc.)
    logger.exception(
        "Unhandled exception occurred",
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        query_params=dict(request.query_params) if request.query_params else None,
    )

    # Always return generic error message to users (never expose internal details)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        error_type="InternalServerError",
        details={},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app.

    Registers exception handlers in order of specificity (most specific first):
    1. BaseAPIException - Custom API exceptions
    2. PydanticValidationError - Request validation errors
    3. PostgresError - Low-level asyncpg/PostgreSQL driver errors
    4. SQLAlchemyError - SQLAlchemy ORM/database errors
    5. Exception - General catch-all for unhandled exceptions

    Args:
        app: FastAPI application instance to register handlers with
    """
    # Register in order of specificity (most specific first)
    app.add_exception_handler(BaseAPIException, base_api_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_error_handler)

    # Only register asyncpg/Postgres handler when the dependency is available.
    if PostgresError is not None:
        app.add_exception_handler(PostgresError, postgres_error_handler)  # type: ignore[arg-type]

    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
