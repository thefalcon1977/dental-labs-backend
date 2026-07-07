"""Main auth router."""

from fastapi import APIRouter

from .login import router as login_router
from .user import router as user_router

router = APIRouter()
router.include_router(login_router)
router.include_router(user_router)

__all__ = ["router"]
