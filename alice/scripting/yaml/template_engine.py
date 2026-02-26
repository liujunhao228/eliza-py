#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板引擎模块

负责响应模板的选择和填充。
"""

import logging
import random
import re
from typing import Any, Dict, Optional

from alice.scripting.context import ScriptContext
from alice.scripting.yaml.parser import ScriptIntent

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    模板引擎

    功能:
    - 响应模板选择
    - 占位符填充
    - 重组引擎集成
    """

    def __init__(self, reassembly_engine: Optional[Any] = None):
        """
        初始化模板引擎

        Args:
            reassembly_engine: 句法重组引擎实例（用于代词替换）
        """
        self.reassembly_engine = reassembly_engine

    def set_reassembly_engine(self, reassembly_engine: Any) -> None:
        """设置重组引擎"""
        self.reassembly_engine = reassembly_engine

    def select_template(self, intent: ScriptIntent) -> str:
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

    def fill_template(
        self,
        template: str,
        context: ScriptContext,
        keyword_only: bool = False,
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
        - {pos_X}: 特定词性的词（如 {pos_v} 动词）
        - {dep_REL}: 特定依存关系的词
        - {triple_subject/predicate/object}: 三元组成分
        - {role_ROLE}: 特定语义角色的词
        - {sdp_REL}: 特定语义依存关系的词
        - {turn_count}: 对话轮数
        - {time_KEY}: 时间变量
        - {user_KEY}: 用户信息
        - {var_KEY}: 脚本变量

        Args:
            template: 模板字符串
            context: 上下文
            keyword_only: 是否仅关键词匹配（不进行代词替换）

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

    def generate_with_reassembly(
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
            return self.fill_template(template, context)

        # 先填充实体占位符
        filled_template = self.fill_template(template, context)

        # 使用重组引擎应用代词映射
        response = self.reassembly_engine.reassemble(
            components=[user_input],
            reassembly_rule=filled_template,
            apply_pronoun_mapping=True,
        )

        return response.strip() if response else filled_template
