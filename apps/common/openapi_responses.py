"""Shared OpenAPI response definitions for consistent API documentation.

Use these in route decorators instead of inline response dicts so Swagger
documents all status codes without cluttering the code. Matches the standard
error shape from error-catalog and BaseAPIException (message, type, details).
"""

# Standard error body shape for OpenAPI examples (matches BaseAPIException / error-catalog)
ERROR_JSON_EXAMPLE = {
    "content": {
        "application/json": {
            "example": {
                "error": {
                    "message": "Human-readable summary",
                    "type": "ExceptionType",
                    "details": {},
                }
            }
        }
    }
}

RESP_400 = {"description": "Invalid input", **ERROR_JSON_EXAMPLE}
RESP_401 = {"description": "Authentication required or invalid"}
RESP_403 = {"description": "Insufficient permissions"}
RESP_404 = {"description": "Resource not found", **ERROR_JSON_EXAMPLE}
RESP_409 = {"description": "Conflict", **ERROR_JSON_EXAMPLE}
RESP_422 = {"description": "Validation error", **ERROR_JSON_EXAMPLE}
RESP_429 = {"description": "Rate limit exceeded"}
RESP_500 = {"description": "Internal server error", **ERROR_JSON_EXAMPLE}
RESP_503 = {"description": "Service temporarily unavailable", **ERROR_JSON_EXAMPLE}

__all__ = [
    "ERROR_JSON_EXAMPLE",
    "RESP_400",
    "RESP_401",
    "RESP_403",
    "RESP_404",
    "RESP_409",
    "RESP_422",
    "RESP_429",
    "RESP_500",
    "RESP_503",
]
