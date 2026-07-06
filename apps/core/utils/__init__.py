"""Core utility functions and helpers.

This package provides utility functions used across the application,
primarily focused on pagination utilities for database queries and
Python lists, timezone/datetime helpers, as well as security utilities
for input validation.

Main exports:
    - PaginationParams: Request pagination parameters
    - PaginationMeta: Pagination metadata for responses
    - PaginatedResponse: Generic paginated response model
    - paginate_query: SQL-level pagination for database queries
    - paginate_list: Python-level pagination for in-memory lists
    - Datetime utilities: UTC/Asia-Tehran conversions
    - Security utilities: Input validation and sanitization functions
"""

from .datetime_utils import (
    TEHRAN_TZ,
    UTC_TZ,
    assume_tehran_timezone,
    tehran_to_utc,
    utc_to_tehran,
)
from .pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    get_paginated_response,
    paginate_list,
    paginate_query,
    paginate_query_with_count_subquery,
)
from .security import (
    escape_like_pattern,
    redact_sensitive_fields,
    sanitize_for_logging,
    validate_s3_bucket_name,
    validate_s3_key,
)

__all__ = [
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "paginate_query",
    "paginate_query_with_count_subquery",
    "paginate_list",
    "get_paginated_response",
    "DEFAULT_PAGE",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MIN_PAGE_SIZE",
    # Datetime utilities
    "TEHRAN_TZ",
    "UTC_TZ",
    "assume_tehran_timezone",
    "tehran_to_utc",
    "utc_to_tehran",
    # Security utilities
    "validate_s3_bucket_name",
    "validate_s3_key",
    "escape_like_pattern",
    "sanitize_for_logging",
    "redact_sensitive_fields",
]
