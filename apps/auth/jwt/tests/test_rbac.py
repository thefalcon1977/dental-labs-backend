"""Tests for JWT-mode groups, roles, and permissions (service, API, tokens)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TypeAlias
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from apps.auth import dependencies as auth_dependencies
from apps.auth.config import AuthMode
from apps.auth.jwt import schemas
from apps.auth.jwt.helpers.exceptions import ProtectedResourceError
from apps.auth.jwt.models import Group, LocalUser, Permission, Role
from apps.auth.jwt.routers.router import router as jwt_router
from apps.auth.jwt.services import rbac_service
from apps.auth.jwt.types import NameList, UserAccess
from apps.auth.jwt.utils import tokens
from apps.core.db import get_db
from apps.core.exceptions import NotFoundError, register_exception_handlers
from apps.core.utils import PaginationParams

Link: TypeAlias = tuple[str, str]
LinkSet: TypeAlias = set[Link]
HeaderDict: TypeAlias = dict[str, str]

ADMIN_PERMISSION = "auth:manage"
ADMIN_ROLE = "admin"


def _stamp(entity: Permission | Role | Group | LocalUser) -> None:
    """Give an in-memory entity the id/timestamp the database would."""
    entity.id = entity.id or str(uuid4())
    entity.created_at = datetime.now(UTC)


class FakeRbacStore:
    """In-memory stand-in for the DAL/BLL functions used by ``rbac_service``."""

    def __init__(self) -> None:
        """Seed the admin permission and role, like the migration does."""
        self.permissions: dict[str, Permission] = {}
        self.roles: dict[str, Role] = {}
        self.groups: dict[str, Group] = {}
        self.users: dict[str, LocalUser] = {}
        self.role_permissions: LinkSet = set()
        self.group_roles: LinkSet = set()
        self.user_groups: LinkSet = set()
        self.user_roles: LinkSet = set()

        self.admin_permission = self._new_permission(ADMIN_PERMISSION)
        self.admin_role = self._new_role(ADMIN_ROLE)
        self.role_permissions.add((self.admin_role.id, self.admin_permission.id))

    # Seeding helpers

    def _new_permission(self, code: str) -> Permission:
        permission = Permission(code=code)
        _stamp(permission)
        self.permissions[permission.id] = permission
        return permission

    def _new_role(self, name: str) -> Role:
        role = Role(name=name)
        _stamp(role)
        self.roles[role.id] = role
        return role

    def add_user(self, username: str) -> LocalUser:
        user = LocalUser(
            username=username,
            email=f"{username}@example.com",
            password_hash="x",
            is_active=True,
        )
        _stamp(user)
        self.users[user.id] = user
        return user

    def _detail_role(self, role: Role) -> Role:
        role.__dict__["permissions"] = sorted(
            (self.permissions[p] for r, p in self.role_permissions if r == role.id),
            key=lambda p: p.code,
        )
        return role

    def _detail_group(self, group: Group) -> Group:
        group.__dict__["roles"] = sorted(
            (self.roles[r] for g, r in self.group_roles if g == group.id),
            key=lambda r: r.name,
        )
        return group

    # DAL

    async def get_permission(self, db: object, permission_id: str) -> Permission | None:
        return self.permissions.get(permission_id)

    async def get_permission_by_code(self, db: object, code: str) -> Permission | None:
        return next((p for p in self.permissions.values() if p.code == code), None)

    async def get_role(
        self, db: object, role_id: str, with_permissions: bool = False
    ) -> Role | None:
        role = self.roles.get(role_id)
        return self._detail_role(role) if role and with_permissions else role

    async def get_role_by_name(self, db: object, name: str) -> Role | None:
        return next((r for r in self.roles.values() if r.name == name), None)

    async def get_group(
        self, db: object, group_id: str, with_roles: bool = False
    ) -> Group | None:
        group = self.groups.get(group_id)
        return self._detail_group(group) if group and with_roles else group

    async def list_permissions(
        self, db: object, pagination: PaginationParams, search: str | None
    ) -> tuple[list[Permission], int]:
        items = sorted(self.permissions.values(), key=lambda p: p.code)
        return items, len(items)

    async def user_exists(self, db: object, user_id: str) -> bool:
        return user_id in self.users

    async def get_user_by_login(self, db: object, login: str) -> LocalUser | None:
        return next((u for u in self.users.values() if u.username == login), None)

    async def get_user_direct_role_names(self, db: object, user_id: str) -> NameList:
        return sorted(self.roles[r].name for u, r in self.user_roles if u == user_id)

    async def get_user_access(self, db: object, user_id: str) -> UserAccess:
        group_ids = {g for u, g in self.user_groups if u == user_id}
        role_ids = {r for u, r in self.user_roles if u == user_id} | {
            r for g, r in self.group_roles if g in group_ids
        }
        return UserAccess(
            roles=sorted(self.roles[r].name for r in role_ids),
            groups=sorted(self.groups[g].name for g in group_ids),
            permissions=sorted(
                {
                    self.permissions[p].code
                    for r, p in self.role_permissions
                    if r in role_ids
                }
            ),
        )

    # BLL

    async def create_permission(
        self, db: object, data: schemas.PermissionCreate
    ) -> Permission:
        permission = self._new_permission(data.code)
        permission.description = data.description
        return permission

    async def delete_permission(self, db: object, permission: Permission) -> None:
        del self.permissions[permission.id]

    async def create_role(self, db: object, data: schemas.RoleCreate) -> Role:
        return self._new_role(data.name)

    async def update_role(
        self, db: object, role: Role, data: schemas.RoleUpdate
    ) -> Role:
        for field in data.model_fields_set:
            setattr(role, field, getattr(data, field))
        return role

    async def delete_role(self, db: object, role: Role) -> None:
        del self.roles[role.id]

    async def add_permission_to_role(
        self, db: object, role_id: str, permission_id: str
    ) -> None:
        self.role_permissions.add((role_id, permission_id))

    async def remove_permission_from_role(
        self, db: object, role_id: str, permission_id: str
    ) -> None:
        self.role_permissions.discard((role_id, permission_id))

    async def create_group(self, db: object, data: schemas.GroupCreate) -> Group:
        group = Group(name=data.name, description=data.description)
        _stamp(group)
        self.groups[group.id] = group
        return group

    async def add_role_to_group(self, db: object, group_id: str, role_id: str) -> None:
        self.group_roles.add((group_id, role_id))

    async def add_user_to_group(self, db: object, group_id: str, user_id: str) -> None:
        self.user_groups.add((user_id, group_id))

    async def remove_user_from_group(
        self, db: object, group_id: str, user_id: str
    ) -> None:
        self.user_groups.discard((user_id, group_id))

    async def add_role_to_user(self, db: object, user_id: str, role_id: str) -> None:
        self.user_roles.add((user_id, role_id))

    async def remove_role_from_user(
        self, db: object, user_id: str, role_id: str
    ) -> None:
        self.user_roles.discard((user_id, role_id))

    async def create_user(self, db: object, data: schemas.RegisterRequest) -> LocalUser:
        return self.add_user(data.username)

    async def ensure_admin_role(self, db: object) -> Role:
        return self.admin_role


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeRbacStore:
    """Wire a fake store into ``rbac_service``."""
    fake = FakeRbacStore()
    monkeypatch.setattr(rbac_service, "dal", fake)
    monkeypatch.setattr(rbac_service, "bll", fake)
    return fake


@pytest_asyncio.fixture
async def client(
    store: FakeRbacStore, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """HTTP client for an app mounting the JWT router with auth in JWT mode."""
    monkeypatch.setattr(auth_dependencies, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth_dependencies, "get_auth_mode", lambda: AuthMode.JWT)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(jwt_router, prefix="/auth")

    async def fake_db() -> AsyncIterator[None]:
        yield None

    app.dependency_overrides[get_db] = fake_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def bearer(user: LocalUser, permissions: NameList) -> HeaderDict:
    """Build an Authorization header for ``user`` with the given permissions."""
    access = UserAccess(roles=[], groups=[], permissions=permissions)
    token, _ = tokens.create_access_token(user, access)
    return {"Authorization": f"Bearer {token}"}


class TestEffectiveAccess:
    """Users get their own roles plus their groups' roles and permissions."""

    @pytest.mark.asyncio
    async def test_group_roles_are_inherited(self, store: FakeRbacStore) -> None:
        user = store.add_user("jane")
        perm = await rbac_service.create_permission(
            None, schemas.PermissionCreate(code="orders:read")
        )
        role = await rbac_service.create_role(None, schemas.RoleCreate(name="viewer"))
        group = await rbac_service.create_group(None, schemas.GroupCreate(name="Ops"))
        await rbac_service.add_permission_to_role(None, role.id, perm.id)
        await rbac_service.add_role_to_group(None, group.id, role.id)
        await rbac_service.add_user_to_group(None, group.id, user.id)

        access = await rbac_service.get_user_access(None, user.id)

        assert access.direct_roles == []
        assert access.groups == ["Ops"]
        assert access.effective_roles == ["viewer"]
        assert access.permissions == ["orders:read"]

        await rbac_service.remove_user_from_group(None, group.id, user.id)
        access = await rbac_service.get_user_access(None, user.id)
        assert access.effective_roles == []
        assert access.permissions == []

    @pytest.mark.asyncio
    async def test_direct_role(self, store: FakeRbacStore) -> None:
        user = store.add_user("jane")
        access = await rbac_service.add_role_to_user(None, user.id, store.admin_role.id)
        assert access.direct_roles == [ADMIN_ROLE]
        assert access.permissions == [ADMIN_PERMISSION]

    @pytest.mark.asyncio
    async def test_access_token_carries_groups_and_permissions(
        self, store: FakeRbacStore
    ) -> None:
        user = store.add_user("jane")
        access = UserAccess(
            roles=["viewer"], groups=["Ops"], permissions=["orders:read"]
        )
        token, _ = tokens.create_access_token(user, access)
        info = tokens.user_info_from_claims(
            tokens.decode_token(token, tokens.ACCESS_TOKEN_TYPE)
        )
        assert info.roles.realm_roles == ["viewer"]
        assert info.groups == ["Ops"]
        assert info.permissions.permissions == ["orders:read"]


