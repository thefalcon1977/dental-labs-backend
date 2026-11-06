"""Type aliases for the local JWT authentication provider."""

from dataclasses import dataclass, field
from typing import Any, TypeAlias

TokenClaimsDict: TypeAlias = dict[str, Any]
RoleList: TypeAlias = list[str]
NameList: TypeAlias = list[str]
IssuedToken: TypeAlias = tuple[str, int]


@dataclass(frozen=True)
class UserAccess:
    """A user's effective access, resolved from direct and group grants.

    Attributes:
        roles: Sorted role names (direct + inherited from groups).
        groups: Sorted names of groups the user belongs to.
        permissions: Sorted permission codes from all effective roles.
    """

    roles: NameList = field(default_factory=list)
    groups: NameList = field(default_factory=list)
    permissions: NameList = field(default_factory=list)


__all__ = [
    "IssuedToken",
    "NameList",
    "RoleList",
    "TokenClaimsDict",
    "UserAccess",
]
