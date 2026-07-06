"""Middleware registration for the FastAPI application."""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from config.settings import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add common security headers to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Add security headers after downstream request handling.

        Args:
            request: Incoming FastAPI request.
            call_next: Next middleware or route handler.

        Returns:
            Response with security headers attached.
        """
        response = await call_next(request)
        security_settings = settings.security

        response.headers["X-Frame-Options"] = security_settings.X_FRAME_OPTIONS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = security_settings.X_XSS_PROTECTION
        response.headers["Referrer-Policy"] = security_settings.REFERRER_POLICY
        response.headers["Cross-Origin-Opener-Policy"] = (
            security_settings.CROSS_ORIGIN_OPENER_POLICY
        )
        response.headers["Cross-Origin-Resource-Policy"] = (
            security_settings.CROSS_ORIGIN_RESOURCE_POLICY
        )

        content_security_policy = getattr(
            security_settings,
            "CONTENT_SECURITY_POLICY",
            None,
        )
        if content_security_policy:
            response.headers["Content-Security-Policy"] = content_security_policy

        permissions_policy = getattr(security_settings, "PERMISSIONS_POLICY", None)
        if permissions_policy:
            response.headers["Permissions-Policy"] = permissions_policy

        if security_settings.ENABLE_HSTS:
            hsts_value = f"max-age={security_settings.HSTS_MAX_AGE}"
            if security_settings.HSTS_INCLUDE_SUBDOMAINS:
                hsts_value += "; includeSubDomains"
            if security_settings.HSTS_PRELOAD:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with a Content-Length over the configured limit."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Validate Content-Length before processing the request body.

        Args:
            request: Incoming FastAPI request.
            call_next: Next middleware or route handler.

        Returns:
            Downstream response or a 413 error response.
        """
        max_size_bytes = settings.security.MAX_REQUEST_SIZE_MB * 1024 * 1024
        content_length = request.headers.get("content-length")

        if content_length is not None and int(content_length) > max_size_bytes:
            return ORJSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": {
                        "message": "Request body too large",
                        "type": "RequestEntityTooLargeError",
                        "details": {
                            "max_size_mb": settings.security.MAX_REQUEST_SIZE_MB,
                        },
                    }
                },
            )

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Register application middleware in the expected execution order.

    Args:
        app: FastAPI application instance.
    """
    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.ORIGINS,
        allow_credentials=settings.cors.ALLOW_CREDENTIALS,
        allow_methods=settings.cors.ALLOWED_METHODS,
        allow_headers=settings.cors.ALLOWED_HEADERS,
        expose_headers=settings.cors.EXPOSED_HEADERS,
        max_age=settings.cors.MAX_AGE,
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    if settings.ENABLE_METRICS:
        from config.metrics import PrometheusMiddleware

        app.add_middleware(PrometheusMiddleware)


__all__ = [
    "RequestSizeLimitMiddleware",
    "SecurityHeadersMiddleware",
    "register_middleware",
]
