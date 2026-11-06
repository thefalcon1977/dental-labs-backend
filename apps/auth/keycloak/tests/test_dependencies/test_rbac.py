"""Tests for RBAC dependencies."""

import pytest

from apps.auth.keycloak.helpers.exceptions import InsufficientPermissionsError
from apps.auth.keycloak.schemas.user import UserInfo, UserPermissions, UserRoles
from apps.auth.keycloak.utils.jwt_validator import get_jwt_validator
from apps.auth.rbac import (
    require_all_permissions,
    require_all_roles,
    require_any_role,
    require_permissions,
    require_roles,
)
from apps.core.exceptions import ForbiddenError, ValidationError

pytestmark = [pytest.mark.integration, pytest.mark.keycloak_required]


class TestRBACDependencies:
    """Test cases for RBAC dependencies."""

    @pytest.fixture
    async def user_with_roles(self, access_token: str) -> UserInfo:
        """Get user with roles from real token."""
        validator = get_jwt_validator()
        payload = await validator.validate_token(access_token)
        return validator.get_user_from_token(payload)

    @pytest.mark.asyncio
    async def test_require_roles_success(self, user_with_roles: UserInfo) -> None:
        """Test require_roles with user having required role."""
        # Get realm roles from user
        if user_with_roles.roles.realm_roles:
            check_roles = require_roles(user_with_roles.roles.realm_roles[0])
            await check_roles(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no realm roles to test")

    @pytest.mark.asyncio
    async def test_require_roles_failure(self) -> None:
        """Test require_roles with user lacking required role."""
        # Create user without admin role
        user_without_admin = UserInfo(
            id="user-456",
            username="regularuser",
            roles=UserRoles(realm_roles=["user"], client_roles={}),
            permissions=UserPermissions(permissions=["read"]),
        )

        check_roles = require_roles("admin")
        with pytest.raises(ForbiddenError, match="Required roles"):
            await check_roles(user=user_without_admin)

    @pytest.mark.asyncio
    async def test_require_roles_any_of_multiple(
        self, user_with_roles: UserInfo
    ) -> None:
        """Test require_roles with user having one of multiple roles."""
        if user_with_roles.roles.realm_roles:
            check_roles = require_roles(
                user_with_roles.roles.realm_roles[0], "non-existent-role"
            )
            await check_roles(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no realm roles to test")

    @pytest.mark.asyncio
    async def test_require_roles_no_roles_specified(self) -> None:
        """Test require_roles with no roles specified."""
        with pytest.raises(
            ValidationError, match="At least one role must be specified"
        ):
            require_roles()

    @pytest.mark.asyncio
    async def test_require_all_roles_success(self, user_with_roles: UserInfo) -> None:
        """Test require_all_roles with user having all required roles."""
        if len(user_with_roles.roles.realm_roles) >= 2:
            check_all_roles = require_all_roles(
                user_with_roles.roles.realm_roles[0],
                user_with_roles.roles.realm_roles[1],
            )
            await check_all_roles(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User needs at least 2 realm roles to test")

    @pytest.mark.asyncio
    async def test_require_all_roles_failure(self, user_with_roles: UserInfo) -> None:
        """Test require_all_roles with user missing one role."""
        check_all_roles = require_all_roles(
            (
                user_with_roles.roles.realm_roles[0]
                if user_with_roles.roles.realm_roles
                else "user"
            ),
            "non-existent-role",
        )
        with pytest.raises(ForbiddenError, match="Missing required roles"):
            await check_all_roles(user=user_with_roles)

    @pytest.mark.asyncio
    async def test_require_all_roles_no_roles_specified(self) -> None:
        """Test require_all_roles with no roles specified."""
        with pytest.raises(
            ValidationError, match="At least one role must be specified"
        ):
            require_all_roles()

    @pytest.mark.asyncio
    async def test_require_any_role_alias(self, user_with_roles: UserInfo) -> None:
        """Test require_any_role as alias for require_roles."""
        if user_with_roles.roles.realm_roles:
            check_roles = require_any_role(user_with_roles.roles.realm_roles[0])
            await check_roles(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no realm roles to test")

    @pytest.mark.asyncio
    async def test_require_permissions_success(self, user_with_roles: UserInfo) -> None:
        """Test require_permissions with user having required permission."""
        if user_with_roles.permissions.permissions:
            check_permissions = require_permissions(
                user_with_roles.permissions.permissions[0]
            )
            await check_permissions(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no permissions to test")

    @pytest.mark.asyncio
    async def test_require_permissions_any_of_multiple(
        self, user_with_roles: UserInfo
    ) -> None:
        """Test require_permissions with user having one of multiple permissions."""
        if user_with_roles.permissions.permissions:
            check_permissions = require_permissions(
                user_with_roles.permissions.permissions[0], "non-existent-permission"
            )
            await check_permissions(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no permissions to test")

    @pytest.mark.asyncio
    async def test_require_permissions_failure(self) -> None:
        """Test require_permissions with user lacking required permission."""
        user_without_permission = UserInfo(
            id="user-456",
            username="readonlyuser",
            roles=UserRoles(realm_roles=["user"], client_roles={}),
            permissions=UserPermissions(permissions=["read"]),
        )

        check_permissions = require_permissions("delete")
        with pytest.raises(InsufficientPermissionsError, match="Required permissions"):
            await check_permissions(user=user_without_permission)

    @pytest.mark.asyncio
    async def test_require_permissions_no_permissions_specified(self) -> None:
        """Test require_permissions with no permissions specified."""
        with pytest.raises(
            ValidationError, match="At least one permission must be specified"
        ):
            require_permissions()

    @pytest.mark.asyncio
    async def test_require_all_permissions_success(
        self, user_with_roles: UserInfo
    ) -> None:
        """Test require_all_permissions with user having all required permissions."""
        if len(user_with_roles.permissions.permissions) >= 2:
            check_all_permissions = require_all_permissions(
                user_with_roles.permissions.permissions[0],
                user_with_roles.permissions.permissions[1],
            )
            await check_all_permissions(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User needs at least 2 permissions to test")

    @pytest.mark.asyncio
    async def test_require_all_permissions_failure(
        self, user_with_roles: UserInfo
    ) -> None:
        """Test require_all_permissions with user missing one permission."""
        check_all_permissions = require_all_permissions(
            (
                user_with_roles.permissions.permissions[0]
                if user_with_roles.permissions.permissions
                else "read"
            ),
            "non-existent-permission",
        )
        with pytest.raises(
            InsufficientPermissionsError, match="Missing required permissions"
        ):
            await check_all_permissions(user=user_with_roles)

    @pytest.mark.asyncio
    async def test_require_all_permissions_no_permissions_specified(
        self,
    ) -> None:
        """Test require_all_permissions with no permissions specified."""
        with pytest.raises(
            ValidationError, match="At least one permission must be specified"
        ):
            require_all_permissions()

    @pytest.mark.asyncio
    async def test_require_roles_realm_and_client(
        self, user_with_roles: UserInfo
    ) -> None:
        """Test require_roles with both realm and client roles."""
        # Test realm role
        if user_with_roles.roles.realm_roles:
            check_roles = require_roles(user_with_roles.roles.realm_roles[0])
            await check_roles(user=user_with_roles)
            # Should not raise exception
        else:
            pytest.skip("User has no realm roles to test")

        # Test client role if available
        if user_with_roles.roles.client_roles:
            client_id = list(user_with_roles.roles.client_roles.keys())[0]
            client_role = user_with_roles.roles.client_roles[client_id][0]
            check_roles = require_roles(client_role)
            await check_roles(user=user_with_roles)
            # Should not raise exception
