"""User information schemas from Keycloak SSO tokens."""

from pydantic import BaseModel, ConfigDict

from ..types import ClaimsDict, ClientRolesDict, StringList


class UserRoles(BaseModel):
    """User roles structure from Keycloak token claims."""

    model_config = ConfigDict(from_attributes=True)

    realm_roles: StringList = []
    client_roles: ClientRolesDict = {}


class UserPermissions(BaseModel):
    """User permissions structure from Keycloak token claims."""

    model_config = ConfigDict(from_attributes=True)

    permissions: StringList = []


class UserInfo(BaseModel):
    """User information extracted from a Keycloak SSO token.

    Contains user identification and role information from Keycloak claims.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    roles: UserRoles
    permissions: UserPermissions
    groups: StringList = []
    client_id: str | None = None
    realm: str | None = None
    # Additional claims from Keycloak.
    claims: ClaimsDict = {}
