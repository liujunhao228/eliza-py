"""
服务层包

导出所有服务模块。
"""

from .nlp_service import (
    SharedNLPService,
    get_nlp_service,
    reset_nlp_service,
)

__all__ = [
    "SharedNLPService",
    "get_nlp_service",
    "reset_nlp_service",
]
