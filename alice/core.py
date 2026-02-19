#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice - 好奇的朋友聊天机器人核心模块
基于 ELIZA 原理，采用轻量化设计实现中文对话
"""

import logging
import os
import re
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 导入统一配置
from alice.config import (
    PRONOUN_MAPPING,
    TRANSFORMATION_RULES,
    CONTEXT_MAX_ITEMS,
    CONVERSATION_HISTORY_MAX_TURNS,
    DEFAULT_SCRIPT_FILE,
    DEFAULT_RULES_FILE,
    LTP_SCRIPT_FILE,
    ENABLE_LTP_BY_DEFAULT,
    ENABLE_NER_BY_DEFAULT,
    NER_USE_LTP_BY_DEFAULT,
    ENABLE_LOGGING_BY_DEFAULT,
    MAX_INPUT_LENGTH,
)

# 导入自定义异常类
from alice.exceptions import (
    ConfigurationError,
    MissingConfigurationError,
    InvalidConfigurationError,
    InitializationError,
    DependencyError,
    DialogueError,
    InputValidationError,
    ScriptMatchingError,
    ResponseGenerationError,
    TextProcessingError,
    ExternalLibraryError,
    LTPError,
    JiebaError,
)

# 导入降级监控器
from alice.utils.degradation_monitor import degradation_monitor

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    # 使用 logger 而非 print
    logger = logging.getLogger(__name__)
    logger.warning("jieba 未安装，将使用基础分词模式")

# 导入日志和性能监控模块
try:
    from alice.utils.logger import DialogueLogger
    from alice.utils.performance import PerformanceMonitor
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("日志模块未安装，将禁用日志功能")

# 导入重组引擎模块
try:
    from alice.utils.reassembly import ReassemblyEngine, DecompositionMatcher, ReassemblyRuleSelector
    REASSEMBLY_AVAILABLE = True
except ImportError:
    REASSEMBLY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("重组引擎模块未找到，部分功能可能不可用")
    degradation_monitor.register_degradation(
        component='reassembly_engine',
        reason='模块导入失败',
        severity=2,
        recovery_plan='使用基础响应模式'
    )

# 导入 LTP 句法分析器模块
try:
    from alice.utils.ltp_parser import LTPParser, SyntaxBasedReassemblyEngine
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("LTP 模块未安装，将使用简化句法分析模式")
    degradation_monitor.register_degradation(
        component='ltp_parser',
        reason='模块导入失败',
        severity=2,
        recovery_plan='使用简化句法分析模式'
    )

# 导入通用脚本引擎模块（必需）
from alice.utils.script_engine import ScriptEngine, ScriptMatch


from alice.utils.context import ContextManager, ConversationHistory

# 导入 NER 模块
try:
    from alice.utils.ner import (
        RuleBasedNER,
        LTPBasedNER,
        extract_entities,
        extract_entities_as_tuples,
        extract_entities_as_dict,
        Entity,
        EntityType
    )
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("NER 模块未找到，将使用基础实体提取")
    degradation_monitor.register_degradation(
        component='ner_module',
        reason='模块导入失败',
        severity=2,
        recovery_plan='使用基础实体提取'
    )

# 模块级 logger
logger = logging.getLogger(__name__)


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self):
        # 中文标点符号映射（全角转半角）
        self.punctuation_map = {
            '，': ',', '。': '.', '！': '!', '？': '?',
            '；': ';', '：': ':', '"': '"', "'": "'",
            '、': ',', '「': '"', '」': '"', '『': '"', '』': '"'
        }
        # 全角转半角映射
        self.fullwidth_map = {
            chr(0xFF01 + i): chr(0x21 + i) for i in range(94)  # 标点
        }
        self.fullwidth_map[' '] = ' '
        self.fullwidth_map['。'] = '.'

    def standardize_text(self, text: str) -> str:
        """文本标准化"""
        # 全角转半角
        for full, half in self.fullwidth_map.items():
            text = text.replace(full, half)
        # 统一标点符号
        for full, half in self.punctuation_map.items():
            text = text.replace(full, half)
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def segment_text(self, text: str) -> List[str]:
        """中文分词"""
        if JIEBA_AVAILABLE:
            return list(jieba.cut(text))
        else:
            # 基础分词：按字符分割
            return list(text)


class SemanticAnalyzer:
    """语义分析器（增强版 - 集成 NER）"""

    def __init__(self, use_ner: bool = True, use_ltp: bool = False):
        """
        初始化语义分析器

        Args:
            use_ner: 是否使用 NER 模块
            use_ltp: 是否使用 LTP 增强 NER
        """
        self.preprocessor = TextPreprocessor()
        # 情感词库（简化版）
        self.positive_words = {
            '好', '棒', '喜欢', '开心', '高兴', '快乐', '幸福', '满意',
            '爱', '美好', '顺利', '成功', '优秀', '赞美', '感谢'
        }
        self.negative_words = {
            '坏', '差', '讨厌', '难过', '生气', '焦虑', '痛苦', '失望',
            '恨', '烦恼', '压力', '累', '困', '烦', '糟糕', '失败'
        }
        # 意图关键词映射
        self.intent_keywords = {
            'narrative': ['去', '做', '看', '买', '发生', '出现', '开始', '结束'],
            'emotion': ['感觉', '觉得', '心情', '情绪', '感受'],
            'person': ['朋友', '家人', '同事', '同学', '老师', '老板'],
            'relationship': ['关系', '相处', '吵架', '矛盾', '误会'],
            'question': ['为什么', '怎么', '如何', '什么', '哪里', '何时']
        }

        # NER 模块
        self.use_ner = use_ner and NER_AVAILABLE
        self.use_ltp = use_ltp
        self.ner = None
        if self.use_ner:
            try:
                if self.use_ltp:
                    self.ner = LTPBasedNER()
                    self.ner.initialize_ltp()
                else:
                    self.ner = RuleBasedNER()
            except Exception as e:
                print(f"NER 初始化失败：{e}，将使用基础实体提取")
                self.use_ner = False

    def analyze(self, text: str) -> Dict:
        """分析文本语义"""
        words = self.preprocessor.segment_text(text)

        analysis = {
            'tokens': words,
            'sentiment': self._analyze_sentiment(words),
            'intent': self._detect_intent(words),
            'entities': self._extract_entities(words, text),
            'original_text': text
        }
        return analysis

    def _analyze_sentiment(self, tokens: List[str]) -> float:
        """简单情感分析"""
        pos_count = sum(1 for token in tokens if any(pw in token for pw in self.positive_words))
        neg_count = sum(1 for token in tokens if any(nw in token for nw in self.negative_words))

        if pos_count + neg_count == 0:
            return 0.0
        return (pos_count - neg_count) / (pos_count + neg_count)

    def _detect_intent(self, tokens: List[str]) -> str:
        """意图检测"""
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            # 改进：检查 tokens 中是否包含关键词或其子串
            score = sum(1 for token in tokens if any(kw in token for kw in keywords))
            intent_scores[intent] = score

        # 返回得分最高的意图
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        return 'general'

    def _extract_entities(self, tokens: List[str], text: str) -> List[Tuple[str, str]]:
        """
        提取关键实体（增强版 - 使用 NER）

        Args:
            tokens: 分词结果
            text: 原始文本

        Returns:
            实体列表 [(类型，文本), ...]
        """
        if self.use_ner and self.ner:
            # 使用 NER 模块提取实体
            entities = self.ner.extract(text)
            return [e.to_tuple() for e in entities]
        else:
            # 回退到基础实体提取
            return self._extract_entities_basic(tokens, text)

    def _extract_entities_basic(self, tokens: List[str], text: str) -> List[Tuple[str, str]]:
        """
        基础实体提取（回退方案）

        Args:
            tokens: 分词结果
            text: 原始文本

        Returns:
            实体列表
        """
        entities = []
        # 人称代词
        pronouns = ['我', '你', '他', '她', '它', '我们', '你们', '他们', '她们']
        for pronoun in pronouns:
            if pronoun in tokens:
                entities.append(('pronoun', pronoun))

        # 时间词
        time_words = ['今天', '昨天', '明天', '刚才', '最近', '上周', '下周']
        for tw in time_words:
            if tw in tokens:
                entities.append(('time', tw))

        return entities


class ReflectionEngine:
    """反射转换引擎（增强版 - 支持重组规则）"""

    def __init__(self, rules_file: Optional[str] = None):
        # 代词映射表（从统一配置加载）
        self.pronoun_mapping = dict(PRONOUN_MAPPING)
        self.transformation_rules = []
        self._load_rules(rules_file)

    def _load_rules(self, rules_file: Optional[str]):
        """从配置文件加载规则

        严禁回退：规则文件必须存在且有效，否则抛出异常。
        """
        if not rules_file:
            raise MissingConfigurationError("规则文件路径不能为空")

        if not os.path.exists(rules_file):
            raise MissingConfigurationError(f"规则文件不存在：{rules_file}")

        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.pronoun_mapping = config.get('pronoun_mapping', {})
                self.transformation_rules = [
                    (pattern, replacement)
                    for pattern, replacement in config.get('transformation_rules', [])
                ]
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(f"规则文件 JSON 格式无效：{rules_file} - {e}") from e
        except IOError as e:
            raise ConfigurationError(f"无法读取规则文件：{rules_file}") from e

    def transform(self, text: str, semantic_info: Optional[Dict] = None) -> str:
        """执行反射转换"""
        # 1. 应用代词映射（按长度排序，优先匹配长的）
        transformed = text
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)

        # 2. 应用句式转换规则
        for pattern, replacement in self.transformation_rules:
            match = re.search(pattern, transformed)
            if match:
                transformed = re.sub(pattern, replacement, transformed)
                break

        return transformed

    def transform_with_reassembly(self, text: str, components: List[str],
                                   reassembly_rule: str) -> str:
        """
        使用重组规则执行反射转换

        参数:
            text: 原始文本
            components: 分解组件列表
            reassembly_rule: 重组规则（支持 {1}, {2} 等占位符）

        返回:
            转换后的响应
        """
        # 1. 先应用代词映射到组件
        transformed_components = [
            self._apply_pronoun_mapping(comp) for comp in components
        ]

        # 2. 应用重组规则
        response = reassembly_rule
        for i, comp in enumerate(transformed_components, 1):
            placeholder = f'{{{i}}}'
            response = response.replace(placeholder, comp.strip() if comp else '')

        # 3. 清理未匹配的占位符
        response = re.sub(r'\{\d+\}', '', response)

        return response.strip()

    def _apply_pronoun_mapping(self, text: str) -> str:
        """应用代词映射"""
        transformed = text
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)
        return transformed


class CuriosityScriptEngine:
    """
    好奇心脚本引擎 - 基于通用 ScriptEngine 的封装（优化版 - 按需使用LTP）

    新增特性：
    - LTP按需加载：只在检测到需要句法分析时才初始化LTP
    - 性能监控：跟踪LTP使用频率和性能影响
    - 智能降级：LTP不可用时无缝切换到简化模式
    """

    def __init__(self, script_file: Optional[str] = None,
                 rules_file: Optional[str] = None,
                 enable_ltp: bool = False):
        """
        初始化好奇心脚本引擎

        参数:
            script_file: 脚本配置文件路径
            rules_file: 反射规则文件路径（用于代词映射）
            enable_ltp: 是否启用 LTP 句法分析（按需模式）
        """
        self.script_file = script_file
        self.rules_file = rules_file
        self.enable_ltp = enable_ltp

        # 脚本引擎是必需模块，直接初始化
        self.engine = ScriptEngine(script_file=script_file)

        self.script_history: Dict[str, int] = {}
        self.last_used_responses: Dict[str, str] = {}

        # 重组引擎（必需）
        if rules_file:
            self.reassembly_engine = ReassemblyEngine(rules_file)
        else:
            self.reassembly_engine = ReassemblyEngine()

        # LTP 相关组件（按需初始化）
        self.ltp_parser = None
        self.syntax_reassembly_engine = None
        self.ltp_initialized = False
        self.ltp_usage_stats = {
            'attempts': 0,
            'successes': 0,
            'failures': 0,
            'fallback_to_simple': 0,
            'skipped_for_simple': 0
        }

    def _initialize_ltp_if_needed(self) -> bool:
        """
        按需初始化 LTP 模型
        
        返回:
            是否成功初始化 LTP
        """
        if self.ltp_initialized:
            return self.ltp_parser is not None
            
        if not self.enable_ltp or not LTP_AVAILABLE:
            self.ltp_initialized = True
            return False

        try:
            # 使用优化版LTP解析器
            from alice.utils.ltp_parser import OptimizedLTPParser
            self.ltp_parser = OptimizedLTPParser(lazy_load=True)
            self.syntax_reassembly_engine = SyntaxBasedReassemblyEngine(self.ltp_parser)
            self.ltp_initialized = True
            logger.info("LTP 模型按需加载成功")
            return True
        except Exception as e:
            logger.error(f"LTP 初始化失败：{e}")
            # 注册降级事件
            degradation_monitor.register_degradation(
                component='ltp_init',
                reason=str(e),
                severity=3,
                recovery_plan='使用简化句法分析模式'
            )
            self.ltp_parser = None
            self.syntax_reassembly_engine = None
            self.ltp_initialized = True
            return False

    def _should_use_syntax_analysis(self, match, text: str) -> bool:
        """
        判断是否需要使用句法分析
        
        参数:
            match: 脚本匹配结果
            text: 原始文本
            
        返回:
            是否需要句法分析
        """
        if not self.enable_ltp:
            return False
            
        # 首先检查内容复杂度
        if self.ltp_parser and not self.ltp_parser.should_use_ltp(text):
            self.ltp_usage_stats['skipped_for_simple'] += 1
            return False
            
        # 检查脚本是否包含句法相关配置
        script_data = self.engine.scripts.get(match.script_id, {})
        
        # 有句法触发规则
        if script_data.get('syntax_triggers'):
            return True
            
        # 有句法重组规则（包含 {SUBJ}, {PRED}, {OBJ} 等占位符）
        reassembly_rules = match.reassembly_rules or []
        syntax_placeholders = ['{SUBJ}', '{PRED}', '{OBJ}', '{ATT}', '{ADV}']
        for rule in reassembly_rules:
            if any(placeholder in rule for placeholder in syntax_placeholders):
                return True
                
        return False

    def match_script(self, text: str, semantic_info: Dict) -> Optional[str]:
        """
        匹配合适的脚本并生成响应

        匹配流程:
        1. 使用 ScriptEngine 匹配脚本
        2. 检查是否需要句法分析
        3. 如需要则按需初始化 LTP
        4. 优先使用重组规则生成响应
        5. 如果重组失败，使用预定义响应

        参数:
            text: 待匹配的文本
            semantic_info: 语义分析结果

        返回:
            生成的响应，无匹配返回 None
        """
        # 1. 使用通用脚本引擎匹配
        match = self.engine.match(text)
        if not match:
            return None

        # 2. 判断是否需要句法分析
        needs_syntax = self._should_use_syntax_analysis(match, text)
        
        # 3. 如需要则按需初始化 LTP
        if needs_syntax:
            self.ltp_usage_stats['attempts'] += 1
            ltp_available = self._initialize_ltp_if_needed()
            if not ltp_available:
                self.ltp_usage_stats['fallback_to_simple'] += 1

        # 4. 生成响应：优先使用重组规则
        response = self._generate_response(match, semantic_info, needs_syntax)

        # 5. 更新历史记录
        self.script_history = self.engine.get_usage_statistics()
        if match.script_id and response:
            self.last_used_responses[match.script_id] = response

        return response

    def _generate_response(self, match, semantic_info: Dict, needs_syntax: bool) -> Optional[str]:
        """
        生成响应：优先使用重组规则，支持按需 LTP 句法分析

        参数:
            match: 脚本匹配结果
            semantic_info: 语义分析结果
            needs_syntax: 是否需要句法分析

        返回:
            生成的响应
        """
        response = None

        # 如果需要句法分析且 LTP 可用，尝试使用句法重组
        if needs_syntax and self.ltp_parser and self.syntax_reassembly_engine:
            try:
                response = self._apply_syntax_reassembly(match, semantic_info)
                if response:
                    self.ltp_usage_stats['successes'] += 1
                else:
                    self.ltp_usage_stats['failures'] += 1
            except Exception as e:
                print(f"LTP 句法分析失败：{e}")
                self.ltp_usage_stats['failures'] += 1
                response = None

        # 如果句法重组失败或不需要句法分析，使用普通重组规则
        if response is None and match.reassembly_rules and match.components:
            response = self._apply_reassembly(match)

        # 如果重组失败，使用预定义响应
        if response is None and match.responses:
            response = self._select_response(match)

        return response

    def _apply_syntax_reassembly(self, match, semantic_info: Dict) -> Optional[str]:
        """
        应用 LTP 句法分析进行重组

        参数:
            match: 脚本匹配结果
            semantic_info: 语义分析结果

        返回:
            重组后的响应
        """
        if not self.syntax_reassembly_engine:
            return None

        # 获取句法分析结果
        text = semantic_info.get('original_text', '')
        syntax_structure = self.ltp_parser.get_main_structure(text) if text else {}

        # 检查脚本是否有句法触发规则
        script_data = self.engine.scripts.get(match.script_id, {})
        syntax_triggers = script_data.get('syntax_triggers', {}).get('rules', [])

        # 如果有句法触发规则，检查是否满足条件
        if syntax_triggers:
            for trigger in syntax_triggers:
                if self._check_syntax_trigger(syntax_structure, trigger):
                    templates = trigger.get('response_templates', [])
                    if templates:
                        import random
                        template = random.choice(templates)
                        response = self.syntax_reassembly_engine.reassemble_with_syntax(
                            text, template
                        )
                        if response and response.strip():
                            return response

        # 如果没有句法触发或触发失败，尝试使用普通句法重组
        if match.reassembly_rules:
            for rule in match.reassembly_rules:
                response = self.syntax_reassembly_engine.reassemble_with_syntax(text, rule)
                if response and response.strip():
                    return response

        return None

    def _check_syntax_trigger(self, syntax_structure: Dict, trigger: Dict) -> bool:
        """
        检查句法触发条件是否满足

        参数:
            syntax_structure: 句法分析结果
            trigger: 触发条件

        返回:
            是否满足触发条件
        """
        if not syntax_structure or not trigger:
            return False

        # 检查谓语触发
        if 'predicate' in trigger:
            pred_list = trigger['predicate']
            if syntax_structure.get('predicate', '') not in pred_list:
                return False

        # 检查主语人称触发
        if trigger.get('subject_person', False):
            subj = syntax_structure.get('subject', '')
            if not any(p in subj for p in ['他', '她', '我', '你', '朋友', '同事', '家人']):
                return False

        # 检查情感谓语触发
        if 'predicate_emotion' in trigger:
            pred = syntax_structure.get('predicate', '')
            if pred not in trigger['predicate_emotion']:
                return False

        # 检查情感宾语触发
        if 'object_emotion' in trigger:
            obj = syntax_structure.get('object', '')
            if not any(e in obj for e in trigger['object_emotion']):
                return False

        # 检查程度副词触发
        if 'adverbial_degree' in trigger:
            # 需要从完整句法结构中获取状语
            pass  # 简化处理，暂时跳过

        return True

    def _apply_reassembly(self, match) -> Optional[str]:
        """
        应用重组规则生成响应

        参数:
            match: 脚本匹配结果

        返回:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None

        # 选择重组规则（避免重复）
        rules = match.reassembly_rules
        selected_rule = self._select_reassembly_rule(rules, match.script_id)
        if not selected_rule:
            return None

        # 使用重组引擎生成响应
        response = self.reassembly_engine.reassemble(
            components=match.components,
            reassembly_rule=selected_rule,
            apply_pronoun_mapping=True
        )

        return response.strip() if response else None

    def _select_reassembly_rule(self, rules: List[str], script_id: str) -> Optional[str]:
        """
        选择重组规则（避免重复）

        参数:
            rules: 重组规则列表
            script_id: 脚本 ID

        返回:
            选中的规则
        """
        if not rules:
            return None

        last_rule = self.last_used_responses.get(f"{script_id}_rule", '')
        available_rules = [r for r in rules if r != last_rule]

        if available_rules:
            selected = random.choice(available_rules)
        else:
            selected = random.choice(rules)

        self.last_used_responses[f"{script_id}_rule"] = selected
        return selected

    def _select_response(self, match) -> Optional[str]:
        """
        从预定义响应中选择

        参数:
            match: 脚本匹配结果

        返回:
            选中的响应
        """
        if not match.responses:
            return None

        last_response = self.last_used_responses.get(match.script_id, '')
        available_responses = [r for r in match.responses if r != last_response]

        if available_responses:
            selected = random.choice(available_responses)
        else:
            selected = random.choice(match.responses)

        return selected

    def get_ltp_stats(self) -> Dict:
        """获取 LTP 使用统计信息"""
        stats = self.ltp_usage_stats.copy()
        if self.ltp_parser:
            cache_stats = self.ltp_parser.get_cache_stats()
            stats.update(cache_stats)
        return stats

    def reset(self) -> None:
        """重置引擎状态"""
        self.engine.reset()
        self.script_history.clear()
        self.last_used_responses.clear()
        self.ltp_usage_stats = {
            'attempts': 0,
            'successes': 0,
            'failures': 0,
            'fallback_to_simple': 0,
            'skipped_for_simple': 0
        }
        # 清空LTP缓存
        if self.ltp_parser:
            self.ltp_parser.clear_cache()


