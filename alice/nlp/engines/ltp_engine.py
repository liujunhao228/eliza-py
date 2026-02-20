#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTP 引擎 - 句法分析与实体识别（增强版）
======================================

功能:
- 分词 + 词性标注 (CWS + POS)
- 命名实体识别 (NER)
- 依存句法分析 (DEP)
- 语义角色标注 (SRL) - 可选
- 语义依存分析 (SDP) - 可选

架构设计:
- 分层架构：核心层 / 任务层 / 应用层
- 插件化任务管理
- 完整的类型注解
- 完善的错误处理与降级策略
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    List, Optional, Dict, Tuple, Union, Any,
    Callable, Protocol, runtime_checkable
)
from abc import ABC, abstractmethod
import json
import time

from alice.nlp.base import (
    SyntaxAnalyzer,
    Entity,
    EntityType,
    NlpResult,
    SyntaxStructure,
)
from alice.exceptions import DependencyError

logger = logging.getLogger(__name__)

# =============================================================================
# 依赖检查与导入
# =============================================================================

try:
    from ltp import LTP
    LTP_AVAILABLE = True
    LTP_VERSION = getattr(LTP, '__version__', 'unknown')
except ImportError:
    LTP_AVAILABLE = False
    LTP_VERSION = None
    logger.warning("LTP 未安装，功能不可用（安装：pip install ltp>=4.2.10）")


# =============================================================================
# 枚举与数据模型
# =============================================================================

class TaskType(Enum):
    """LTP 支持的任务类型"""
    CWS = auto()      # 中文分词
    POS = auto()      # 词性标注
    NER = auto()      # 命名实体识别
    DEP = auto()      # 依存句法分析
    SDP = auto()      # 语义依存分析（需单独开启）
    SRL = auto()      # 语义角色标注（需单独开启）


@dataclass(frozen=True)
class Token:
    """分词单元"""
    text: str
    idx: int
    start_pos: int
    end_pos: int

    def __repr__(self) -> str:
        return f"Token({self.text!r}, pos={self.start_pos}-{self.end_pos})"


@dataclass
class POSTag:
    """词性标注结果"""
    token: Token
    pos: str          # 词性标签
    probability: float = 1.0

    # 常见词性对照表（PKU 标注集）
    POS_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'n': '名词', 'v': '动词', 'a': '形容词', 'd': '副词',
        'm': '数词', 'q': '量词', 'r': '代词', 'p': '介词',
        'c': '连词', 'u': '助词', 'e': '叹词', 'y': '语气词',
        'o': '拟声词', 'h': '前缀', 'k': '后缀', 'x': '字符串',
        'w': '标点符号',
        # 命名实体标签
        'nh': '人名', 'ni': '机构名', 'ns': '地名',
        'nt': '时间词', 'nz': '其他专名',
    })

    @property
    def description(self) -> str:
        return self.POS_DESCRIPTIONS.get(self.pos, '未知')


@dataclass
class DependencyRelation:
    """依存句法关系"""
    token: Token
    head_idx: int     # 依存头部索引 (-1 表示根节点)
    relation: str     # 依存关系类型

    # LTP 依存关系标注集（共 14 种）
    RELATION_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'SBV': '主谓关系',      # Subject-Verb
        'VOB': '动宾关系',      # Verb-Object
        'IOB': '间宾关系',      # Indirect-Object
        'FOB': '前置宾语',      # Fronting-Object
        'DBL': '兼语',          # Double
        'ATT': '定中关系',      # Attribute
        'ADV': '状中结构',      # Adverbial
        'CMP': '动补结构',      # Complement
        'COO': '并列关系',      # Coordinate
        'POB': '介宾关系',      # Preposition-Object
        'LAD': '左附加关系',    # Left Adjunct
        'RAD': '右附加关系',    # Right Adjunct
        'IS': '独立结构',       # Independent Structure
        'HED': '核心关系',      # Head
        'WP': '标点符号',       # Punctuation
    })

    @property
    def is_root(self) -> bool:
        return self.head_idx == -1 or self.relation == 'HED'

    @property
    def description(self) -> str:
        return self.RELATION_DESCRIPTIONS.get(self.relation, self.relation)


