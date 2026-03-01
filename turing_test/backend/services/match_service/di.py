"""
匹配服务依赖注入

提供 FastAPI 依赖注入函数，从 app.state 获取匹配服务实例。
"""

from typing import Annotated
from fastapi import Depends, Request
from loguru import logger

# 直接从一个 service 模块导入，避免循环依赖
from turing_test.backend.services.match_service.service import MatchService


async def get_match_service(request: Request) -> MatchService:
    """
    从 app.state 获取匹配服务实例

    使用方式:
        @router.post("/join")
        async def join(
            match_service: Annotated[MatchService, Depends(get_match_service)]
        ):
            ...
    """
    service = getattr(request.app.state, "match_service", None)
    if service is None:
        logger.error("匹配服务未初始化，请在 main.py 的 lifespan 中初始化")
        raise RuntimeError("匹配服务未初始化")
    return service


# 类型别名，简化使用
MatchServiceDep = Annotated[MatchService, Depends(get_match_service)]