class AliceBot:
    """Alice 聊天机器人（支持 LTP 依存句法分析和 NER 实体识别）"""

    def __init__(self, script_file: Optional[str] = None,
                 rules_file: Optional[str] = None,
                 enable_logging: bool = False,
                 enable_ltp: bool = False,
                 enable_ner: bool = True,
                 ner_use_ltp: bool = False):
        """
        初始化 Alice 机器人

        参数:
            script_file: 脚本配置文件路径
            rules_file: 反射规则文件路径
            enable_logging: 是否启用日志
            enable_ltp: 是否启用 LTP 句法分析
            enable_ner: 是否启用 NER 实体识别
            ner_use_ltp: NER 是否使用 LTP 增强
        """
        # 确定脚本文件路径
        if script_file is None:
            default_scripts = DEFAULT_SCRIPT_FILE
            if default_scripts.exists():
                script_file = str(default_scripts)

        # 确定规则文件路径
        if rules_file is None:
            # 使用默认路径
            default_rules = DEFAULT_RULES_FILE
            if default_rules.exists():
                rules_file = str(default_rules)

        self.preprocessor = TextPreprocessor()
        self.analyzer = SemanticAnalyzer(use_ner=enable_ner, use_ltp=ner_use_ltp)
        self.reflection_engine = ReflectionEngine(rules_file)

        # 根据是否启用 LTP 选择脚本引擎
        if enable_ltp:
            # 尝试使用 LTP 增强脚本
            ltp_script_file = LTP_SCRIPT_FILE
            if ltp_script_file.exists():
                script_file = str(ltp_script_file)
            self.script_engine = CuriosityScriptEngine(script_file, rules_file, enable_ltp=True)
        else:
            self.script_engine = CuriosityScriptEngine(script_file, rules_file, enable_ltp=False)

        # 使用 ContextManager 替代简化的 DialogueContext
        self.context_manager = ContextManager(max_items=CONTEXT_MAX_ITEMS)
        self.conversation_history = ConversationHistory(max_turns=CONVERSATION_HISTORY_MAX_TURNS)

        # 日志和性能监控（可选）
        self.enable_logging = enable_logging
        if enable_logging and LOGGING_AVAILABLE:
            self.dialogue_logger = DialogueLogger()
            self.perf_monitor = PerformanceMonitor()
        else:
            self.dialogue_logger = None
            self.perf_monitor = None

        # NER 状态
        self.ner_enabled = enable_ner and NER_AVAILABLE

    def respond(self, user_input: str) -> str:
        """
        生成回复

        Args:
            user_input: 用户输入

        Returns:
            机器人回复

        Raises:
            InputValidationError: 输入验证失败
            ScriptMatchingError: 脚本匹配失败
            ResponseGenerationError: 响应生成失败
        """
        # 1. 输入验证（禁止降级）
        if not user_input or not user_input.strip():
            raise InputValidationError("输入不能为空")

        if len(user_input) > MAX_INPUT_LENGTH:
            raise InputValidationError(
                f"输入过长（最大{MAX_INPUT_LENGTH}字符，当前{len(user_input)}字符）"
            )

        start_time = time.time()

        try:
            # 2. 预处理
            standardized_text = self.preprocessor.standardize_text(user_input)

            # 3. 语义分析
            semantic_info = self.analyzer.analyze(standardized_text)

            # 4. 更新上下文（包含情感分析和话题追踪）
            self.context_manager.update_context(semantic_info, user_input)

            # 5. 脚本匹配（必须匹配，无回退逻辑）
            script_response = self.script_engine.match_script(standardized_text, semantic_info)
            if script_response:
                final_response = script_response
            else:
                # 严禁回退：脚本匹配失败直接抛出异常
                logger.warning(f"脚本匹配失败：'{user_input[:50]}...'")
                raise ScriptMatchingError(
                    f"无匹配脚本：'{user_input[:50]}...'"
                )

            # 6. 记录对话
            self._record_conversation(user_input, final_response)

            # 7. 记录日志和性能
            self._log_interaction(user_input, final_response, start_time)

            return final_response

        except (InputValidationError, ScriptMatchingError):
            # 业务异常直接抛出
            raise
        except Exception as e:
            # 系统异常记录日志后抛出
            logger.error(f"响应生成失败：{e}", exc_info=True)
            # 注册降级事件
            degradation_monitor.register_degradation(
                component='respond',
                reason=str(e),
                severity=3,
                recovery_plan='请检查系统配置和依赖'
            )
            raise ResponseGenerationError("响应生成失败，请稍后再试") from e

    def _log_interaction(self, user_input: str, response: str, start_time: float):
        """记录交互日志和性能"""
        duration = (time.time() - start_time) * 1000

        if self.enable_logging and self.dialogue_logger:
            self.dialogue_logger.log_dialogue(user_input, response)
            self.dialogue_logger.log_performance("respond", duration)

        if self.perf_monitor:
            self.perf_monitor.start_timer("respond")
            self.perf_monitor.stop_timer("respond", duration_ms=duration)

    def _record_conversation(self, user_input: str, response: str):
        """记录对话历史"""
        self.conversation_history.add_turn(user_input, response)

    def get_conversation_summary(self) -> Dict:
        """获取对话摘要"""
        context_state = self.context_manager.get_context_state()
        return {
            'turns': len(self.conversation_history.history),
            'recent_entities': self.context_manager.get_recent_persons(limit=3),
            'current_topic': context_state.get('current_topic', ''),
            'emotion_trend': context_state.get('emotion_trend', 'neutral'),
            'script_usage': self.script_engine.script_history,
            'recent_events': self.context_manager.get_recent_events(limit=2),
            'ltp_stats': self.script_engine.get_ltp_stats() if hasattr(self.script_engine, 'get_ltp_stats') else {}
        }

    def reset(self):
        """重置对话状态"""
        self.context_manager.reset()
        self.conversation_history.clear()
        self.script_engine.script_history = {}
        self.script_engine.last_used_responses = {}
        # 重置脚本引擎
        self.script_engine.reset()


# 主程序入口
if __name__ == "__main__":
    alice = AliceBot()

    print("Alice: 你好！我是 Alice。有什么想聊的吗？")
    print("Alice: 输入 'quit' 或 '再见' 结束对话。\n")

    while True:
        try:
            user_input = input("你：").strip()
            if user_input.lower() in ['再见', 'quit', 'exit', 'bye']:
                print("Alice: 再见！很高兴和你聊天！")
                break

            if not user_input:
                continue

            response = alice.respond(user_input)
            print(f"Alice: {response}")

        except KeyboardInterrupt:
            print("\nAlice: 再见！")
            break
        except RuntimeError as e:
            # 严禁回退：运行时错误直接抛出
            print(f"Alice: {e}")
            break
        except Exception as e:
            # 其他异常也抛出
            raise