@dataclass
class SemanticRole:
    """语义角色标注结果（SRL）"""
    predicate_idx: int
    predicate: str
    arguments: List[Tuple[str, str, int, int]]  # (role_type, text, start, end)

    # 语义角色类型（基于 PropBank 标准）
    ROLE_DESCRIPTIONS: Dict[str, str] = field(default_factory=lambda: {
        'A0': '施事（动作发出者）',
        'A1': '受事（动作承受者）',
        'A2': '起点/终点/受益人',
        'A3': '起点/受益人',
        'A4': '终点',
        'A5': '工具/方式',
        'ADV': '附加语（状语）',
        'TMP': '时间',
        'LOC': '地点',
        'MNR': '方式',
        'PRP': '目的',
        'CAU': '原因',
        'EXT': '范围',
        'DIR': '方向',
    })


@dataclass
class SemanticDependency:
    """语义依存关系（SDP）"""
    head_idx: int
    dependent_idx: int
    relation: str


@dataclass
class SemanticDependencyGraph:
    """语义依存图（SDP）"""
    edges: List[SemanticDependency]

    def get_heads(self, idx: int) -> List[int]:
        """获取一个词的所有语义父节点"""
        return [e.head_idx for e in self.edges if e.dependent_idx == idx]

    def get_dependents(self, idx: int) -> List[int]:
        """获取一个词的所有语义子节点"""
        return [e.dependent_idx for e in self.edges if e.head_idx == idx]


@dataclass
class LtpFullResult:
    """LTP 完整分析结果"""
    text: str
    tokens: List[Token] = field(default_factory=list)
    pos_tags: List[POSTag] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    dependencies: List[DependencyRelation] = field(default_factory=list)
    semantic_roles: Optional[List[SemanticRole]] = None
    semantic_deps: Optional[SemanticDependencyGraph] = None
    raw_output: Optional[Any] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'text': self.text,
            'tokens': [{'text': t.text, 'pos': t.start_pos} for t in self.tokens],
            'pos_tags': [{'word': p.token.text, 'pos': p.pos, 'desc': p.description}
                        for p in self.pos_tags],
            'entities': [{'text': e.text, 'type': e.entity_type.name,
                         'confidence': e.confidence} for e in self.entities],
            'dependencies': [{'word': d.token.text, 'relation': d.relation,
                            'head': d.head_idx, 'desc': d.description}
                           for d in self.dependencies],
            'semantic_roles': [
                {
                    'predicate': r.predicate,
                    'arguments': [
                        {'type': arg[0], 'text': arg[1], 'desc': SemanticRole.ROLE_DESCRIPTIONS.get(arg[0], arg[0])}
                        for arg in r.arguments
                    ]
                }
                for r in (self.semantic_roles or [])
            ] if self.semantic_roles else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def get_main_predicate(self) -> Optional[str]:
        """获取句子核心谓语"""
        for dep in self.dependencies:
            if dep.relation == 'HED' and dep.token.pos in ['v', 'a']:
                return dep.token.text
        return None

    def get_subjects(self) -> List[str]:
        """获取所有主语"""
        return [dep.token.text for dep in self.dependencies if dep.relation == 'SBV']

    def get_objects(self) -> List[str]:
        """获取所有宾语"""
        return [dep.token.text for dep in self.dependencies if dep.relation == 'VOB']


# =============================================================================
# 配置类
# =============================================================================

@dataclass
class LtpConfig:
    """LTP 引擎配置"""
    model_path: Optional[str] = None
    device: Optional[str] = None      # 'cpu', 'cuda', 'cuda:0' 等
    batch_size: int = 32
    max_length: int = 512
    lazy_load: bool = True
    cache_dir: Optional[str] = None

    # 任务启用开关
    enable_cws: bool = True
    enable_pos: bool = True
    enable_ner: bool = True
    enable_dep: bool = True
    enable_sdp: bool = False          # 语义依存分析，默认关闭
    enable_srl: bool = False          # 语义角色标注，默认关闭

    def get_enabled_tasks(self) -> List[str]:
        """获取启用的任务列表"""
        tasks = []
        if self.enable_cws: tasks.append('cws')
        if self.enable_pos: tasks.append('pos')
        if self.enable_ner: tasks.append('ner')
        if self.enable_dep: tasks.append('dep')
        if self.enable_sdp: tasks.append('sdp')
        if self.enable_srl: tasks.append('srl')
        return tasks