class TestProtectedResources:
    """The admin role/permission cannot be removed through the API."""

    @pytest.mark.asyncio
    async def test_cannot_delete_admin_permission(self, store: FakeRbacStore) -> None:
        with pytest.raises(ProtectedResourceError):
            await rbac_service.delete_permission(None, store.admin_permission.id)

    @pytest.mark.asyncio
    async def test_cannot_delete_admin_role(self, store: FakeRbacStore) -> None:
        with pytest.raises(ProtectedResourceError):
            await rbac_service.delete_role(None, store.admin_role.id)

    @pytest.mark.asyncio
    async def test_cannot_rename_admin_role(self, store: FakeRbacStore) -> None:
        with pytest.raises(ProtectedResourceError):
            await rbac_service.update_role(
                None, store.admin_role.id, schemas.RoleUpdate(name="root")
            )

    @pytest.mark.asyncio
    async def test_admin_role_description_is_editable(
        self, store: FakeRbacStore
    ) -> None:
        role = await rbac_service.update_role(
            None, store.admin_role.id, schemas.RoleUpdate(description="Ops admins")
        )
        assert role.description == "Ops admins"

    @pytest.mark.asyncio
    async def test_cannot_strip_admin_permission_from_admin_role(
        self, store: FakeRbacStore
    ) -> None:
        with pytest.raises(ProtectedResourceError):
            await rbac_service.remove_permission_from_role(
                None, store.admin_role.id, store.admin_permission.id
            )

    @pytest.mark.asyncio
    async def test_missing_role_is_404(self, store: FakeRbacStore) -> None:
        with pytest.raises(NotFoundError):
            await rbac_service.add_role_to_user(None, "nope", store.admin_role.id)


