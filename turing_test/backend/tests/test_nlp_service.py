"""
共享 NLP 服务测试

测试 SharedNLPService 的基本功能。
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from services.nlp_service import get_nlp_service, reset_nlp_service
from loguru import logger


def test_nlp_service():
    """测试 NLP 服务"""
    logger.info("=" * 50)
    logger.info("开始测试共享 NLP 服务")
    logger.info("=" * 50)

    # 获取服务实例
    nlp_service = get_nlp_service()

    # 测试分词
    logger.info("\n1. 测试分词功能")
    test_text = "我喜欢吃苹果"
    words = nlp_service.segment(test_text)
    logger.info(f"输入: {test_text}")
    logger.info(f"分词结果: {words}")

    # 测试缓存（第二次调用应该更快）
    logger.info("\n2. 测试缓存功能")
    words_cached = nlp_service.segment(test_text)
    logger.info(f"缓存命中结果: {words_cached}")

    # 获取缓存统计
    cache_stats = nlp_service.get_cache_stats()
    logger.info(f"缓存统计: {cache_stats}")

    # 测试命名实体识别
    logger.info("\n3. 测试命名实体识别")
    test_text2 = "张三在北京工作"
    entities = nlp_service.get_entities(test_text2)
    logger.info(f"输入: {test_text2}")
    logger.info(f"实体识别结果: {entities}")

    # 测试词性标注
    logger.info("\n4. 测试词性标注")
    test_text3 = "我喜欢学习自然语言处理"
    pos_tags = nlp_service.get_pos_tags(test_text3)
    logger.info(f"输入: {test_text3}")
    logger.info(f"词性标注结果: {pos_tags}")

    # 测试句法分析
    logger.info("\n5. 测试句法分析")
    syntax_info = nlp_service.analyze_syntax(test_text3)
    logger.info(f"输入: {test_text3}")
    logger.info(f"句法分析结果:")
    logger.info(f"  - 分词: {syntax_info['cws']}")
    logger.info(f"  - 词性: {syntax_info['pos']}")
    logger.info(f"  - 依存: {syntax_info['dep']}")

    # 获取服务状态
    logger.info("\n6. 服务状态")
    status = nlp_service.get_status()
    logger.info(f"NLP 服务状态: {status}")

    logger.info("\n" + "=" * 50)
    logger.info("测试完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    test_nlp_service()