# =============================================================================
# 异常类
# =============================================================================

class LtpError(Exception):
    """LTP 引擎异常基类"""
    pass


class ModelLoadError(LtpError):
    """模型加载失败"""
    pass


class AnalysisError(LtpError):
    """分析过程错误"""
    pass


# =============================================================================
# 任务处理器接口
# =============================================================================

@runtime_checkable
class TaskHandler(Protocol):
    """任务处理器协议"""
    task_type: TaskType

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Any:
        ...


class BaseTaskHandler(ABC):
    """任务处理器基类"""
    task_type: TaskType

    @abstractmethod
    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Any:
        raise NotImplementedError


# =============================================================================
# 具体任务处理器
# =============================================================================

class CWSTaskHandler(BaseTaskHandler):
    """分词任务处理器 (CWS)"""
    task_type = TaskType.CWS

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[Token]:
        if not hasattr(ltp_output, 'cws') or not ltp_output.cws:
            # 回退到字符级分词
            return [Token(text[i], i, i, i+1) for i in range(len(text))]

        words = ltp_output.cws[0] if ltp_output.cws else []
        result_tokens = []
        pos = 0
        for idx, word in enumerate(words):
            start = text.find(word, pos)
            if start == -1:
                start = pos
            end = start + len(word)
            result_tokens.append(Token(word, idx, start, end))
            pos = end
        return result_tokens


class POSTaskHandler(BaseTaskHandler):
    """词性标注处理器 (POS)"""
    task_type = TaskType.POS

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[POSTag]:
        if not hasattr(ltp_output, 'pos') or not ltp_output.pos:
            return [POSTag(token, 'n', 0.0) for token in tokens]

        pos_tags = ltp_output.pos[0] if ltp_output.pos else []
        return [
            POSTag(token, pos_tag, 1.0)
            for token, pos_tag in zip(tokens, pos_tags)
        ]


class NERTaskHandler(BaseTaskHandler):
    """命名实体识别处理器 (NER)"""
    task_type = TaskType.NER

    # LTP NER 标签映射（BIOES 标注方案）
    ENTITY_MAPPING: Dict[str, EntityType] = {
        'Nh': EntityType.PERSON,        # 人名
        'Ni': EntityType.ORGANIZATION,  # 机构名
        'Ns': EntityType.LOCATION,      # 地名
        'nt': EntityType.TIME,          # 时间词
        'nd': EntityType.DATE,          # 日期
        'nz': EntityType.GENERAL,       # 其他专名
    }

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[Entity]:
        if not hasattr(ltp_output, 'ner') or not ltp_output.ner:
            return []

        entities = []
        ner_data = ltp_output.ner[0] if ltp_output.ner else []

        # 处理可能的嵌套结构 [[(text, type), ...]]
        if ner_data and isinstance(ner_data[0], list):
            ner_data = ner_data[0]

        for item in ner_data:
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                continue

            entity_text, entity_type = item[0], item[1]

            # 查找位置
            start_pos = text.find(entity_text)
            if start_pos == -1:
                continue

            entity_type_enum = self.ENTITY_MAPPING.get(
                entity_type, EntityType.GENERAL
            )

            entities.append(Entity(
                text=entity_text,
                entity_type=entity_type_enum,
                start_pos=start_pos,
                end_pos=start_pos + len(entity_text),
                confidence=0.95,
            ))

        return entities


class DEPTaskHandler(BaseTaskHandler):
    """依存句法分析处理器 (DEP)"""
    task_type = TaskType.DEP

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> List[DependencyRelation]:
        if not hasattr(ltp_output, 'dep') or not ltp_output.dep:
            return []

        dep_data = ltp_output.dep[0] if ltp_output.dep else {}

        # 处理不同版本的格式
        if isinstance(dep_data, dict):
            # 新版本：{'head': [...], 'label': [...]}
            heads = dep_data.get('head', [])
            labels = dep_data.get('label', [])
        elif isinstance(dep_data, list):
            # 旧版本：[(label, head), ...]
            labels = [d[0] if isinstance(d, (list, tuple)) else 'HED'
                     for d in dep_data]
            heads = [d[1] if isinstance(d, (list, tuple)) and len(d) > 1 else -1
                    for d in dep_data]
        else:
            return []

        dependencies = []
        for idx, (token, head, label) in enumerate(zip(tokens, heads, labels)):
            dependencies.append(DependencyRelation(
                token=token,
                head_idx=head if head is not None else -1,
                relation=label if label else 'HED'
            ))

        return dependencies


