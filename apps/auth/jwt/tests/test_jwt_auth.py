"""Tests for local JWT auth: passwords, tokens, service, endpoints, and mode dispatch."""

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from apps.auth import dependencies as auth_dependencies
from apps.auth.config import AuthMode
from apps.auth.jwt import schemas
from apps.auth.jwt.helpers.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    RegistrationDisabledError,
    UserAlreadyExistsError,
)
from apps.auth.jwt.models import LocalUser, LocalUserProfile
from apps.auth.jwt.routers.router import router as jwt_router
from apps.auth.jwt.services import auth_service
from apps.auth.jwt.types import UserAccess
from apps.auth.jwt.utils import passwords, tokens
from apps.auth.keycloak.helpers.exceptions import (
    AuthDisabledError,
    InvalidTokenError,
    TokenExpiredError,
)
from apps.core.db import get_db
from apps.core.exceptions import UnauthorizedError, register_exception_handlers
from config.settings import settings

PASSWORD = "correct horse battery"
DEFAULT_ACCESS = UserAccess(roles=["user"], groups=[], permissions=[])


class FakeUserStore:
    """In-memory stand-in for the DAL/BLL modules used by the service."""

    def __init__(self) -> None:
        """Initialize an empty store."""
        self.users: dict[str, LocalUser] = {}
        self.profiles: dict[str, LocalUserProfile] = {}

    async def get_profile_by_user_id(
        self, db: object, user_id: str
    ) -> LocalUserProfile | None:
        """Fake ``dal.get_profile_by_user_id``."""
        return self.profiles.get(user_id)

    async def update_profile(
        self, db: object, user_id: str, data: schemas.ProfileUpdate
    ) -> LocalUserProfile:
        """Fake ``bll.update_profile`` with the same partial-update rule."""
        profile = self.profiles.setdefault(user_id, LocalUserProfile(user_id=user_id))
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field == "avatar_url" and value is not None:
                value = str(value)
            setattr(profile, field, value)
        profile.updated_at = datetime.now(UTC)
        return profile

    async def add(self, username: str, email: str, is_active: bool = True) -> LocalUser:
        """Insert a user with ``PASSWORD`` as the password.

        Args:
            username: Lowercase username.
            email: Lowercase email.
            is_active: Whether the account is active.

        Returns:
            The stored user.
        """
        user = LocalUser(
            id=str(uuid4()),
            username=username,
            email=email,
            password_hash=await passwords.hash_password(PASSWORD),
            first_name="Jane",
            last_name="Doe",
            is_active=is_active,
        )
        user.created_at = datetime.now(UTC)
        self.users[user.id] = user
        return user

    async def get_user_by_id(self, db: object, user_id: str) -> LocalUser | None:
        """Fake ``dal.get_user_by_id``."""
        return self.users.get(user_id)

    async def get_user_by_login(self, db: object, login: str) -> LocalUser | None:
        """Fake ``dal.get_user_by_login``."""
        value = login.strip().lower()
        return next(
            (u for u in self.users.values() if value in (u.username, u.email)), None
        )

    async def create_user(self, db: object, data: schemas.RegisterRequest) -> LocalUser:
        """Fake ``bll.create_user`` with the same uniqueness rule."""
        for user in self.users.values():
            if user.username == data.username:
                raise UserAlreadyExistsError("username")
            if user.email == data.email:
                raise UserAlreadyExistsError("email")
        return await self.add(data.username, data.email)

    async def get_user_access(self, db: object, user_id: str) -> UserAccess:
        """Fake ``dal.get_user_access``: every user has only the ``user`` role."""
        return DEFAULT_ACCESS

    async def record_login(self, db: object, user: LocalUser) -> LocalUser:
        """Fake ``bll.record_login``."""
        user.last_login_at = datetime.now(UTC)
        return user


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeUserStore:
    """Wire a fake store into the service and force JWT mode on."""
    fake = FakeUserStore()
    monkeypatch.setattr(auth_service, "dal", fake)
    monkeypatch.setattr(auth_service, "bll", fake)
    monkeypatch.setattr(auth_service, "is_jwt_mode", lambda: True)
    monkeypatch.setitem(settings.auth, "JWT_REGISTRATION_ENABLED", True)
    return fake


