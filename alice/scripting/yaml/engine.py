#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本引擎

基于 YAML 的声明式脚本引擎，支持：
- 意图匹配和条件触发
- 响应模板管理
- 优先级调度
- 热重载支持

本模块依赖:
- PyYAML (外部库)
- scripting.base, scripting.context, scripting.config (内部模块)

使用示例:
    engine = YAMLScriptEngine()
    config = ScriptConfig(
        script_id="greeting",
        name="问候脚本",
        script_type="yaml",
        priority=90,
        script_path=Path("scripts/greeting.yaml"),
    )
    engine.load_script(config)
    
    context = ScriptContext(text="你好", tokens=["你好"])
    match = engine.match(context)
    if match:
        response = engine.generate_response(match.script_id, context)
"""

import hashlib
import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from alice.scripting.base import (
    BaseScriptEngine,
    ScriptConfig,
    ScriptMatchResult,
    ScriptResponse,
)
from alice.scripting.context import ScriptContext
from alice.scripting.config import ScriptConfigLoader

logger = logging.getLogger(__name__)


@dataclass
class ScriptIntent:
    """
    脚本意图定义
    
    Attributes:
        name: 意图名称
        priority: 优先级 (0-100)
        condition: 匹配条件
        templates: 响应模板列表
        reassembly_rules: 重组规则
        keyword_only: 是否仅关键词匹配（不进行代词替换）
        usage_count: 使用次数统计
        last_used: 最后使用时间
    """
    name: str
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None
    templates: List[str] = field(default_factory=list)
    reassembly_rules: List[str] = field(default_factory=list)
    keyword_only: bool = False
    usage_count: int = 0
    last_used: Optional[str] = None


class YAMLScriptEngine(BaseScriptEngine):
    """
    YAML 脚本引擎

    特性:
    - 声明式 YAML 配置
    - 基于条件的意图匹配
    - 响应模板管理
    - 优先级调度

    优先级分级:
    - P0 (90-100): 非常重要
    - P1 (70-89): 实体挖掘
    - P2 (40-69): 叙事助推
    - P3 (0-39): 万能回复
    """

    def __init__(
        self,
        default_script_file: Optional[Path] = None,
        config_loader: Optional[ScriptConfigLoader] = None,
        script_file: Optional[str] = None,  # 向后兼容参数
        reassembly_engine: Optional[Any] = None,  # 重组引擎（可选）
    ):
        """
        初始化 YAML 脚本引擎

        Args:
            default_script_file: 默认脚本文件路径（Path 对象）
            script_file: 默认脚本文件路径（字符串路径，向后兼容）
            reassembly_engine: 句法重组引擎实例（用于代词替换）
            config_loader: 配置加载器
        """
        super().__init__(engine_type="yaml")

        if not YAML_AVAILABLE:
            raise ImportError("PyYAML 未安装，请运行：pip install pyyaml")

        # 支持两种参数形式：default_script_file (Path) 或 script_file (str)
        self.default_script_file = default_script_file
        if script_file and not default_script_file:
            self.default_script_file = Path(script_file)

        self.config_loader = config_loader or ScriptConfigLoader()
        self.reassembly_engine = reassembly_engine

        # 意图存储
        self._intents: Dict[str, ScriptIntent] = {}
        self._script_hashes: Dict[str, str] = {}

        # 如果指定了默认文件，加载它
        if self.default_script_file:
            self._load_default_script()
    
    def _load_default_script(self) -> bool:
        """加载默认脚本"""
        if not self.default_script_file or not self.default_script_file.exists():
            logger.warning(f"默认脚本文件不存在：{self.default_script_file}")
            return False
        
        config = ScriptConfig(
            script_id=self.default_script_file.stem,
            name=self.default_script_file.stem,
            script_type="yaml",
            priority=50,
            script_path=self.default_script_file,
        )
        return self.load_script(config)
    
    # =========================================================================
    # BaseScriptEngine 接口实现
    # =========================================================================
    
    def load_script(self, config: ScriptConfig) -> bool:
        """
        加载 YAML 脚本
        
        Args:
            config: 脚本配置
            
        Returns:
            是否加载成功
        """
        if config.script_type != "yaml":
            logger.error(f"脚本类型不匹配：期望 'yaml'，实际 '{config.script_type}'")
            return False
        
        if not config.script_path:
            logger.error(f"脚本路径未指定：{config.script_id}")
            return False
        
        if not config.script_path.exists():
            logger.error(f"脚本文件不存在：{config.script_path}")
            return False
        
        try:
            # 读取脚本内容
            content = config.script_path.read_text(encoding='utf-8')
            
            # 计算哈希
            script_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            # 检查是否需要重新加载
            if config.script_id in self.scripts:
                if self._script_hashes.get(config.script_id) == script_hash:
                    logger.info(f"YAML 脚本未变更，跳过加载：{config.script_id}")
                    return True
            
            # 解析 YAML
            scripts_data = yaml.safe_load(content)
            
            if not scripts_data:
                logger.warning(f"YAML 脚本内容为空：{config.script_path}")
                return False
            
            if not isinstance(scripts_data, list):
                logger.error(f"YAML 脚本格式错误：期望列表格式：{config.script_path}")
                return False
            
            # 解析意图
            intents = self._parse_intents(scripts_data, config)
            
            if not intents:
                logger.warning(f"YAML 脚本未解析出任何意图：{config.script_path}")
                return False
            
            # 存储意图
            self._intents.update(intents)
            self._script_hashes[config.script_id] = script_hash
            self.scripts[config.script_id] = config
            
            self._increment_stat('load_count')
            logger.info(f"YAML 脚本加载成功：{config.script_id} ({len(intents)} 个意图)")
            return True
            
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 [{config.script_path}]: {e}")
            self._increment_stat('error_count')
            return False
        except Exception as e:
            logger.error(f"YAML 脚本加载失败 [{config.script_id}]: {e}")
            self._increment_stat('error_count')
            return False
    
    def unload_script(self, script_id: str) -> bool:
        """
        卸载脚本
        
        移除与脚本 ID 关联的所有意图。
        
        Args:
            script_id: 脚本 ID
            
        Returns:
            是否卸载成功
        """
        config = self.scripts.get(script_id)
        if not config:
            return False
        
        # 找到此脚本加载的所有意图
        intents_to_remove = []
        for intent_name, intent in self._intents.items():
            if intent.name.startswith(f"{script_id}_"):
                intents_to_remove.append(intent_name)
        
        # 移除意图
        for intent_name in intents_to_remove:
            del self._intents[intent_name]
        
        # 移除配置和哈希
        if script_id in self._script_hashes:
            del self._script_hashes[script_id]
        if script_id in self.scripts:
            del self.scripts[script_id]
        
        logger.info(f"YAML 脚本已卸载：{script_id} (移除 {len(intents_to_remove)} 个意图)")
        return True
    
    def match(self, context: ScriptContext) -> Optional[ScriptMatchResult]:
        """
        匹配 YAML 脚本意图
        
        Args:
            context: 脚本上下文
            
        Returns:
            匹配结果
        """
        self._increment_stat('match_count')
        
        # 获取所有启用的意图，按优先级排序
        enabled_intents = [
            intent for intent in self._intents.values()
            if self.scripts.get(intent.name.split('_')[0], ScriptConfig("", "", "yaml")).enabled
        ]
        enabled_intents.sort(key=lambda i: i.priority, reverse=True)
        
        for intent in enabled_intents:
            if self._check_condition(intent, context):
                intent.usage_count += 1
                from datetime import datetime
                intent.last_used = datetime.now().isoformat()
                
                return ScriptMatchResult(
                    script_id=intent.name,
                    script_type='yaml',
                    intent_name=intent.name,
                    priority=intent.priority,
                    confidence=self._calculate_confidence(intent, context),
                    metadata={
                        'templates_count': len(intent.templates),
                        'keyword_only': intent.keyword_only,
                    }
                )
        
        return None
    
    def generate_response(
        self,
        script_id: str,
        context: ScriptContext,
        user_input: Optional[str] = None,
    ) -> Optional[ScriptResponse]:
        """
        生成响应

        Args:
            script_id: 脚本 ID
            context: 脚本上下文
            user_input: 用户输入（用于重组引擎的代词替换）

        Returns:
            响应结果
        """
        intent = self._intents.get(script_id)
        if not intent:
            logger.error(f"意图不存在：{script_id}")
            return None

        if not intent.templates:
            logger.warning(f"意图没有响应模板：{script_id}")
            return None

        # 选择模板
        template = self._select_template(intent)

        # 如果是 keyword_only 模板，直接填充占位符（不进行代词替换）
        if intent.keyword_only:
            filled_template = self._fill_placeholders(template, context)
        # 如果有重组引擎和用户输入，使用重组引擎进行代词替换
        elif self.reassembly_engine and user_input:
            filled_template = self._generate_with_reassembly(
                template, context, user_input
            )
        else:
            # 默认填充占位符
            filled_template = self._fill_placeholders(template, context)

        return ScriptResponse(
            text=filled_template,
            script_id=script_id,
            intent_name=intent.name,
            metadata={
                'template': template,
                'keyword_only': intent.keyword_only,
            }
        )

    def _generate_with_reassembly(
        self,
        template: str,
        context: ScriptContext,
        user_input: str,
    ) -> str:
        """
        使用重组引擎生成响应（进行代词替换）

        Args:
            template: 模板字符串
            context: 上下文信息
            user_input: 用户输入

        Returns:
            重组后的响应
        """
        if not self.reassembly_engine:
            return self._fill_placeholders(template, context)

        # 先填充实体占位符
        filled_template = self._fill_placeholders(template, context)

        # 使用重组引擎应用代词映射
        response = self.reassembly_engine.reassemble(
            components=[user_input],
            reassembly_rule=filled_template,
            apply_pronoun_mapping=True,
        )

        return response.strip() if response else filled_template
    
    def reload_script(self, script_id: str) -> bool:
        """热重载脚本"""
        config = self.scripts.get(script_id)
        if not config:
            logger.error(f"脚本不存在，无法重载：{script_id}")
            return False
        
        # 先卸载
        self.unload_script(script_id)
        
        # 重新加载
        return self.load_script(config)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'engine_type': 'yaml',
            'loaded_scripts': len(self.scripts),
            'total_intents': len(self._intents),
            **self._stats,
            'intents': [
                {
                    'name': intent.name,
                    'priority': intent.priority,
                    'usage_count': intent.usage_count,
                    'last_used': intent.last_used,
                }
                for intent in self._intents.values()
            ]
        }
    
    def _get_extension(self) -> str:
        """获取文件扩展名"""
        return "yaml"
    
    def _create_config_from_file(self, file_path: Path) -> Optional[ScriptConfig]:
        """从文件创建配置"""
        try:
            script_id = file_path.stem
            
            return ScriptConfig(
                script_id=script_id,
                name=script_id,
                script_type="yaml",
                priority=50,
                script_path=file_path,
                description=f"YAML 脚本：{script_id}",
            )
        except Exception as e:
            logger.error(f"创建脚本配置失败 [{file_path}]: {e}")
            return None
    
    # =========================================================================
    # 内部方法
    # =========================================================================
    
    def _parse_intents(
        self,
        scripts_data: List[Dict[str, Any]],
        config: ScriptConfig,
    ) -> Dict[str, ScriptIntent]:
        """
        解析意图数据
        
        Args:
            scripts_data: 脚本数据列表
            config: 脚本配置
            
        Returns:
            意图字典
        """
        intents = {}
        
        for idx, script_data in enumerate(scripts_data):
            if not isinstance(script_data, dict):
                logger.warning(f"跳过无效的意图数据 (索引：{idx})")
                continue
            
            if "intent" not in script_data:
                logger.warning(f"意图缺少 'intent' 字段 (索引：{idx})")
                continue
            
            if "templates" not in script_data:
                logger.warning(f"意图缺少 'templates' 字段：{script_data.get('intent')}")
                continue
            
            templates = script_data.get("templates", [])
            if not isinstance(templates, list) or not templates:
                logger.warning(f"意图 'templates' 必须是非空列表：{script_data.get('intent')}")
                continue
            
            # 生成意图名称（使用脚本 ID 前缀避免冲突）
            intent_name = f"{config.script_id}_{script_data['intent']}"
            
            intent = ScriptIntent(
                name=intent_name,
                priority=script_data.get("priority", config.priority),
                condition=script_data.get("condition"),
                templates=templates,
                reassembly_rules=script_data.get("reassembly_rules", []),
                keyword_only=script_data.get("keyword_only", False),
            )
            
            intents[intent_name] = intent
        
        return intents
    
    def _check_condition(self, intent: ScriptIntent, context: ScriptContext) -> bool:
        """
        检查条件是否满足

        支持的条件类型:
        - entities: 命名实体匹配
        - keywords: 关键词匹配
        - pos_tags: 词性标签匹配
        - dependencies: 依存关系匹配
        - subject/predicate/object: 句法成分匹配
        - triples: 三元组匹配
        - semantic_roles: 语义角色匹配
        - semantic_deps: 语义依存匹配
        - min_tokens/max_tokens: 分词数量范围
        - min_turns/max_turns: 对话轮数范围

        Args:
            intent: 意图
            context: 上下文

        Returns:
            条件是否满足
        """
        condition = intent.condition

        if condition is None:
            return True  # 无条件，总是匹配

        # 检查实体条件
        if "entities" in condition:
            required_entities = condition["entities"]
            context_entities = context.entities

            if not any(
                etype.upper() in [e.upper() for e in required_entities]
                for etype, _ in context_entities
            ):
                return False

        # 检查关键词条件
        if "keywords" in condition:
            keywords = condition["keywords"]
            if not any(kw in context.text for kw in keywords):
                return False

        # 检查 POS 标签条件
        if "pos_tags" in condition:
            required_pos = condition["pos_tags"]
            pos_list = [pos for _, pos in context.pos_tags]

            if not any(pos in pos_list for pos in required_pos):
                return False

        # 检查依存关系条件
        if "dependencies" in condition:
            required_deps = condition["dependencies"]
            deps = context.dependencies

            if not any(dep.get("relation") in required_deps for dep in deps):
                return False

        # 检查主语条件
        if "subject" in condition:
            required_subjects = condition["subject"]
            subject = context.get_subject()

            if not subject or not any(subj in subject for subj in required_subjects):
                return False

        # 检查谓语条件
        if "predicate" in condition:
            required_predicates = condition["predicate"]
            predicate = context.get_predicate()

            if not predicate or not any(pred in predicate for pred in required_predicates):
                return False

        # 检查宾语条件
        if "object" in condition:
            required_objects = condition["object"]
            obj = context.get_object()

            if not obj or not any(o in obj for o in required_objects):
                return False

        # 检查三元组条件
        if "triples" in condition:
            required_triples = condition["triples"]
            triples = context.triples

            if not triples:
                return False

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
            semantic_roles = context.semantic_roles

            if not semantic_roles:
                return False

            for role in semantic_roles:
                if isinstance(role, dict):
                    if role.get("role_type") in required_roles:
                        return True
                elif isinstance(role, str):
                    if role in required_roles:
                        return True
            return False

        # 检查语义依存条件
        if "semantic_deps" in condition:
            required_deps = condition["semantic_deps"]
            semantic_deps = context.semantic_deps

            if not semantic_deps:
                return False

            for dep in semantic_deps:
                if isinstance(dep, dict):
                    if dep.get("relation") in required_deps:
                        return True
                elif isinstance(dep, str):
                    if dep in required_deps:
                        return True
            return False

        # 检查分词数量范围
        if "min_tokens" in condition:
            if len(context.tokens) < condition["min_tokens"]:
                return False

        if "max_tokens" in condition:
            if len(context.tokens) > condition["max_tokens"]:
                return False

        # 检查对话轮数范围
        if "min_turns" in condition:
            if context.turn_count < condition["min_turns"]:
                return False

        if "max_turns" in condition:
            if context.turn_count > condition["max_turns"]:
                return False

        return True
    
    def _calculate_confidence(
        self,
        intent: ScriptIntent,
        context: ScriptContext,
    ) -> float:
        """
        计算匹配置信度
        
        Args:
            intent: 意图
            context: 上下文
            
        Returns:
            置信度 (0.0 - 1.0)
        """
        # 基础置信度基于优先级
        base_confidence = min(intent.priority / 100.0, 1.0)
        
        # 关键词匹配奖励
        condition = intent.condition or {}
        keywords = condition.get("keywords", [])
        if keywords:
            matched_keywords = sum(1 for kw in keywords if kw in context.text)
            if matched_keywords > 0:
                keyword_bonus = min(matched_keywords * 0.1, 0.3)
                base_confidence += keyword_bonus
        
        # 实体匹配奖励
        entities = condition.get("entities", [])
        if entities:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _select_template(self, intent: ScriptIntent) -> str:
        """
        选择响应模板
        
        使用加权随机选择，避免重复。
        
        Args:
            intent: 意图
            
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
        context: ScriptContext,
    ) -> str:
        """
        填充模板占位符

        支持的占位符:
        - {entity_TYPE}: 命名实体（如 {entity_PERSON}）
        - {subject}: 主语
        - {predicate}: 谓语
        - {object}: 宾语
        - {token_N}: 第 N 个分词
        - {first_token}: 第一个分词
        - {last_token}: 最后一个分词
        - {pos_X}: 特定词性的词（如 {pos_v} 动词，{pos_n} 名词）
        - {dep_REL}: 特定依存关系的词（如 {dep_SBV} 主谓关系）
        - {triple_subject}: 三元组中的主语
        - {triple_object}: 三元组中的宾语
        - {triple_predicate}: 三元组中的谓语
        - {role_ROLE}: 特定语义角色的词（如 {role_A0} 施事）
        - {sdp_REL}: 特定语义依存关系的词
        - {turn_count}: 对话轮数
        - {time_KEY}: 时间变量（如 {time_hour}）
        - {user_KEY}: 用户信息（如 {user_name}）
        - {var_KEY}: 脚本变量（如 {var_mood}）

        Args:
            template: 模板字符串
            context: 上下文

        Returns:
            填充后的字符串
        """
        result = template

        # 填充命名实体 {entity_TYPE}
        entity_pattern = re.compile(r"\{entity_(\w+)\}", re.IGNORECASE)
        for match in entity_pattern.finditer(template):
            entity_type = match.group(1).upper()
            entity_text = context.get_first_entity(entity_type) or ""
            result = result.replace(match.group(0), entity_text)

        # 填充句法成分
        if context.get_subject():
            result = result.replace("{subject}", context.get_subject())
        if context.get_predicate():
            result = result.replace("{predicate}", context.get_predicate())
        if context.get_object():
            result = result.replace("{object}", context.get_object())

        # 填充分词
        if context.tokens:
            result = result.replace("{first_token}", context.tokens[0])
            result = result.replace("{last_token}", context.tokens[-1])

        token_pattern = re.compile(r"\{token_(\d+)\}")
        for match in token_pattern.finditer(template):
            idx = int(match.group(1))
            if 0 <= idx < len(context.tokens):
                result = result.replace(match.group(0), context.tokens[idx])

        # 填充 POS 占位符 {pos_X}
        pos_pattern = re.compile(r"\{pos_(\w+)\}", re.IGNORECASE)
        for match in pos_pattern.finditer(template):
            pos_tag = match.group(1).lower()
            for token, token_pos in context.pos_tags:
                if token_pos.lower() == pos_tag:
                    result = result.replace(match.group(0), token)
                    break

        # 填充依存关系占位符 {dep_REL}
        dep_pattern = re.compile(r"\{dep_(\w+)\}", re.IGNORECASE)
        for match in dep_pattern.finditer(template):
            dep_rel = match.group(1).upper()
            for dep in context.dependencies:
                if dep.get("relation", "").upper() == dep_rel:
                    result = result.replace(match.group(0), dep.get("word", dep.get("dependent", "")))
                    break

        # 填充三元组占位符
        triples = context.triples
        if triples:
            first_triple = triples[0]
            if len(first_triple) >= 3:
                if "{triple_subject}" in result:
                    result = result.replace("{triple_subject}", first_triple[0] or "")
                if "{triple_predicate}" in result:
                    result = result.replace("{triple_predicate}", first_triple[1] or "")
                if "{triple_object}" in result:
                    result = result.replace("{triple_object}", first_triple[2] or "")

        # 填充语义角色占位符 {role_ROLE}
        role_pattern = re.compile(r"\{role_(\w+)\}", re.IGNORECASE)
        for match in role_pattern.finditer(template):
            role_type = match.group(1).upper()
            for role in context.semantic_roles:
                if isinstance(role, dict):
                    if role.get("role_type", "").upper() == role_type:
                        result = result.replace(match.group(0), role.get("text", ""))
                        break
                elif isinstance(role, str):
                    # 旧格式：直接是角色类型字符串
                    if role.upper() == role_type:
                        result = result.replace(match.group(0), role)
                        break

        # 填充语义依存占位符 {sdp_REL}
        sdp_pattern = re.compile(r"\{sdp_(\w+)\}", re.IGNORECASE)
        for match in sdp_pattern.finditer(template):
            sdp_rel = match.group(1).upper()
            for dep in context.semantic_deps:
                if isinstance(dep, dict):
                    if dep.get("relation", "").upper() == sdp_rel:
                        result = result.replace(match.group(0), dep.get("dependent", dep.get("word", "")))
                        break

        # 填充对话轮数
        result = result.replace("{turn_count}", str(context.turn_count))

        # 填充时间变量 {time_KEY}
        time_pattern = re.compile(r"\{time_(\w+)\}", re.IGNORECASE)
        for match in time_pattern.finditer(template):
            key = match.group(1).lower()
            value = context.get_time(key, "")
            result = result.replace(match.group(0), str(value))

        # 填充用户信息 {user_KEY}
        user_pattern = re.compile(r"\{user_(\w+)\}", re.IGNORECASE)
        for match in user_pattern.finditer(template):
            key = match.group(1).lower()
            value = context.get_user_info(key, "")
            result = result.replace(match.group(0), str(value))

        # 填充脚本变量 {var_KEY}
        var_pattern = re.compile(r"\{var_(\w+)\}", re.IGNORECASE)
        for match in var_pattern.finditer(template):
            key = match.group(1).lower()
            value = context.get_variable(key, "")
            result = result.replace(match.group(0), str(value))

        # 清理未匹配的占位符
        result = re.sub(r"\{[^}]+\}", "", result)

        return result
    
    # =========================================================================
    # 额外方法
    # =========================================================================
    
    def get_intent(self, intent_name: str) -> Optional[ScriptIntent]:
        """获取意图"""
        return self._intents.get(intent_name)
    
    def get_intents(self) -> Dict[str, ScriptIntent]:
        """获取所有意图"""
        return self._intents.copy()
    
    def get_intent_names(self) -> List[str]:
        """获取所有意图名称"""
        return list(self._intents.keys())
    
    def load_from_config_file(self, config_path: Path) -> int:
        """
        从配置文件加载
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            成功加载的脚本数量
        """
        configs = self.config_loader.load_from_yaml(config_path)
        count = 0
        for config in configs:
            if config.script_type == 'yaml' and self.load_script(config):
                count += 1
        return count
