"""Integration tests for authentication flow."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps.auth.keycloak.dependencies.auth import get_current_user, get_optional_user
from apps.auth.keycloak.schemas.user import UserInfo
from apps.auth.rbac import require_permissions, require_roles

pytestmark = [pytest.mark.integration, pytest.mark.keycloak_required, pytest.mark.slow]


class TestAuthFlowIntegration:
    """Integration tests for complete authentication flow."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app for testing."""
        from apps.core.app_factory import create_app

        return create_app()

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(
        self, app: FastAPI, access_token: str
    ) -> None:
        """Test accessing protected endpoint with valid token."""

        # Create a test endpoint
        @app.get("/test-protected")
        async def protected_endpoint(
            user: UserInfo = Depends(get_current_user),
        ) -> dict:
            return {"user_id": user.id, "username": user.username}

        client = TestClient(app)
        response = client.get(
            "/test-protected",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is not None
        assert data["username"] is not None

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, app: FastAPI) -> None:
        """Test accessing protected endpoint without token."""

        @app.get("/test-protected")
        async def protected_endpoint(
            user: UserInfo = Depends(get_current_user),
        ) -> dict:
            return {"user_id": user.id}

        client = TestClient(app)
        response = client.get("/test-protected")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, app: FastAPI) -> None:
        """Test accessing protected endpoint with invalid token."""

        @app.get("/test-protected")
        async def protected_endpoint(
            user: UserInfo = Depends(get_current_user),
        ) -> dict:
            return {"user_id": user.id}

        client = TestClient(app)
        response = client.get(
            "/test-protected",
            headers={"Authorization": "Bearer invalid-token-12345"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rbac_endpoint_with_required_role(
        self, app: FastAPI, access_token: str, authenticated_user_info: dict | None
    ) -> None:
        """Test accessing RBAC endpoint with required role."""
        # Get user roles from token
        from apps.auth.keycloak.utils.jwt_validator import get_jwt_validator

        validator = get_jwt_validator()
        payload = await validator.validate_token(access_token)
        user_info = validator.get_user_from_token(payload)

        # Use a role that the user has
        if user_info.roles.realm_roles:
            required_role = user_info.roles.realm_roles[0]

            @app.get("/test-admin")
            async def admin_endpoint(
                user: UserInfo = Depends(get_current_user),
                _: None = Depends(require_roles(required_role)),
            ) -> dict:
                return {"message": "Admin access granted"}

            client = TestClient(app)
            response = client.get(
                "/test-admin",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Admin access granted"
        else:
            pytest.skip("User has no realm roles to test")

    @pytest.mark.asyncio
    async def test_rbac_endpoint_without_required_role(
        self, app: FastAPI, access_token: str
    ) -> None:
        """Test accessing RBAC endpoint without required role."""

        @app.get("/test-admin")
        async def admin_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_roles("non-existent-role-12345")),
        ) -> dict:
            return {"message": "Admin access granted"}

        client = TestClient(app)
        response = client.get(
            "/test-admin",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_permission_endpoint_with_required_permission(
        self, app: FastAPI, access_token: str, authenticated_user_info: dict | None
    ) -> None:
        """Test accessing permission endpoint with required permission."""
        # Get user permissions from token
        from apps.auth.keycloak.utils.jwt_validator import get_jwt_validator

        validator = get_jwt_validator()
        payload = await validator.validate_token(access_token)
        user_info = validator.get_user_from_token(payload)

        # Use a permission that the user has
        if user_info.permissions.permissions:
            required_permission = user_info.permissions.permissions[0]

            @app.post("/test-write")
            async def write_endpoint(
                user: UserInfo = Depends(get_current_user),
                _: None = Depends(require_permissions(required_permission)),
            ) -> dict:
                return {"message": "Write access granted"}

            client = TestClient(app)
            response = client.post(
                "/test-write",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Write access granted"
        else:
            pytest.skip("User has no permissions to test")

    @pytest.mark.asyncio
    async def test_permission_endpoint_without_required_permission(
        self, app: FastAPI, access_token: str
    ) -> None:
        """Test accessing permission endpoint without required permission."""

        @app.post("/test-write")
        async def write_endpoint(
            user: UserInfo = Depends(get_current_user),
            _: None = Depends(require_permissions("non-existent-permission-12345")),
        ) -> dict:
            return {"message": "Write access granted"}

        client = TestClient(app)
        response = client.post(
            "/test-write",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_optional_auth_endpoint_with_token(
        self, app: FastAPI, access_token: str
    ) -> None:
        """Test optional auth endpoint with valid token."""

        @app.get("/test-optional")
        async def optional_endpoint(
            user: UserInfo | None = Depends(get_optional_user),
        ) -> dict:
            if user:
                return {"authenticated": True, "user_id": user.id}
            return {"authenticated": False}

        client = TestClient(app)
        response = client.get(
            "/test-optional",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] is not None

    @pytest.mark.asyncio
    async def test_optional_auth_endpoint_without_token(self, app: FastAPI) -> None:
        """Test optional auth endpoint without token."""

        @app.get("/test-optional")
        async def optional_endpoint(
            user: UserInfo | None = Depends(get_optional_user),
        ) -> dict:
            if user:
                return {"authenticated": True, "user_id": user.id}
            return {"authenticated": False}

        client = TestClient(app)
        response = client.get("/test-optional")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
