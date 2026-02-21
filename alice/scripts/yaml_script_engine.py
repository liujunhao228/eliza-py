#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本引擎 v2 模块

支持 YAML 格式的脚本配置，提供更灵活的脚本定义和优先级调度。

脚本模块:
- 叙事助推 (Narrative Continuity)
- 实体深度挖掘 (Entity Deep-Dive)
- 认知探索 (Cognitive Probing)
- Meta 对话 (Meta-Conversation)

支持的 LTP 变量:
- tokens: 分词列表
- pos_tags: 词性标注列表
- entities: 命名实体列表
- dependencies: 依存句法关系
- subject: 主语
- predicate: 谓语
- object: 宾语
- triples: 主谓宾三元组
- semantic_roles: 语义角色

支持的上下文变量:
- turn_count: 对话轮数
- time_context: 时间上下文
- user_profile: 用户画像
"""

import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from alice.exceptions import (
    InvalidConfigurationError,
    MissingConfigurationError,
    ConfigurationError,
    DependencyError,
)

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PyYAML 未安装，YAML 脚本引擎将不可用")

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """脚本意图定义"""
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    
    # 新增：仅关键词匹配标志，设为 True 时不进行代词替换
    keyword_only: bool = False

    # 统计信息
    usage_count: int = 0
    last_used: Optional[str] = None


class YAMLScriptEngine:
    """
    YAML 脚本引擎 v2
    
    功能:
    - 加载 YAML 格式脚本
    - 基于优先级的意图匹配
    - 条件触发机制
    - 响应模板管理
    - 使用统计追踪
    
    优先级调度:
    - P0 (90-100): 非常重要
    - P1 (70-89): 实体挖掘
    - P2 (40-69): 叙事助推
    - P3 (0-39): 万能回复
    """

    def __init__(self, script_file: Optional[str] = None):
        """
        初始化 YAML 脚本引擎

        Args:
            script_file: YAML 脚本文件路径
        """
        self.script_file = script_file
        self.intents: Dict[str, ScriptIntent] = {}
        self._load_scripts()

    def _load_scripts(self) -> None:
        """从 YAML 文件加载脚本"""
        if not YAML_AVAILABLE:
            raise DependencyError("PyYAML 未安装，无法使用 YAML 脚本引擎")

        if not self.script_file:
            raise MissingConfigurationError("未指定 YAML 脚本文件路径")

        script_path = Path(self.script_file)
        if not script_path.exists():
            raise MissingConfigurationError(f"脚本文件不存在：{script_path}")

        try:
            # 先读取文件内容为字符串，避免 Windows 上文件锁导致的空读问题
            content = script_path.read_text(encoding="utf-8")
            
            # 检查文件内容是否为空
            if not content or not content.strip():
                raise InvalidConfigurationError(f"脚本文件内容为空：{script_path}")
            
            scripts_data = yaml.safe_load(content)

            if not scripts_data:
                raise InvalidConfigurationError(f"脚本文件解析结果为空：{script_path}")

            self._parse_scripts(scripts_data, script_path)
            logger.info(f"成功加载 {len(self.intents)} 个脚本意图")

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 [{script_path}]: {e}", exc_info=True)
            raise InvalidConfigurationError(f"YAML 脚本格式错误：{script_path}") from e
        except IOError as e:
            logger.error(f"无法读取脚本文件 [{script_path}]: {e}", exc_info=True)
            raise ConfigurationError(f"无法读取 YAML 脚本文件：{script_path}") from e

    def _parse_scripts(self, scripts_data: Any, script_path: Path) -> None:
        """
        解析脚本数据

        Args:
            scripts_data: 脚本数据列表
            script_path: 脚本文件路径（用于错误报告）

        Raises:
            InvalidConfigurationError: 当脚本格式无效时
        """
        if not isinstance(scripts_data, list):
            raise InvalidConfigurationError(
                f"脚本格式错误：期望列表格式，实际为 {type(scripts_data).__name__} [{script_path}]"
            )

        for idx, script_data in enumerate(scripts_data):
            if not isinstance(script_data, dict):
                raise InvalidConfigurationError(
                    f"脚本格式错误：索引 {idx} 处的条目应为字典 [{script_path}]"
                )

            # 验证必需字段
            if "intent" not in script_data:
                raise InvalidConfigurationError(
                    f"脚本缺少必需字段 'intent' (索引：{idx}) [{script_path}]"
                )

            if "templates" not in script_data:
                raise InvalidConfigurationError(
                    f"脚本缺少必需字段 'templates' (意图：{script_data.get('intent', 'unknown')}) [{script_path}]"
                )

            templates = script_data.get("templates", [])
            if not isinstance(templates, list) or len(templates) == 0:
                raise InvalidConfigurationError(
                    f"脚本 'templates' 必须是非空列表 (意图：{script_data.get('intent', 'unknown')}) [{script_path}]"
                )

            intent_name = script_data.get("intent", f"intent_{len(self.intents)}")

            intent = ScriptIntent(
                name=intent_name,
                priority=script_data.get("priority", 50),
                condition=script_data.get("condition"),
                templates=script_data.get("templates", []),
                reassembly_rules=script_data.get("reassembly_rules", []),
                keyword_only=script_data.get("keyword_only", False),
            )

            self.intents[intent_name] = intent

    def match(self, text: str, context: Optional[Dict[str, Any]] = None) -> Optional[ScriptIntent]:
        """
        匹配脚本

        Args:
            text: 输入文本
            context: 上下文信息（包含 entities 等）

        Returns:
            匹配的脚本意图
        """
        context = context or {}

        # 按优先级排序（从高到低）
        sorted_intents = sorted(
            self.intents.values(),
            key=lambda i: i.priority,
            reverse=True,
        )

        for intent in sorted_intents:
            if self._check_condition(intent, text, context):
                intent.usage_count += 1
                from datetime import datetime
                intent.last_used = datetime.now().isoformat()
                return intent

        return None

    def _check_condition(
        self,
        intent: ScriptIntent,
        text: str,
        context: Dict[str, Any],
    ) -> bool:
        """
        检查条件是否满足

        支持的 LTP 变量条件:
        - entities: 命名实体类型匹配
        - keywords: 关键词匹配
        - pos_tags: 词性标签匹配
        - dependencies: 依存关系匹配
        - subject/predicate/object: 句法成分匹配
        - triples: 三元组匹配
        - semantic_roles: 语义角色匹配
        - min_tokens/max_tokens: 分词数量范围
        - has_predicate: 是否包含谓语

        Args:
            intent: 脚本意图
            text: 输入文本
            context: 上下文信息（包含 syntax, entities, tokens 等）

        Returns:
            条件是否满足
        """
        condition = intent.condition

        if condition is None:
            return True  # 无条件，总是匹配

        # 检查实体条件
        if "entities" in condition:
            required_entities = condition["entities"]
            context_entities = context.get("entities", [])
            
            # 将要求的实体类型转换为大写集合，用于不区分大小写的匹配
            required_entities_upper = {e.upper() for e in required_entities}

            if not any(e[0].upper() in required_entities_upper for e in context_entities):
                return False

        # 检查关键词条件
        if "keywords" in condition:
            keywords = condition["keywords"]
            if not any(kw in text for kw in keywords):
                return False

        # 检查 POS 标签条件
        if "pos_tags" in condition:
            required_pos = condition["pos_tags"]
            syntax = context.get("syntax", {})
            pos_list = syntax.get("poses", []) if syntax else []
            
            # 也检查 tokens 中的 pos 信息
            tokens_with_pos = context.get("tokens_with_pos", [])
            token_pos_list = [pos for _, pos in tokens_with_pos] if tokens_with_pos else []
            
            all_pos = pos_list + token_pos_list
            
            # 检查是否有至少一个匹配的词性
            if not any(pos in all_pos for pos in required_pos):
                return False

        # 检查依存关系条件
        if "dependencies" in condition:
            required_deps = condition["dependencies"]
            syntax = context.get("syntax", {})
            dependencies = syntax.get("dependencies", [])
            
            # 检查是否有至少一个匹配的依存关系
            if not any(dep.get("relation") in required_deps for dep in dependencies):
                return False

        # 检查主语条件
        if "subject" in condition:
            required_subjects = condition["subject"]
            syntax = context.get("syntax", {})
            subject = syntax.get("subject", "")
            
            if not subject or not any(subj in subject for subj in required_subjects):
                return False

        # 检查谓语条件
        if "predicate" in condition:
            required_predicates = condition["predicate"]
            syntax = context.get("syntax", {})
            predicate = syntax.get("predicate", "")
            
            if not predicate or not any(pred in predicate for pred in required_predicates):
                return False

        # 检查宾语条件
        if "object" in condition:
            required_objects = condition["object"]
            syntax = context.get("syntax", {})
            obj = syntax.get("object", "")
            
            if not obj or not any(o in obj for o in required_objects):
                return False

        # 检查是否有谓语（判断是否为完整句子）
        if "has_predicate" in condition:
            required_has = condition["has_predicate"]
            syntax = context.get("syntax", {})
            has_pred = bool(syntax.get("predicate", ""))
            
            if required_has and not has_pred:
                return False
            if not required_has and has_pred:
                return False

        # 检查三元组条件
        if "triples" in condition:
            required_triples = condition["triples"]
            triples = context.get("triples", [])
            
            if not triples:
                return False
            
            # 检查是否有匹配的三元组类型
            for req in required_triples:
                if isinstance(req, dict):
                    # 支持更复杂的三元组匹配
                    if "subject" in req:
                        if not any(t[0] == req["subject"] for t in triples):
                            return False
                    if "predicate" in req:
                        if not any(t[1] == req["predicate"] for t in triples):
                            return False
                    if "object" in req:
                        if not any(t[2] == req["object"] for t in triples):
                            return False
                else:
                    # 简单匹配：req 是字符串，匹配三元组的任何部分
                    if not any(req in str(t) for t in triples):
                        return False

        # 检查语义角色条件
        if "semantic_roles" in condition:
            required_roles = condition["semantic_roles"]
            semantic_roles = context.get("semantic_roles", [])
            
            if not semantic_roles:
                return False
            
            # 检查是否有匹配的语义角色
            for role in semantic_roles:
                if role.get("role_type") in required_roles:
                    return True
            return False

        # 检查分词数量范围
        if "min_tokens" in condition:
            min_count = condition["min_tokens"]
            tokens = context.get("tokens", [])
            if len(tokens) < min_count:
                return False

        if "max_tokens" in condition:
            max_count = condition["max_tokens"]
            tokens = context.get("tokens", [])
            if len(tokens) > max_count:
                return False

        # 检查对话轮数范围
        if "min_turns" in condition:
            min_turns = condition["min_turns"]
            turn_count = context.get("turn_count", 0)
            if turn_count < min_turns:
                return False

        if "max_turns" in condition:
            max_turns = condition["max_turns"]
            turn_count = context.get("turn_count", 0)
            if turn_count > max_turns:
                return False

        return True

    def generate_response(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成响应

        Args:
            intent: 脚本意图
            context: 上下文信息

        Returns:
            生成的响应
        """
        if not intent.templates:
            return ""

        # 选择一个模板（避免重复）
        template = self._select_template(intent)

        # 填充实体占位符
        if context:
            template = self._fill_placeholders(template, context)

        return template

    def generate_response_with_reassembly(
        self,
        intent: ScriptIntent,
        context: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None,
        reassembly_engine: Optional[Any] = None,
    ) -> str:
        """
        生成响应（支持代词替换）

        Args:
            intent: 脚本意图
            context: 上下文信息
            user_input: 用户输入
            reassembly_engine: 句法重组引擎

        Returns:
            生成的响应
        """
        if not intent.templates:
            return ""

        # 选择一个模板（避免重复）
        template = self._select_template(intent)

        # 如果是 keyword_only 模板，仅填充实体占位符，不进行代词替换
        if intent.keyword_only:
            if context:
                template = self._fill_placeholders(template, context)
            return template

        # 非 keyword_only 模板，使用重组引擎进行代词替换
        if reassembly_engine and user_input:
            template = self._fill_placeholders(template, context or {})
            # 使用重组引擎应用代词映射
            response = reassembly_engine.reassemble(
                components=[user_input],
                reassembly_rule=template,
                apply_pronoun_mapping=True,
            )
            return response

        # 无重组引擎时，仅填充实体占位符
        if context:
            template = self._fill_placeholders(template, context)
        return template

    def _select_template(self, intent: ScriptIntent) -> str:
        """
        选择模板（避免重复）
        
        Args:
            intent: 脚本意图
            
        Returns:
            选中的模板
        """
        templates = intent.templates
        
        if len(templates) == 1:
            return templates[0]
        
        # 简单随机选择
        return random.choice(templates)

    def _fill_placeholders(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        填充占位符

        支持的占位符类型:
        - {entity_type}: 命名实体（如 {person}, {location}, {organization}）
        - {subject}: 主语
        - {predicate}: 谓语
        - {object}: 宾语
        - {token_N}: 第 N 个分词（从 0 开始）
        - {first_token}: 第一个分词
        - {last_token}: 最后一个分词
        - {pos_X}: 特定词性的词（如 {pos_v} 动词，{pos_n} 名词）
        - {dep_REL}: 特定依存关系的词（如 {dep_SBV} 主谓关系）
        - {triple_subject}: 三元组中的主语
        - {triple_object}: 三元组中的宾语
        - {triple_predicate}: 三元组中的谓语
        - {role_ROLE}: 特定语义角色的词（如 {role_A0} 施事）

        Args:
            template: 模板字符串
            context: 上下文信息

        Returns:
            填充后的字符串
        """
        # 填充命名实体占位符
        entities = context.get("entities", [])

        for entity_type, entity_text in entities:
            placeholder = f"{{{entity_type}}}"
            if placeholder in template:
                template = template.replace(placeholder, entity_text)

        # 填充句法成分占位符
        syntax = context.get("syntax", {}) or {}

        # 主语
        if syntax.get("subject"):
            template = template.replace("{subject}", syntax["subject"])

        # 谓语
        if syntax.get("predicate"):
            template = template.replace("{predicate}", syntax["predicate"])

        # 宾语
        if syntax.get("object"):
            template = template.replace("{object}", syntax["object"])

        # 填充分词占位符
        tokens = context.get("tokens", [])

        # 特定索引的分词 {token_N}
        token_pattern = re.compile(r"\{token_(\d+)\}")
        for match in token_pattern.finditer(template):
            idx = int(match.group(1))
            if 0 <= idx < len(tokens):
                template = template.replace(match.group(0), tokens[idx])

        # 第一个分词
        if tokens:
            template = template.replace("{first_token}", tokens[0])

        # 最后一个分词
        if tokens:
            template = template.replace("{last_token}", tokens[-1])

        # 填充词性占位符 {pos_X}
        tokens_with_pos = context.get("tokens_with_pos", [])
        pos_pattern = re.compile(r"\{pos_(\w+)\}")
        for match in pos_pattern.finditer(template):
            pos_tag = match.group(1)
            # 找到第一个匹配词性的词
            for token, pos in tokens_with_pos:
                if pos == pos_tag:
                    template = template.replace(match.group(0), token)
                    break

        # 填充依存关系占位符 {dep_REL}
        dependencies = syntax.get("dependencies", [])
        dep_pattern = re.compile(r"\{dep_(\w+)\}")
        for match in dep_pattern.finditer(template):
            dep_rel = match.group(1)
            # 找到第一个匹配依存关系的词
            for dep in dependencies:
                if dep.get("relation") == dep_rel:
                    template = template.replace(match.group(0), dep.get("word", ""))
                    break

        # 填充三元组占位符
        triples = context.get("triples", [])
        if triples:
            # 使用第一个三元组
            first_triple = triples[0]
            if len(first_triple) >= 3:
                if "{triple_subject}" in template:
                    template = template.replace("{triple_subject}", first_triple[0] or "")
                if "{triple_predicate}" in template:
                    template = template.replace("{triple_predicate}", first_triple[1] or "")
                if "{triple_object}" in template:
                    template = template.replace("{triple_object}", first_triple[2] or "")

        # 填充语义角色占位符 {role_ROLE}
        semantic_roles = context.get("semantic_roles", [])
        role_pattern = re.compile(r"\{role_(\w+)\}")
        for match in role_pattern.finditer(template):
            role_type = match.group(1)
            # 找到第一个匹配语义角色的词
            for role in semantic_roles:
                if role.get("role_type") == role_type:
                    template = template.replace(match.group(0), role.get("text", ""))
                    break

        # 填充时间变量占位符
        template = self._fill_time_placeholders(template, context)

        # 填充用户画像变量占位符
        template = self._fill_user_profile_placeholders(template, context)

        # 填充对话轮数占位符 {turn_count}
        turn_count = context.get("turn_count", 0)
        template = template.replace("{turn_count}", str(turn_count))

        # 清理未匹配的占位符
        template = re.sub(r"\{[^}]+\}", "", template)

        return template

    def _fill_time_placeholders(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        填充时间变量占位符

        支持的占位符（不区分大小写）:
        - {year}: 年份（如 2026）
        - {month}: 月份（1-12）
        - {day}: 日期（1-31）
        - {weekday}: 星期数字（0-6，0=周一）
        - {weekday_name}: 星期名称（如"星期五"）
        - {hour}: 小时（0-23）
        - {minute}: 分钟（0-59）
        - {second}: 秒（0-59）
        - {category_time}: 时间段（早晨/中午/下午/晚上/深夜）

        Args:
            template: 模板字符串
            context: 上下文信息

        Returns:
            填充后的字符串
        """
        # 从 context 获取 time_context 或 turn_count 等信息
        time_context = context.get("time_context", {})

        # 定义占位符映射（支持不区分大小写）
        time_placeholders = {
            "year": str(time_context.get("year", "")),
            "month": str(time_context.get("month", "")),
            "day": str(time_context.get("day", "")),
            "weekday": str(time_context.get("weekday", "")),
            "weekday_name": str(time_context.get("weekday_name", "")),
            "hour": str(time_context.get("hour", "")),
            "minute": str(time_context.get("minute", "")),
            "second": str(time_context.get("second", "")),
            "category_time": str(time_context.get("category_time", "")),
        }

        # 不区分大小写替换
        for key, value in time_placeholders.items():
            # 使用正则表达式进行不区分大小写的替换
            pattern = re.compile(r"\{" + key + r"\}", re.IGNORECASE)
            template = pattern.sub(value, template)

        return template

    def _fill_user_profile_placeholders(
        self,
        template: str,
        context: Dict[str, Any],
    ) -> str:
        """
        填充用户画像变量占位符

        支持的占位符:
        - {user_name}: 用户姓名
        - {user_nickname}: 用户昵称
        - {address_form}: 称呼偏好（你/您）

        Args:
            template: 模板字符串
            context: 上下文信息

        Returns:
            填充后的字符串
        """
        user_profile = context.get("user_profile", {})

        # 定义占位符映射
        profile_placeholders = {
            "user_name": str(user_profile.get("name", "")),
            "user_nickname": str(user_profile.get("nickname", "")),
            "address_form": str(user_profile.get("address_form", context.get("address_form", "你"))),
        }

        # 不区分大小写替换
        for key, value in profile_placeholders.items():
            pattern = re.compile(r"\{" + key + r"\}", re.IGNORECASE)
            template = pattern.sub(value, template)

        return template

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_intents": len(self.intents),
            "intents": [
                {
                    "name": i.name,
                    "priority": i.priority,
                    "usage_count": i.usage_count,
                    "last_used": i.last_used,
                }
                for i in self.intents.values()
            ],
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        for intent in self.intents.values():
            intent.usage_count = 0
            intent.last_used = None