@pytest_asyncio.fixture
async def client(store: FakeUserStore) -> AsyncIterator[AsyncClient]:
    """HTTP client for an app mounting only the JWT auth router."""
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


class TestPasswords:
    """Password hashing."""

    @pytest.mark.asyncio
    async def test_hash_roundtrip(self) -> None:
        encoded = await passwords.hash_password(PASSWORD)
        assert encoded.startswith("scrypt$")
        assert PASSWORD not in encoded
        assert await passwords.verify_password(PASSWORD, encoded)
        assert not await passwords.verify_password("wrong", encoded)

    def test_salts_differ(self) -> None:
        assert passwords.hash_password_sync("x" * 8) != passwords.hash_password_sync(
            "x" * 8
        )

    @pytest.mark.parametrize("encoded", ["", "garbage", "bcrypt$1$2$3$a$b"])
    def test_malformed_hash_is_rejected(self, encoded: str) -> None:
        assert passwords.verify_password_sync(PASSWORD, encoded) is False


class TestTokens:
    """Token issue/verify."""

    @pytest.mark.asyncio
    async def test_access_token_maps_to_user_info(self, store: FakeUserStore) -> None:
        user = await store.add("jane", "jane@example.com")
        token, ttl = tokens.create_access_token(user, DEFAULT_ACCESS)
        claims = tokens.decode_token(token, tokens.ACCESS_TOKEN_TYPE)
        info = tokens.user_info_from_claims(claims)
        assert ttl == settings.auth.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert info.id == user.id
        assert info.username == "jane"
        assert info.roles.realm_roles == ["user"]
        assert info.full_name == "Jane Doe"

    @pytest.mark.asyncio
    async def test_refresh_token_rejected_as_access(self, store: FakeUserStore) -> None:
        user = await store.add("jane", "jane@example.com")
        refresh, _ = tokens.create_refresh_token(user)
        with pytest.raises(InvalidTokenError):
            tokens.decode_token(refresh, tokens.ACCESS_TOKEN_TYPE)

    def test_tampered_token_rejected(self) -> None:
        forged = jwt.encode(
            {"sub": "x", "typ": "access", "exp": int(time.time()) + 60},
            "not-the-real-secret-not-the-real-secret",
            algorithm="HS256",
        )
        with pytest.raises(InvalidTokenError):
            tokens.decode_token(forged, tokens.ACCESS_TOKEN_TYPE)

    def test_expired_token_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        token, _ = tokens._encode({"sub": "x"}, tokens.ACCESS_TOKEN_TYPE, ttl=-10)
        with pytest.raises(TokenExpiredError):
            tokens.decode_token(token, tokens.ACCESS_TOKEN_TYPE)

    @pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer "])
    def test_bad_authorization_header(self, header: str | None) -> None:
        with pytest.raises(InvalidTokenError):
            tokens.extract_bearer_token(header)


