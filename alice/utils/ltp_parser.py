#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 依存句法分析器模块（优化版 - 按需加载）

功能:
- 基于 LTP (Language Technology Platform) 进行中文依存句法分析
- 提供按需加载机制，避免不必要的性能消耗
- 支持懒加载和缓存机制
- 提取句子主干结构（主谓宾等）
- 识别修饰关系（定中、状中等）
- 为重组规则引擎提供句法组件

依赖:
- ltp>=4.2.10 (可选，未安装时自动降级到简化模式)
"""

import logging
import os
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

# 导入自定义异常
from alice.exceptions import LTPError, ExternalLibraryError

# 模块级 logger
logger = logging.getLogger(__name__)

# 尝试导入 LTP
try:
    from ltp import LTP
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False
    logger.warning("未安装 LTP，将使用简化句法分析模式")


@dataclass
class DependencyWord:
    """依存词单元"""
    word: str           # 词语
    pos: str           # 词性
    dep: str           # 依存关系
    head: int          # 依存头索引
    index: int         # 当前索引


@dataclass
class SentenceStructure:
    """句子结构"""
    words: List[str] = field(default_factory=list)           # 词语列表
    poses: List[str] = field(default_factory=list)           # 词性列表
    deps: List[DependencyWord] = field(default_factory=list) # 依存关系
    subject: str = ""         # 主语
    predicate: str = ""       # 谓语
    object: str = ""          # 宾语
    modifiers: Dict[str, List[str]] = field(default_factory=dict)  # 修饰语


class LazyLTPWrapper:
    """
    LTP 模型懒加载包装器
    
    实现按需加载，只有在真正需要时才初始化 LTP 模型
    """
    
    _instance = None
    _ltp_model = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._ltp_model = None
            self._model_path = None
    
    def initialize(self, model_path: Optional[str] = None):
        """初始化 LTP 模型（按需）"""
        if self._ltp_model is not None:
            return True

        try:
            from ltp import LTP
            if model_path and os.path.exists(model_path):
                self._ltp_model = LTP(model_path)
            else:
                # 使用默认模型（自动下载）
                self._ltp_model = LTP()
            logger.info("LTP 模型加载成功")
            return True
        except Exception as e:
            logger.error(f"LTP 模型加载失败：{e}")
            self._ltp_model = None
            return False
    
    @property
    def ltp(self):
        """获取 LTP 模型实例"""
        return self._ltp_model
    
    def is_available(self) -> bool:
        """检查 LTP 是否可用"""
        return self._ltp_model is not None


class OptimizedLTPParser:
    """
    优化版 LTP 依存句法分析器

    新增特性：
    - 懒加载机制
    - 智能内容分析决策
    - 缓存优化
    - 按需初始化
    """

    def __init__(self, model_path: Optional[str] = None, lazy_load: bool = True):
        """
        初始化优化版 LTP 分析器

        参数:
            model_path: LTP 模型路径，如 None 则使用默认模型
            lazy_load: 是否启用懒加载（默认启用）
        """
        self._lazy_load = lazy_load
        self._model_path = model_path
        self._ltp_wrapper = LazyLTPWrapper()
        
        # 缓存机制
        self._parse_cache: Dict[str, SentenceStructure] = {}
        self._cache_size_limit = 100  # 最大缓存条目数
        
        # 初始化简化规则（确保始终存在）
        self._init_simple_rules()
        
        # 如果不禁用懒加载，则延迟初始化
        if not lazy_load:
            self._ensure_initialized()

    def _init_simple_rules(self):
        """初始化简化分析规则"""
        self.simple_rules = {
            'subject_patterns': ['我', '你', '他', '她', '它', '我们', '你们', '他们'],
            'predicate_keywords': ['是', '有', '在', '觉得', '认为', '喜欢', '讨厌', '希望', '想要', '需要'],
        }

    def _ensure_initialized(self) -> bool:
        """确保 LTP 已初始化"""
        if self._ltp_wrapper.is_available():
            return True
        return self._ltp_wrapper.initialize(self._model_path)

    def should_use_ltp(self, text: str) -> bool:
        """
        智能判断是否需要使用 LTP 分析
        
        参数:
            text: 待分析的文本
            
        返回:
            是否需要使用 LTP
        """
        # 简单规则过滤
        if len(text.strip()) < 10:
            return False
            
        # 问候语等简单对话
        if re.match(r'^(你好|在吗|再见|拜拜|您好)', text.strip()):
            return False
            
        # 简单单句
        if not any(punct in text for punct in ['，', '。', '！', '？']) and len(text) < 20:
            return False
            
        return True

    def parse(self, text: str) -> Optional[SentenceStructure]:
        """
        分析句子结构（带智能决策和缓存）

        参数:
            text: 待分析的文本

        返回:
            SentenceStructure 对象，分析失败返回 None
        """
        if not text.strip():
            return None

        # 检查缓存
        cache_key = text.strip()
        if cache_key in self._parse_cache:
            return self._parse_cache[cache_key]

        # 智能决策是否使用 LTP
        if self.should_use_ltp(text):
            # 需要复杂分析
            if self._lazy_load and not self._ltp_wrapper.is_available():
                # 懒加载模式下，先尝试初始化
                if not self._ensure_initialized():
                    result = self._parse_simple(text)
                else:
                    result = self._parse_with_ltp(text)
            elif self._ltp_wrapper.is_available():
                result = self._parse_with_ltp(text)
            else:
                result = self._parse_simple(text)
        else:
            # 简单内容使用基础分析
            result = self._parse_simple(text)

        # 缓存结果（如果成功）
        if result is not None:
            self._manage_cache(cache_key, result)

        return result

    def _manage_cache(self, key: str, value: SentenceStructure):
        """管理缓存大小"""
        if len(self._parse_cache) >= self._cache_size_limit:
            # 简单的 FIFO 缓存淘汰策略
            oldest_key = next(iter(self._parse_cache))
            del self._parse_cache[oldest_key]
        
        self._parse_cache[key] = value

    def _parse_with_ltp(self, text: str) -> SentenceStructure:
        """使用 LTP 进行完整句法分析"""
        try:
            # 使用正确的任务名称
            tasks = ['cws', 'pos', 'dep']
            
            # LTP 分析
            result = self._ltp_wrapper.ltp.pipeline([text], tasks=tasks)
            
            # 处理 LTPOutput 对象
            words = []
            poses = []
            dep_heads = []
            dep_labels = []
            
            if hasattr(result, 'cws'):
                # LTPOutput 对象格式
                words = result.cws[0] if result.cws else []
                
                if hasattr(result, 'pos') and result.pos:
                    poses = result.pos[0]
                else:
                    poses = ['n'] * len(words) if words else []
                
                if hasattr(result, 'dep') and result.dep:
                    dep_data = result.dep[0]
                    if isinstance(dep_data, dict):
                        dep_heads = dep_data.get('head', [])
                        dep_labels = dep_data.get('label', [])
            else:
                # 字典格式
                if isinstance(result, dict):
                    words = result.get('cws', [[]])[0] if result.get('cws') else []
                    poses = result.get('pos', [[]])[0] if result.get('pos') else ['n'] * len(words)
                    dep_info = result.get('dep', [[]])[0] if result.get('dep') else []

            # 如果没有有效的分析结果，降级到简化模式
            if not words:
                return self._parse_simple(text)

            # 构建依存词列表
            dep_words = []
            for i, (word, po) in enumerate(zip(words, poses)):
                # 获取依存关系信息
                if i < len(dep_heads) and i < len(dep_labels):
                    head = dep_heads[i]
                    dep_rel = dep_labels[i]
                else:
                    head = -1
                    dep_rel = 'HED'
                    
                dep_word = DependencyWord(
                    word=word,
                    pos=po,
                    dep=dep_rel,
                    head=head,
                    index=i
                )
                dep_words.append(dep_word)

            # 提取句子成分
            structure = SentenceStructure(
                words=words,
                poses=poses,
                deps=dep_words
            )

            # 提取主干和修饰语
            self._extract_components(structure)

            return structure

        except Exception as e:
            logger.warning(f"LTP 分析失败：{type(e).__name__}: {e}，降级到简化模式")
            # 注册降级事件
            from alice.utils.degradation_monitor import degradation_monitor
            degradation_monitor.register_degradation(
                component='ltp_parse',
                reason=f'{type(e).__name__}: {e}',
                severity=2,
                recovery_plan='使用简化句法分析模式'
            )
            return self._parse_simple(text)

    def _parse_simple(self, text: str) -> SentenceStructure:
        """简化句法分析（无 LTP 时的降级方案）"""
        # 简单分词（按字符）
        words = list(text)
        structure = SentenceStructure(words=words)

        # 简单匹配主语
        for pattern in self.simple_rules['subject_patterns']:
            if pattern in text:
                structure.subject = pattern
                break

        # 简单匹配谓语
        for kw in self.simple_rules['predicate_keywords']:
            if kw in text:
                structure.predicate = kw
                break

        return structure

    def _extract_components(self, structure: SentenceStructure):
        """
        从依存句法树中提取句子成分

        参数:
            structure: 句子结构对象
        """
        if not structure.deps:
            return

        # 提取主语（SBV 关系的子节点）
        for dep in structure.deps:
            if dep.dep == 'SBV':
                # SBV 的子节点是主语
                structure.subject = dep.word
            elif dep.dep == 'VOB':
                # VOB 的子节点是宾语
                structure.object = dep.word
            elif dep.dep == 'HED':
                # HED 是核心，通常是谓语
                structure.predicate = dep.word

        # 提取修饰语
        for dep in structure.deps:
            if dep.dep == 'ATT':
                if 'att' not in structure.modifiers:
                    structure.modifiers['att'] = []
                structure.modifiers['att'].append(dep.word)
            elif dep.dep == 'ADV':
                if 'adv' not in structure.modifiers:
                    structure.modifiers['adv'] = []
                structure.modifiers['adv'].append(dep.word)

    def get_main_structure(self, text: str) -> Dict[str, str]:
        """
        获取句子主干结构（主谓宾）

        参数:
            text: 待分析的文本

        返回:
            包含 subject, predicate, object 的字典
        """
        structure = self.parse(text)
        if not structure:
            return {'subject': '', 'predicate': '', 'object': ''}

        return {
            'subject': structure.subject,
            'predicate': structure.predicate,
            'object': structure.object,
        }

    def clear_cache(self):
        """清空分析缓存"""
        self._parse_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self._parse_cache),
            'cache_limit': self._cache_size_limit
        }


class SyntaxBasedReassemblyEngine:
    """
    基于句法的重组引擎
    
    利用句法分析结果生成更智能的回复
    """

    def __init__(self, parser: OptimizedLTPParser):
        self.parser = parser

    def reassemble_with_syntax(self, text: str, template: str) -> str:
        """
        基于句法结构进行重组
        
        参数:
            text: 原始文本
            template: 重组模板，支持 {SUBJ}, {PRED}, {OBJ} 占位符
            
        返回:
            重组后的文本
        """
        structure = self.parser.parse(text)
        if not structure:
            return template  # 如果分析失败，返回原始模板

        # 构建替换字典
        replacements = {
            '{SUBJ}': structure.subject or '你',
            '{PRED}': structure.predicate or '',
            '{OBJ}': structure.object or ''
        }

        # 执行替换
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        # 处理代词转换（我→你）
        result = result.replace('我', '你')
        
        return result

    def generate_syntax_question(self, text: str, question_type: str = 'why') -> str:
        """
        根据句法结构生成问句
        
        参数:
            text: 原始文本
            question_type: 问句类型 ('why', 'what', 'how')
            
        返回:
            生成的问句
        """
        structure = self.parser.parse(text)
        if not structure:
            return "能详细说说吗？"

        # 根据不同类型的问句生成模板
        templates = {
            'why': "为什么{SUBJ}{PRED}{OBJ}？",
            'what': "{SUBJ}{PRED}了什么{OBJ}？",
            'how': "{SUBJ}是怎么{PRED}{OBJ}的？"
        }

        template = templates.get(question_type, "为什么{SUBJ}{PRED}{OBJ}？")
        return self.reassemble_with_syntax(text, template)

    def extract_focus_point(self, text: str) -> str:
        """
        提取句子的焦点（最重要的成分）
        
        参数:
            text: 待分析的文本
            
        返回:
            焦点成分
        """
        structure = self.parser.parse(text)
        if not structure:
            return text[:10] + "..." if len(text) > 10 else text

        # 优先级：谓语 > 宾语 > 主语
        if structure.predicate:
            return structure.predicate
        elif structure.object:
            return structure.object
        elif structure.subject:
            return structure.subject
        else:
            return structure.words[0] if structure.words else text[:5]


# 确保向后兼容
LTPParser = OptimizedLTPParser

# 便捷函数
def parse_sentence(text: str, lazy_load: bool = True) -> Optional[SentenceStructure]:
    """
    便捷函数：分析句子结构
    
    参数:
        text: 待分析的文本
        lazy_load: 是否启用懒加载
        
    返回:
        句子结构对象
    """
    parser = OptimizedLTPParser(lazy_load=lazy_load)
    return parser.parse(text)


def get_main_components(text: str, lazy_load: bool = True) -> Dict[str, str]:
    """
    便捷函数：获取句子主干成分
    
    参数:
        text: 待分析的文本
        lazy_load: 是否启用懒加载
        
    返回:
        主干成分字典
    """
    parser = OptimizedLTPParser(lazy_load=lazy_load)
    return parser.get_main_structure(text)


# 确保模块可以被导入
__all__ = [
    'LTPParser',
    'OptimizedLTPParser',
    'SyntaxBasedReassemblyEngine',
    'SentenceStructure',
    'DependencyWord',
    'parse_sentence',
    'get_main_components'
]

if __name__ == "__main__":
    # 测试示例
    print("=== LTP 依存句法分析器测试 ===\n")

    test_sentences = [
        "我觉得今天很开心",
        "我和朋友去了一家新餐厅",
        "他说的话让我很感动",
        "我希望能够改变现状",
    ]

    parser = LTPParser()

    for sentence in test_sentences:
        print(f"原句：{sentence}")
        print("-" * 40)

        # 主干结构
        main = parser.get_main_structure(sentence)
        print(f"主干：主语={main['subject']}, 谓语={main['predicate']}, 宾语={main['object']}")

        # 修饰语
        modifiers = parser.get_modifiers(sentence)
        print(f"修饰语：{modifiers}")

        # 依存树
        tree = parser.get_dependency_tree(sentence)
        if tree:
            print(f"词语：{tree['words']}")
            print(f"依存关系:")
            for dep in tree['dependencies']:
                print(f"  {dep['word']}({dep['pos']}) --[{dep['dep']}]--> {dep['head_word']}")

        print()

    # 句法重组测试
    print("\n=== 句法重组测试 ===")
    reassembly_engine = SyntaxBasedReassemblyEngine(parser)

    for sentence in test_sentences:
        print(f"\n原句：{sentence}")
        response = reassembly_engine.reassemble_with_syntax(
            sentence,
            "为什么{SUBJ}{PRED}{OBJ}呢？"
        )
        print(f"重组：{response}")

        question = reassembly_engine.generate_syntax_question(sentence, 'why')
        print(f"问句：{question}")
