"""Type aliases for authentication module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from .schemas.group import GroupResponse
    from .schemas.role import RoleResponse
    from .schemas.user import UserResponse

# Dictionary type aliases
TokenDataDict: TypeAlias = dict[str, Any]
UserInfoDict: TypeAlias = dict[str, Any]
ClaimsDict: TypeAlias = dict[str, Any]
TokenPayloadDict: TypeAlias = dict[str, Any]
DetailsDict: TypeAlias = dict[str, Any]
ParamsDict: TypeAlias = dict[str, str | int]
QueryParamsStrDict: TypeAlias = dict[str, str]
TokensDict: TypeAlias = dict[str, str]

# List type aliases
StringList: TypeAlias = list[str]
UserResponseList: TypeAlias = list["UserResponse"]
GroupResponseList: TypeAlias = list["GroupResponse"]
RoleResponseList: TypeAlias = list["RoleResponse"]

# Set type aliases
StringSet: TypeAlias = set[str]

# Nested dictionary type aliases
ProfileDict: TypeAlias = dict[str, list[str]]

__all__ = [
    "TokenDataDict",
    "UserInfoDict",
    "ClaimsDict",
    "TokenPayloadDict",
    "DetailsDict",
    "ParamsDict",
    "QueryParamsStrDict",
    "TokensDict",
    "StringList",
    "UserResponseList",
    "GroupResponseList",
    "RoleResponseList",
    "StringSet",
    "ProfileDict",
]
