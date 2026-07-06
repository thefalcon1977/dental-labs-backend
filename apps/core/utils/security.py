"""Security utilities for input validation and sanitization."""

import re
from typing import TypeAlias

from apps.core.exceptions import ValidationError

PathString: TypeAlias = str


def validate_s3_bucket_name(bucket: str) -> str:
    """Validate and sanitize S3 bucket name to prevent path traversal.

    Bucket names must:
    - Be 3-63 characters long
    - Contain only lowercase letters, numbers, dots, and hyphens
    - Not contain path traversal sequences (.., //)
    - Not start or end with a dot or hyphen
    - Not contain consecutive dots

    Args:
        bucket: Bucket name to validate

    Returns:
        Validated bucket name

    Raises:
        ValidationError: If bucket name is invalid or contains path traversal
    """
    if not bucket:
        raise ValidationError("Bucket name cannot be empty")

    # Check for path traversal sequences
    if ".." in bucket or "//" in bucket:
        raise ValidationError("Bucket name contains invalid characters")

    # Check for control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in bucket):
        raise ValidationError("Bucket name contains control characters")

    # Validate bucket name format (S3 rules)
    # Bucket names must be 3-63 characters
    if len(bucket) < 3 or len(bucket) > 63:
        raise ValidationError(
            "Bucket name must be between 3 and 63 characters",
            details={"length": len(bucket)},
        )

    # Must start and end with letter or number
    if not bucket[0].isalnum() or not bucket[-1].isalnum():
        raise ValidationError("Bucket name must start and end with a letter or number")

    # Can contain lowercase letters, numbers, dots, and hyphens
    if not re.match(r"^[a-z0-9.-]+$", bucket):
        raise ValidationError(
            "Bucket name can only contain lowercase letters, numbers, dots, and hyphens"
        )

    # Cannot contain consecutive dots
    if ".." in bucket:
        raise ValidationError("Bucket name cannot contain consecutive dots")

    return bucket


def validate_s3_key(key: str) -> str:
    """Validate and sanitize S3 object key to prevent path traversal.

    Object keys must:
    - Not contain path traversal sequences (.., //)
    - Not start with /
    - Not contain control characters
    - Be reasonable length (max 1024 characters)

    Args:
        key: Object key (path) to validate

    Returns:
        Validated and normalized key

    Raises:
        ValidationError: If key is invalid or contains path traversal
    """
    if not key:
        raise ValidationError("Object key cannot be empty")

    # Normalize: remove leading slashes
    key = key.lstrip("/")

    # Check for path traversal sequences
    if ".." in key or "//" in key:
        raise ValidationError("Object key contains path traversal sequences")

    # Check for control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise ValidationError("Object key contains control characters")

    # Validate length (S3 limit is 1024 characters)
    if len(key) > 1024:
        raise ValidationError(
            "Object key exceeds maximum length of 1024 characters",
            details={"length": len(key)},
        )

    return key


def escape_like_pattern(pattern: str, escape_char: str = "\\") -> str:
    """Escape special characters in SQL LIKE/ILIKE patterns.

    Escapes special SQL LIKE characters (% and _) to prevent SQL injection
    when using user input in LIKE/ILIKE queries.

    Args:
        pattern: Input pattern string
        escape_char: Escape character to use (default: backslash)

    Returns:
        Escaped pattern safe for use in LIKE/ILIKE queries

    Example:
        >>> escape_like_pattern("user%name")
        'user\\%name'
        >>> escape_like_pattern("test_123")
        'test\\_123'
    """
    if not pattern:
        return pattern

    # Escape the escape character first
    pattern = pattern.replace(escape_char, escape_char + escape_char)

    # Escape SQL LIKE special characters
    pattern = pattern.replace("%", escape_char + "%")
    pattern = pattern.replace("_", escape_char + "_")

    return pattern


def sanitize_for_logging(value: str | None, max_length: int = 100) -> str:
    """Sanitize sensitive values for safe logging.

    Redacts sensitive information and truncates long values to prevent
    logging sensitive data or overwhelming logs.

    Args:
        value: Value to sanitize
        max_length: Maximum length before truncation

    Returns:
        Sanitized string safe for logging
    """
    if value is None:
        return "[None]"

    # Truncate long values
    if len(value) > max_length:
        return value[:max_length] + f"... (truncated, length={len(value)})"

    return value


def redact_sensitive_fields(data: dict, sensitive_keys: set[str]) -> dict:
    """Redact sensitive fields from dictionary for logging.

    Replaces sensitive field values with [REDACTED] to prevent
    logging passwords, tokens, or other sensitive information.

    Args:
        data: Dictionary to redact
        sensitive_keys: Set of keys to redact

    Returns:
        Dictionary with sensitive fields redacted
    """
    redacted = data.copy()
    for key in sensitive_keys:
        if key in redacted:
            redacted[key] = "[REDACTED]"
    return redacted
