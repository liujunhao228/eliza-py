"""
API 路由包

导出所有路由模块。
"""

from .auth import router as auth_router
from .user import router as user_router
from .match import router as match_router

__all__ = [
    "auth_router",
    "user_router",
    "match_router",
]
