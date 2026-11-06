"""Router definitions for authentication endpoints.

This module aggregates all authentication endpoint routers.

API versioning: Auth is treated as internal-only; per api-versioning rule,
internal endpoints may omit URI versioning (no /v1/ prefix). If auth is
exposed as a public API in the future, add URI versioning (e.g. /v1/auth).
"""

from fastapi import APIRouter

from . import groups, identities, login, logout, me, refresh, roles, users

router = APIRouter()

# Include all endpoint routers
router.include_router(login.router)
router.include_router(me.router)
router.include_router(identities.router)
router.include_router(users.router)
router.include_router(groups.router)
router.include_router(roles.router)
router.include_router(refresh.router)
router.include_router(logout.router)
