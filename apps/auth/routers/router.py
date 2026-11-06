"""Auth router: mounts the provider selected by ``auth.MODE`` under ``/auth``.

- ``sso``: Keycloak login/OTP, refresh, logout, me, and identity admin endpoints.
- ``jwt``: local register, login, refresh, and me.

Auth is internal-only, so it is not URI-versioned (see api-versioning rule).
"""

from fastapi import APIRouter

from ..config import AuthMode, get_auth_mode

router = APIRouter()

if get_auth_mode() is AuthMode.JWT:
    from ..jwt.routers.router import router as provider_router
else:
    from ..keycloak.routers.router import router as provider_router

router.include_router(provider_router)