class TestCreateAdmin:
    """Bootstrap via ``rbac_service.create_admin`` (used by the CLI)."""

    @pytest.mark.asyncio
    async def test_creates_user_and_grants_admin(self, store: FakeRbacStore) -> None:
        access = await rbac_service.create_admin(
            None,
            schemas.RegisterRequest(
                username="root", email="root@example.com", password="x" * 12
            ),
        )
        assert access.direct_roles == [ADMIN_ROLE]
        assert access.permissions == [ADMIN_PERMISSION]

    @pytest.mark.asyncio
    async def test_existing_user_is_promoted(self, store: FakeRbacStore) -> None:
        user = store.add_user("root")
        access = await rbac_service.create_admin(
            None,
            schemas.RegisterRequest(
                username="root", email="root@example.com", password="x" * 12
            ),
        )
        assert access.user_id == user.id
        assert len(store.users) == 1


class TestAdminEndpoints:
    """The admin API requires the admin permission."""

    @pytest.mark.asyncio
    async def test_requires_token(self, client: AsyncClient) -> None:
        response = await client.get("/auth/roles")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_forbidden_without_admin_permission(
        self, client: AsyncClient, store: FakeRbacStore
    ) -> None:
        headers = bearer(store.add_user("jane"), ["orders:read"])
        response = await client.get("/auth/permissions", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_flow(self, client: AsyncClient, store: FakeRbacStore) -> None:
        user = store.add_user("jane")
        headers = bearer(store.add_user("boss"), [ADMIN_PERMISSION])

        listed = await client.get("/auth/permissions", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["items"][0]["code"] == ADMIN_PERMISSION

        perm = await client.post(
            "/auth/permissions", headers=headers, json={"code": "orders:read"}
        )
        assert perm.status_code == 201
        role = await client.post(
            "/auth/roles", headers=headers, json={"name": "viewer"}
        )
        assert role.status_code == 201
        role_id, perm_id = role.json()["id"], perm.json()["id"]

        granted = await client.put(
            f"/auth/roles/{role_id}/permissions/{perm_id}", headers=headers
        )
        assert granted.status_code == 200
        assert [p["code"] for p in granted.json()["permissions"]] == ["orders:read"]

        access = await client.put(
            f"/auth/users/{user.id}/roles/{role_id}", headers=headers
        )
        assert access.status_code == 200
        assert access.json()["permissions"] == ["orders:read"]

    @pytest.mark.asyncio
    async def test_delete_admin_role_returns_409(
        self, client: AsyncClient, store: FakeRbacStore
    ) -> None:
        headers = bearer(store.add_user("boss"), [ADMIN_PERMISSION])
        response = await client.delete(
            f"/auth/roles/{store.admin_role.id}", headers=headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["type"] == "ProtectedResourceError"

    @pytest.mark.asyncio
    async def test_unknown_role_returns_404(
        self, client: AsyncClient, store: FakeRbacStore
    ) -> None:
        headers = bearer(store.add_user("boss"), [ADMIN_PERMISSION])
        response = await client.get("/auth/roles/missing", headers=headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_permission_code_returns_422(
        self, client: AsyncClient, store: FakeRbacStore
    ) -> None:
        headers = bearer(store.add_user("boss"), [ADMIN_PERMISSION])
        response = await client.post(
            "/auth/permissions", headers=headers, json={"code": "Bad Code!"}
        )
        assert response.status_code == 422


@pytest.mark.parametrize("layer", ["dal", "bll"])
def test_real_repository_exposes_what_services_call(layer: str) -> None:
    """Fakes hide missing functions; check the real packages export them all."""
    import ast
    import inspect

    from apps.auth.jwt import repository
    from apps.auth.jwt.services import auth_service

    module = getattr(repository, layer)
    called = set()
    for service in (auth_service, rbac_service):
        for node in ast.walk(ast.parse(inspect.getsource(service))):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == layer
            ):
                called.add(node.attr)
    assert called, layer
    assert not {name for name in called if not hasattr(module, name)}


def test_admin_routes_mounted_only_via_jwt_router() -> None:
    """Admin paths exist on the JWT router."""
    paths = {route.path for route in jwt_router.routes}
    assert {"/permissions", "/roles/{role_id}", "/groups/{group_id}/members"} <= paths