class SRLTaskHandler(BaseTaskHandler):
    """语义角色标注处理器 (SRL)"""
    task_type = TaskType.SRL

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Optional[List[SemanticRole]]:
        if not hasattr(ltp_output, 'srl') or not ltp_output.srl:
            return None

        srl_data = ltp_output.srl[0] if ltp_output.srl else []
        roles = []

        for predicate_data in srl_data:
            if not isinstance(predicate_data, dict):
                continue

            pred_idx = predicate_data.get('index', -1)
            pred_text = tokens[pred_idx].text if 0 <= pred_idx < len(tokens) else ''

            arguments = []
            for arg in predicate_data.get('arguments', []):
                if isinstance(arg, dict):
                    role_type = arg.get('type', '')
                    arg_text = arg.get('text', '')
                    arg_start = arg.get('start', -1)
                    arg_end = arg.get('end', -1)
                    arguments.append((role_type, arg_text, arg_start, arg_end))

            roles.append(SemanticRole(
                predicate_idx=pred_idx,
                predicate=pred_text,
                arguments=arguments
            ))

        return roles if roles else None


class SDPTaskHandler(BaseTaskHandler):
    """语义依存分析处理器 (SDP)"""
    task_type = TaskType.SDP

    def process(self, ltp_output: Any, text: str,
                tokens: List[Token]) -> Optional[SemanticDependencyGraph]:
        if not hasattr(ltp_output, 'sdp') or not ltp_output.sdp:
            return None

        sdp_data = ltp_output.sdp[0] if ltp_output.sdp else []
        edges = []

        for dep_idx, heads in enumerate(sdp_data):
            if not isinstance(heads, list):
                continue
            for head_info in heads:
                if isinstance(head_info, (tuple, list)) and len(head_info) >= 2:
                    head_idx, relation = head_info[0], head_info[1]
                    edges.append(SemanticDependency(
                        head_idx=head_idx,
                        dependent_idx=dep_idx,
                        relation=relation
                    ))

        return SemanticDependencyGraph(edges) if edges else None


# =============================================================================
# 主引擎类
# =============================================================================

