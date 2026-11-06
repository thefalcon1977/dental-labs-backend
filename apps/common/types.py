"""Type aliases for common module."""

from typing import Any, TypeAlias

# Dictionary type aliases
ResponseDict: TypeAlias = dict[str, Any]
EndpointDict: TypeAlias = dict[str, str]
ChecksDict: TypeAlias = dict[str, Any]
DbInfoDict: TypeAlias = dict[str, Any]
CacheInfoDict: TypeAlias = dict[str, Any]
KeycloakInfoDict: TypeAlias = dict[str, Any]
S3InfoDict: TypeAlias = dict[str, Any]

# Tuple type aliases
ReadinessResult: TypeAlias = tuple[ChecksDict, bool]
DbHealthResult: TypeAlias = tuple[bool, DbInfoDict]
KeycloakHealthResult: TypeAlias = tuple[bool, KeycloakInfoDict]
S3HealthResult: TypeAlias = tuple[bool, S3InfoDict]

__all__ = [
    "ResponseDict",
    "EndpointDict",
    "ChecksDict",
    "DbInfoDict",
    "CacheInfoDict",
    "KeycloakInfoDict",
    "S3InfoDict",
    "ReadinessResult",
    "DbHealthResult",
    "KeycloakHealthResult",
    "S3HealthResult",
]
