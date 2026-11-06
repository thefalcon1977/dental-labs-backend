"""Parametrized tests for RBAC dependencies."""

import pytest

from apps.auth.keycloak.helpers.exceptions import InsufficientPermissionsError
from apps.auth.keycloak.tests.factories import create_user_info
from apps.auth.rbac import (
    require_all_permissions,
    require_all_roles,
    require_permissions,
    require_roles,
)
from apps.core.exceptions import ForbiddenError, ValidationError

pytestmark = [pytest.mark.unit]


class TestRBACDependenciesParametrized:
    """Parametrized tests for RBAC dependencies."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_roles,required_roles,should_succeed",
        [
            (["admin", "user"], ["admin"], True),
            (["admin", "user"], ["user"], True),
            (["admin", "user"], ["admin", "user"], True),
            (["user"], ["admin"], False),
            (
                ["user"],
                ["admin", "user"],
                True,
            ),  # User has "user", which is one of the required
            ([], ["admin"], False),
        ],
    )
    async def test_require_roles_variations(
        self, user_roles, required_roles, should_succeed
    ):
        """Test require_roles with various role combinations."""
        user = create_user_info(
            id="test-user",
            username="testuser",
            realm_roles=user_roles,
        )

        check_roles = require_roles(*required_roles)
        if should_succeed:
            await check_roles(user=user)
            # Should not raise exception
        else:
            with pytest.raises(ForbiddenError, match="Required roles"):
                await check_roles(user=user)

    @pytest.mark.asyncio
    async def test_require_roles_no_roles_specified(self):
        """Test require_roles with no roles specified."""
        with pytest.raises(
            ValidationError, match="At least one role must be specified"
        ):
            require_roles()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_permissions,required_permissions,should_succeed",
        [
            (["read", "write"], ["read"], True),
            (["read", "write"], ["write"], True),
            (["read", "write"], ["read", "write"], True),
            (["read"], ["write"], False),
            (
                ["read"],
                ["read", "write"],
                True,
            ),  # User has "read", which is one of the required
            ([], ["read"], False),
        ],
    )
    async def test_require_permissions_variations(
        self, user_permissions, required_permissions, should_succeed
    ):
        """Test require_permissions with various permission combinations."""
        user = create_user_info(
            id="test-user",
            username="testuser",
            permissions=user_permissions,
        )

        check_permissions = require_permissions(*required_permissions)
        if should_succeed:
            await check_permissions(user=user)
            # Should not raise exception
        else:
            with pytest.raises(
                InsufficientPermissionsError, match="Required permissions"
            ):
                await check_permissions(user=user)

    @pytest.mark.asyncio
    async def test_require_permissions_no_permissions_specified(self):
        """Test require_permissions with no permissions specified."""
        with pytest.raises(
            ValidationError, match="At least one permission must be specified"
        ):
            require_permissions()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_roles,required_roles,should_succeed",
        [
            (["admin", "user"], ["admin", "user"], True),
            (["admin", "user"], ["admin"], True),  # Has all required
            (["admin"], ["admin", "user"], False),  # Missing one
            (["user"], ["admin", "user"], False),  # Missing one
            ([], ["admin", "user"], False),
        ],
    )
    async def test_require_all_roles_variations(
        self, user_roles, required_roles, should_succeed
    ):
        """Test require_all_roles with various role combinations."""
        user = create_user_info(
            id="test-user",
            username="testuser",
            realm_roles=user_roles,
        )

        if should_succeed:
            check_all_roles = require_all_roles(*required_roles)
            await check_all_roles(user=user)
            # Should not raise exception
        else:
            check_all_roles = require_all_roles(*required_roles)
            with pytest.raises(ForbiddenError, match="Missing required roles"):
                await check_all_roles(user=user)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "user_permissions,required_permissions,should_succeed",
        [
            (["read", "write", "delete"], ["read", "write"], True),
            (["read", "write"], ["read", "write"], True),
            (["read"], ["read", "write"], False),  # Missing one
            (["write"], ["read", "write"], False),  # Missing one
            ([], ["read", "write"], False),
        ],
    )
    async def test_require_all_permissions_variations(
        self, user_permissions, required_permissions, should_succeed
    ):
        """Test require_all_permissions with various permission combinations."""
        user = create_user_info(
            id="test-user",
            username="testuser",
            permissions=user_permissions,
        )

        if should_succeed:
            check_all_permissions = require_all_permissions(*required_permissions)
            await check_all_permissions(user=user)
            # Should not raise exception
        else:
            check_all_permissions = require_all_permissions(*required_permissions)
            with pytest.raises(
                InsufficientPermissionsError, match="Missing required permissions"
            ):
                await check_all_permissions(user=user)
