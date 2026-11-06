"""Router aggregating local JWT authentication and admin endpoints."""

from fastapi import APIRouter

from . import (
    admin_groups,
    admin_permissions,
    admin_roles,
    admin_users,
    login,
    me,
    profile,
    refresh,
    register,
)

router = APIRouter()

router.include_router(register.router)
router.include_router(login.router)
router.include_router(refresh.router)
router.include_router(me.router)
router.include_router(profile.router)

router.include_router(admin_permissions.router)
router.include_router(admin_roles.router)
router.include_router(admin_groups.router)
router.include_router(admin_users.router)
