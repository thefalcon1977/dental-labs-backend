"""Type aliases for authentication module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from .schemas.groups import GroupBrief, GroupDetail
    from .schemas.users import UserDetail

# Dictionary type aliases
TokenDataDict: TypeAlias = dict[str, Any]
UserInfoDict: TypeAlias = dict[str, Any]
JWKSDict: TypeAlias = dict[str, Any]
IntrospectionDict: TypeAlias = dict[str, Any]
ClaimsDict: TypeAlias = dict[str, Any]
TokenPayloadDict: TypeAlias = dict[str, Any]
DetailsDict: TypeAlias = dict[str, Any]
RawKeycloakDict: TypeAlias = dict[str, Any]
ParamsDict: TypeAlias = dict[str, str | int]
QueryParamsStrDict: TypeAlias = dict[str, str]
ConfigValidationResult: TypeAlias = tuple[bool, list[str]]
RoleCreateDict: TypeAlias = dict[str, str | None]
TokensDict: TypeAlias = dict[str, str]

# List type aliases
StringList: TypeAlias = list[str]
AudienceList: TypeAlias = list[str]
RawKeycloakList: TypeAlias = list[dict[str, Any]]
RawKeycloakListList: TypeAlias = list[RawKeycloakList]
UserDetailList: TypeAlias = list["UserDetail"]
GroupDetailList: TypeAlias = list["GroupDetail"]
GroupBriefList: TypeAlias = list["GroupBrief"]
GroupBriefNestedList: TypeAlias = list[list["GroupBrief"]]

# Set type aliases
StringSet: TypeAlias = set[str]

# Nested dictionary type aliases
ClientRolesDict: TypeAlias = dict[str, list[str]]
ProfileDict: TypeAlias = dict[str, list[str]]

__all__ = [
    "TokenDataDict",
    "UserInfoDict",
    "JWKSDict",
    "IntrospectionDict",
    "ClaimsDict",
    "TokenPayloadDict",
    "DetailsDict",
    "RawKeycloakDict",
    "ParamsDict",
    "QueryParamsStrDict",
    "ConfigValidationResult",
    "RoleCreateDict",
    "TokensDict",
    "StringList",
    "AudienceList",
    "RawKeycloakList",
    "RawKeycloakListList",
    "UserDetailList",
    "GroupDetailList",
    "GroupBriefList",
    "GroupBriefNestedList",
    "StringSet",
    "ClientRolesDict",
    "ProfileDict",
]
