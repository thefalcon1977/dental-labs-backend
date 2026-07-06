"""Additional logging configuration utilities."""

from typing import Any

import structlog


def get_request_id() -> str | None:
    """Return the current request ID from context, if set.

    Used to propagate correlation IDs to outbound HTTP calls (e.g. X-Request-ID).
    Returns None when not in a request context (e.g. background tasks, startup).

    Returns:
        Request ID string, or None if not bound in current context.
    """
    try:
        ctx = structlog.contextvars.get_contextvars()
        return ctx.get("request_id")
    except Exception:
        return None


def add_request_context(**kwargs: Any) -> None:
    """Add context variables to all subsequent log entries in the current context.

    This is useful for adding request-specific information like request_id,
    user_id, etc. that will be included in all log entries.

    Args:
        **kwargs: Key-value pairs to add to the logging context.

    Example:
        ```python
        from config.logging import add_request_context

        add_request_context(request_id="abc123", user_id=456)
        # All subsequent logs will include request_id and user_id
        ```
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_request_context() -> None:
    """Clear all context variables from the current context."""
    structlog.contextvars.clear_contextvars()


__all__ = ["add_request_context", "clear_request_context", "get_request_id"]
