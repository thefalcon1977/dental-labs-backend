"""Type aliases for core module.

This module provides type aliases used throughout the core package for
better type safety and code readability. All type aliases follow the
naming convention of ending with the type (e.g., ConfigDict, SystemInfoDict).

Type Aliases:
    ConfigDict: Dictionary for configuration data
    CorsConfigDict: Dictionary for CORS configuration
    SystemInfoDict: Dictionary for system information
    CpuInfoDict: Dictionary for CPU information
    MemoryInfoDict: Dictionary for memory information
    GpuInfoDict: Dictionary for GPU information
    ExceptionDetailsDict: Dictionary for exception details
    OrganizedConfigDict: Dictionary for organized configuration sections
    RequestCountsList: List of request count values
    RequestCountsDict: Dictionary mapping keys to request count lists
"""

from typing import Any, TypeAlias

# Dictionary type aliases
ConfigDict: TypeAlias = dict[str, Any]
CorsConfigDict: TypeAlias = dict[str, Any]
SystemInfoDict: TypeAlias = dict[str, Any]
CpuInfoDict: TypeAlias = dict[str, Any]
MemoryInfoDict: TypeAlias = dict[str, Any]
GpuInfoDict: TypeAlias = dict[str, Any]
ExceptionDetailsDict: TypeAlias = dict[str, Any]
OrganizedConfigDict: TypeAlias = dict[str, ConfigDict]

# List type aliases
RequestCountsList: TypeAlias = list[float]

# Nested dictionary type aliases
RequestCountsDict: TypeAlias = dict[str, RequestCountsList]

__all__ = [
    "ConfigDict",
    "CorsConfigDict",
    "SystemInfoDict",
    "CpuInfoDict",
    "MemoryInfoDict",
    "GpuInfoDict",
    "ExceptionDetailsDict",
    "OrganizedConfigDict",
    "RequestCountsList",
    "RequestCountsDict",
]