class TestAuthService:
    """Service-level rules."""

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, store: FakeUserStore) -> None:
        await store.add("jane", "jane@example.com")
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                None, schemas.LoginRequest(username="jane", password="nope")
            )

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, store: FakeUserStore) -> None:
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                None, schemas.LoginRequest(username="ghost", password=PASSWORD)
            )

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, store: FakeUserStore) -> None:
        await store.add("jane", "jane@example.com", is_active=False)
        with pytest.raises(InactiveUserError):
            await auth_service.login(
                None, schemas.LoginRequest(username="jane", password=PASSWORD)
            )

    @pytest.mark.asyncio
    async def test_refresh_rejects_deactivated_user(self, store: FakeUserStore) -> None:
        user = await store.add("jane", "jane@example.com")
        refresh, _ = tokens.create_refresh_token(user)
        user.is_active = False
        with pytest.raises(InactiveUserError):
            await auth_service.refresh(None, refresh)

    @pytest.mark.asyncio
    async def test_registration_disabled(
        self, store: FakeUserStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(settings.auth, "JWT_REGISTRATION_ENABLED", False)
        with pytest.raises(RegistrationDisabledError):
            await auth_service.register_user(
                None,
                schemas.RegisterRequest(
                    username="jane", email="jane@example.com", password=PASSWORD
                ),
            )

    @pytest.mark.asyncio
    async def test_rejected_when_not_jwt_mode(
        self, store: FakeUserStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(auth_service, "is_jwt_mode", lambda: False)
        with pytest.raises(AuthDisabledError):
            await auth_service.login(
                None, schemas.LoginRequest(username="jane", password=PASSWORD)
            )


class TestJwtEndpoints:
    """HTTP flow: register, login, me, refresh."""

    @pytest.mark.asyncio
    async def test_full_flow(self, client: AsyncClient) -> None:
        register = await client.post(
            "/auth/register",
            json={
                "username": "Jane.Doe",
                "email": "Jane@Example.com",
                "password": PASSWORD,
            },
        )
        assert register.status_code == 201
        body = register.json()
        assert body["username"] == "jane.doe"
        assert body["email"] == "jane@example.com"
        assert "password_hash" not in body

        login = await client.post(
            "/auth/login",
            json={"username": "JANE@example.com", "password": PASSWORD},
        )
        assert login.status_code == 200
        tokens_body = login.json()
        assert tokens_body["token_type"] == "Bearer"
        assert tokens_body["user"]["username"] == "jane.doe"

        me = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {tokens_body['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["id"] == body["id"]

        refreshed = await client.post(
            "/auth/refresh", json={"refresh_token": tokens_body["refresh_token"]}
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["access_token"]

    @pytest.mark.asyncio
    async def test_register_duplicate_returns_409(
        self, client: AsyncClient, store: FakeUserStore
    ) -> None:
        await store.add("jane", "jane@example.com")
        response = await client.post(
            "/auth/register",
            json={
                "username": "JANE",
                "email": "other@example.com",
                "password": PASSWORD,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["details"] == {"field": "username"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"username": "ab", "email": "a@b.co", "password": PASSWORD},
            {"username": "jane", "email": "not-an-email", "password": PASSWORD},
            {"username": "jane", "email": "a@b.co", "password": "short"},
        ],
    )
    async def test_register_validation(
        self, client: AsyncClient, payload: dict[str, str]
    ) -> None:
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, store: FakeUserStore
    ) -> None:
        await store.add("jane", "jane@example.com")
        response = await client.post(
            "/auth/login", json={"username": "jane", "password": "nope-nope"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["type"] == "InvalidCredentialsError"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_returns_401(
        self, client: AsyncClient, store: FakeUserStore
    ) -> None:
        user = await store.add("jane", "jane@example.com")
        access, _ = tokens.create_access_token(user, DEFAULT_ACCESS)
        response = await client.post("/auth/refresh", json={"refresh_token": access})
        assert response.status_code == 401


class TestProfileEndpoints:
    """GET/PATCH /auth/me/profile."""

    @staticmethod
    async def _auth_header(store: FakeUserStore) -> dict[str, str]:
        user = await store.add("jane", "jane@example.com")
        access, _ = tokens.create_access_token(user, DEFAULT_ACCESS)
        return {"Authorization": f"Bearer {access}"}

    @pytest.mark.asyncio
    async def test_empty_profile_by_default(
        self, client: AsyncClient, store: FakeUserStore
    ) -> None:
        headers = await self._auth_header(store)
        response = await client.get("/auth/me/profile", headers=headers)
        assert response.status_code == 200
        assert response.json()["phone_number"] is None

    @pytest.mark.asyncio
    async def test_partial_update_and_clear(
        self, client: AsyncClient, store: FakeUserStore
    ) -> None:
        headers = await self._auth_header(store)
        first = await client.patch(
            "/auth/me/profile",
            headers=headers,
            json={
                "phone_number": "+98 912 000 0000",
                "avatar_url": "https://cdn.example.com/a.png",
                "birth_date": "1990-04-21",
                "timezone": "Asia/Tehran",
            },
        )
        assert first.status_code == 200
        assert first.json()["avatar_url"] == "https://cdn.example.com/a.png"

        second = await client.patch(
            "/auth/me/profile",
            headers=headers,
            json={"bio": "Backend engineer", "phone_number": None},
        )
        body = second.json()
        assert body["bio"] == "Backend engineer"
        assert body["phone_number"] is None
        assert body["timezone"] == "Asia/Tehran"
        assert body["birth_date"] == "1990-04-21"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"timezone": "Mars/Olympus"},
            {"birth_date": "2999-01-01"},
            {"phone_number": "call me"},
            {"avatar_url": "not a url"},
            {"locale": "english!"},
        ],
    )
    async def test_invalid_update_returns_422(
        self, client: AsyncClient, store: FakeUserStore, payload: dict[str, str]
    ) -> None:
        headers = await self._auth_header(store)
        response = await client.patch("/auth/me/profile", headers=headers, json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_requires_token(self, client: AsyncClient) -> None:
        response = await client.get("/auth/me/profile")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_and_remove_avatar(
        self,
        client: AsyncClient,
        store: FakeUserStore,
        tmp_path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from apps.auth.jwt.utils import avatars

        monkeypatch.setattr(avatars, "avatar_directory", lambda: tmp_path)
        headers = await self._auth_header(store)
        png = b"\x89PNG\r\n\x1a\n" + b"x" * 16
        uploaded = await client.post(
            "/auth/me/avatar",
            headers=headers,
            files={"file": ("photo.png", png, "image/png")},
        )
        assert uploaded.status_code == 200
        avatar_url = uploaded.json()["avatar_url"]
        assert "/auth/avatars/" in avatar_url
        assert avatar_url.endswith(".png") or ".png?" in avatar_url

        filename = avatar_url.rsplit("/", 1)[-1].split("?", 1)[0]
        image = await client.get(f"/auth/avatars/{filename}")
        assert image.status_code == 200
        assert image.content.startswith(b"\x89PNG")
        assert image.headers["cross-origin-resource-policy"] == "cross-origin"

        removed = await client.delete("/auth/me/avatar", headers=headers)
        assert removed.status_code == 200
        assert removed.json()["avatar_url"] is None
        assert (await client.get(f"/auth/avatars/{filename}")).status_code == 404


class TestModeDispatch:
    """Shared ``get_current_user`` picks the provider from ``auth.MODE``."""

    @pytest.mark.asyncio
    async def test_jwt_mode_accepts_local_token(
        self, store: FakeUserStore, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(auth_dependencies, "is_auth_enabled", lambda: True)
        monkeypatch.setattr(auth_dependencies, "get_auth_mode", lambda: AuthMode.JWT)
        user = await store.add("jane", "jane@example.com")
        access, _ = tokens.create_access_token(user, DEFAULT_ACCESS)
        request = SimpleNamespace(client=None)

        info = await auth_dependencies.get_current_user(request, f"Bearer {access}")

        assert info.id == user.id

    @pytest.mark.asyncio
    async def test_jwt_mode_rejects_garbage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(auth_dependencies, "is_auth_enabled", lambda: True)
        monkeypatch.setattr(auth_dependencies, "get_auth_mode", lambda: AuthMode.JWT)
        with pytest.raises(UnauthorizedError):
            await auth_dependencies.get_current_user(
                SimpleNamespace(client=None), "Bearer not.a.jwt"
            )

    @pytest.mark.asyncio
    async def test_sso_mode_uses_keycloak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sentinel = object()

        async def fake_keycloak(request: object, authorization: str | None) -> object:
            return sentinel

        monkeypatch.setattr(auth_dependencies, "is_auth_enabled", lambda: True)
        monkeypatch.setattr(auth_dependencies, "get_auth_mode", lambda: AuthMode.SSO)
        monkeypatch.setattr(
            auth_dependencies.keycloak_auth, "get_current_user", fake_keycloak
        )
        result = await auth_dependencies.get_current_user(
            SimpleNamespace(client=None), "Bearer x"
        )
        assert result is sentinel

    @pytest.mark.asyncio
    async def test_auth_disabled_returns_synthetic_user(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(auth_dependencies, "is_auth_enabled", lambda: False)
        info = await auth_dependencies.get_current_user(
            SimpleNamespace(client=None), None
        )
        assert info.id == "auth:disabled"