class LtpEngine(SyntaxAnalyzer):
    """
    增强版 LTP 引擎

    支持任务:
    - CWS: 中文分词
    - POS: 词性标注
    - NER: 命名实体识别（人名、地名、机构名）
    - DEP: 依存句法分析（14 种依存关系）
    - SRL: 语义角色标注（需显式开启）
    - SDP: 语义依存分析（需显式开启）

    使用示例:
        >>> config = LtpConfig(enable_srl=True, enable_sdp=True)
        >>> engine = LtpEngine(config)
        >>> result = engine.analyze_full("小明在北京大学读书")
        >>> print(result.to_json())
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 512,
        lazy_load: bool = True,
        enable_srl: bool = False,
        enable_sdp: bool = False,
    ):
        """
        初始化 LTP 引擎

        Args:
            model_path: 模型路径，None 使用官方默认模型
            device: 运行设备 ('cpu', 'cuda', 'cuda:0' 等)，None 自动选择
            batch_size: 批处理大小，默认 32
            max_length: 最大序列长度，默认 512
            lazy_load: 是否懒加载（首次分析时才加载模型）
            enable_srl: 是否启用语义角色标注，默认关闭
            enable_sdp: 是否启用语义依存分析，默认关闭

        注意:
            - 模型首次加载较慢（约 5-10 秒）
            - SRL 和 SDP 会增加计算开销，建议按需开启
        """
        if not LTP_AVAILABLE:
            raise DependencyError(
                "LTP 库未安装",
                suggestion="pip install ltp>=4.2.10"
            )

        self.config = LtpConfig(
            model_path=model_path,
            device=device,
            batch_size=batch_size,
            max_length=max_length,
            lazy_load=lazy_load,
            enable_srl=enable_srl,
            enable_sdp=enable_sdp,
        )

        self._ltp: Optional[LTP] = None
        self._initialized = False

        # 注册任务处理器
        self._handlers: Dict[TaskType, BaseTaskHandler] = {
            TaskType.CWS: CWSTaskHandler(),
            TaskType.POS: POSTaskHandler(),
            TaskType.NER: NERTaskHandler(),
            TaskType.DEP: DEPTaskHandler(),
            TaskType.SRL: SRLTaskHandler(),
            TaskType.SDP: SDPTaskHandler(),
        }

        # 性能统计
        self._stats: Dict[str, Any] = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }

        if not lazy_load:
            self._load_model()

    def _load_model(self) -> bool:
        """加载 LTP 模型"""
        if self._initialized:
            return True

        try:
            load_kwargs = {}
            if self.config.model_path:
                load_kwargs['path'] = self.config.model_path
            if self.config.device:
                load_kwargs['device'] = self.config.device

            self._ltp = LTP(**load_kwargs)
            self._initialized = True

            logger.info(
                f"LTP 模型加载成功 | "
                f"版本：{LTP_VERSION} | "
                f"设备：{self.config.device or 'auto'} | "
                f"路径：{self.config.model_path or '默认'}"
            )
            return True

        except Exception as e:
            logger.error(f"LTP 模型加载失败：{e}", exc_info=True)
            raise ModelLoadError(f"无法加载 LTP 模型：{e}") from e

    @property
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not LTP_AVAILABLE:
            return False
        if self.config.lazy_load:
            return True
        return self._initialized and self._ltp is not None

    @property
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self._initialized and self._ltp is not None

    @property
    def stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self._stats.copy()

    def _ensure_loaded(self) -> bool:
        """确保模型已加载"""
        if not self._initialized:
            return self._load_model()
        return True

    def analyze_full(self, text: str) -> LtpFullResult:
        """
        完整分析（增强接口）

        Args:
            text: 待分析文本

        Returns:
            LtpFullResult: 完整分析结果
        """
        if not self._ensure_loaded():
            raise AnalysisError("模型未加载")

        if not text or not text.strip():
            return LtpFullResult(text=text)

        start_time = time.time()

        try:
            tasks = self.config.get_enabled_tasks()

            if not tasks:
                logger.warning("未启用任何分析任务")
                return LtpFullResult(text=text)

            # 执行 LTP 管道
            ltp_output = self._ltp.pipeline([text], tasks=tasks)

            # 构建结果
            result = self._build_result(ltp_output, text)

            # 更新统计
            elapsed = (time.time() - start_time) * 1000
            self._update_stats(elapsed, success=True)

            logger.debug(f"分析完成 | 文本长度：{len(text)} | 耗时：{elapsed:.2f}ms")

            return result

        except Exception as e:
            self._update_stats(0, success=False)
            logger.error(f"分析失败：{e}", exc_info=True)
            raise AnalysisError(f"文本分析失败：{e}") from e

    def _build_result(self, ltp_output: Any, text: str) -> LtpFullResult:
        """构建完整结果对象"""
        result = LtpFullResult(text=text, raw_output=ltp_output)

        # 1. 分词 (基础)
        if self.config.enable_cws:
            result.tokens = self._handlers[TaskType.CWS].process(
                ltp_output, text, []
            )

        # 2. 词性标注
        if self.config.enable_pos and result.tokens:
            result.pos_tags = self._handlers[TaskType.POS].process(
                ltp_output, text, result.tokens
            )

        # 3. 命名实体识别
        if self.config.enable_ner and result.tokens:
            result.entities = self._handlers[TaskType.NER].process(
                ltp_output, text, result.tokens
            )

        # 4. 依存句法分析
        if self.config.enable_dep and result.tokens:
            result.dependencies = self._handlers[TaskType.DEP].process(
                ltp_output, text, result.tokens
            )

        # 5. 语义角色标注 (SRL)
        if self.config.enable_srl and result.tokens:
            result.semantic_roles = self._handlers[TaskType.SRL].process(
                ltp_output, text, result.tokens
            )

        # 6. 语义依存分析 (SDP)
        if self.config.enable_sdp and result.tokens:
            result.semantic_deps = self._handlers[TaskType.SDP].process(
                ltp_output, text, result.tokens
            )

        return result

    def _update_stats(self, elapsed_ms: float, success: bool):
        """更新性能统计"""
        self._stats['total_calls'] += 1
        if not success:
            self._stats['failed_calls'] += 1

        # 移动平均
        n = self._stats['total_calls']
        self._stats['avg_time_ms'] = (
            (self._stats['avg_time_ms'] * (n - 1) + elapsed_ms) / n
        )

    # =====================================================================
    # 标准接口（兼容旧版）
    # =====================================================================

    def analyze(self, text: str) -> NlpResult:
        """标准分析接口（向后兼容）"""
        try:
            full_result = self.analyze_full(text)
            syntax = self._convert_to_syntax_structure(full_result)

            return NlpResult(
                text=text,
                tokens=[t.text for t in full_result.tokens] or list(text),
                entities=full_result.entities,
                syntax=syntax,
            )

        except Exception as e:
            logger.error(f"标准分析失败：{e}")
            return self._fallback_analyze(text)

    def _convert_to_syntax_structure(self,
                                     result: LtpFullResult) -> SyntaxStructure:
        """转换为旧版 SyntaxStructure"""
        words = [t.text for t in result.tokens]
        poses = [p.pos for p in result.pos_tags] if result.pos_tags else ['n'] * len(words)

        # 提取主谓宾
        subject = predicate = obj = ""
        modifiers: Dict[str, List[str]] = {}

        for dep in result.dependencies:
            word = dep.token.text
            if dep.relation == 'SBV':
                subject = word
            elif dep.relation == 'VOB':
                obj = word
            elif dep.relation == 'HED':
                predicate = word
            elif dep.relation in ['ATT', 'ADV']:
                head_idx = dep.head_idx
                if 0 <= head_idx < len(words):
                    head_word = words[head_idx]
                    modifiers.setdefault(head_word, []).append(word)

        return SyntaxStructure(
            words=words,
            poses=poses,
            subject=subject,
            predicate=predicate,
            object=obj,
            modifiers=modifiers,
        )

    def _fallback_analyze(self, text: str) -> NlpResult:
        """降级分析（字符级）"""
        tokens = list(text)
        return NlpResult(
            text=text,
            tokens=tokens,
            syntax=SyntaxStructure(words=tokens),
        )

    # =====================================================================
    # 便捷方法
    # =====================================================================

    def segment(self, text: str) -> List[str]:
        """仅分词"""
        result = self.analyze_full(text)
        return [t.text for t in result.tokens]

    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """分词 + 词性标注"""
        result = self.analyze_full(text)
        return [(p.token.text, p.pos) for p in result.pos_tags]

    def recognize_entities(self, text: str) -> List[Entity]:
        """仅实体识别"""
        result = self.analyze_full(text)
        return result.entities

    def parse_dependency(self, text: str) -> List[DependencyRelation]:
        """依存句法分析"""
        result = self.analyze_full(text)
        return result.dependencies

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]:
        """提取主谓宾三元组"""
        result = self.analyze_full(text)
        triples = []

        predicates = {}
        subjects = {}
        objects = {}

        for dep in result.dependencies:
            if dep.relation == 'HED':
                predicates[dep.token.idx] = dep.token.text
            elif dep.relation == 'SBV':
                head_idx = dep.head_idx
                if head_idx in predicates:
                    subjects[predicates[head_idx]] = dep.token.text
            elif dep.relation == 'VOB':
                head_idx = dep.head_idx
                if head_idx in predicates:
                    objects[predicates[head_idx]] = dep.token.text

        for pred in predicates:
            subj = subjects.get(pred, '')
            obj = objects.get(pred, '')
            if subj or obj:
                triples.append((subj, pred, obj))

        return triples

    # =====================================================================
    # 状态管理
    # =====================================================================

    @classmethod
    def clear_cache(cls):
        """清除 LTP 缓存（用于恢复）"""
        pass

    def reset(self):
        """重置引擎状态"""
        self._ltp = None
        self._initialized = False
        self._stats = {
            'total_calls': 0,
            'failed_calls': 0,
            'avg_time_ms': 0.0,
        }
        logger.info("LTP 引擎已重置")
