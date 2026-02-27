"""
配置 API 端点

提供前端所需的配置信息，确保前后端配置同步。
"""

from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("", summary="获取系统配置")
async def get_config():
    """
    获取系统配置

    返回前端所需的配置信息，包括：
    - 元对话配置（关键词列表、启用状态）
    """
    from config import settings

    try:
        meta_cfg = settings.turing.meta_conversation
        return {
            "meta_conversation": {
                "enabled": meta_cfg.enabled,
                "keywords": meta_cfg.keywords,
            }
        }
    except Exception as e:
        logger.error(f"获取配置失败：{e}")
        # 返回默认配置，确保前端不崩溃
        return {
            "meta_conversation": {
                "enabled": True,
                "keywords": ['真人', '机器', 'AI', '机器人', '人工智能', '程序', '算法'],
            }
        }
