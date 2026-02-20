#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice 统一配置文件

集中管理所有配置项，包括：
- 路径配置
- 魔法数字（常量）
- 功能开关

配置加载说明:
- 代词映射和句式转换规则存储在 scripts/mapping.yaml
- 语义标签存储在 scripts/semantic_tags.yaml
- 由各自模块负责加载（如 SyntaxReassembly、语义分析模块等）
"""

from pathlib import Path


# =============================================================================
# 路径配置
# =============================================================================

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# Alice 模块目录
ALICE_DIR = Path(__file__).parent

# 脚本配置文件目录
SCRIPTS_DIR = ALICE_DIR / "scripts"

# 默认脚本文件路径（YAML 格式）
DEFAULT_SCRIPT_FILE = SCRIPTS_DIR / "curiosity_scripts.yaml"

# 默认反射规则文件路径（YAML 格式，包含代词映射和句式转换规则）
DEFAULT_RULES_FILE = SCRIPTS_DIR / "mapping.yaml"

# 语义标签文件
SEMANTIC_TAGS_FILE = SCRIPTS_DIR / "semantic_tags.yaml"


# =============================================================================
# 对话上下文配置（魔法数字）
# =============================================================================

# 上下文管理器最大条目数
CONTEXT_MAX_ITEMS = 10

# 对话历史最大轮数
CONVERSATION_HISTORY_MAX_TURNS = 20

# LTP 缓存大小限制
LTP_CACHE_SIZE_LIMIT = 100

# 对话日志最大保存条数
DIALOGUE_LOG_MAX_ENTRIES = 1000

# 性能监控采样率 (0.0 - 1.0)
PERFORMANCE_MONITOR_SAMPLE_RATE = 1.0


# =============================================================================
# 功能开关
# =============================================================================

# 分词策略:
# - 仅使用分词功能时：使用 jieba
# - 使用高级功能（句法分析、命名实体识别）时：使用 LTP（分词也顺便用 LTP 来做）

# 是否默认启用 LTP 句法分析
ENABLE_LTP_BY_DEFAULT = True

# 是否默认启用 NER 实体识别
ENABLE_NER_BY_DEFAULT = True

# 是否默认启用对话日志
ENABLE_LOGGING_BY_DEFAULT = True

# NER 是否使用 LTP 增强
NER_USE_LTP_BY_DEFAULT = True


# =============================================================================
# LTP 任务启用开关
# =============================================================================

# 词分词 (Chinese Word Segmentation)
LTP_ENABLE_CWS = True

# 词性标注 (Part-of-Speech tagging)
LTP_ENABLE_POS = True

# 命名实体识别 (Named Entity Recognition)
LTP_ENABLE_NER = True

# 依存句法分析 (Dependency Parsing)
LTP_ENABLE_DEP = True

# 语义依存分析 (Semantic Dependency Parsing)，默认关闭
LTP_ENABLE_SDP = False

# 语义角色标注 (Semantic Role Labeling)，默认关闭
LTP_ENABLE_SRL = False


# =============================================================================
# 预定义响应配置
# =============================================================================

# 无匹配时的默认响应
FALLBACK_RESPONSES = [
    "嗯，我明白了。",
    "能再多说一些吗？",
    "这很有趣，继续说。",
    "我理解你的感受。",
    "为什么会这样呢？",
]

# 问候语响应
GREETING_RESPONSES = [
    "你好！有什么可以帮你的吗？",
    "嗨！今天过得怎么样？",
    "你好！想聊些什么呢？",
]


# =============================================================================
# 性能优化配置
# =============================================================================

# LTP 模型缓存大小（缓存分析结果数量）
LTP_CACHE_SIZE = 50

# 文本预处理最大长度（超过此长度的文本会被截断）
MAX_INPUT_LENGTH = 500

# 正则表达式编译缓存大小
REGEX_CACHE_SIZE = 100

# 脚本匹配超时时间（毫秒）
SCRIPT_MATCH_TIMEOUT = 100


# =============================================================================
# 日志配置
# =============================================================================

# 日志文件目录
LOG_DIR = PROJECT_ROOT / "logs"

# 日志文件最大大小（MB）
LOG_MAX_SIZE_MB = 10

# 日志文件备份数量
LOG_BACKUP_COUNT = 5

# 日志级别
LOG_LEVEL = "INFO"
