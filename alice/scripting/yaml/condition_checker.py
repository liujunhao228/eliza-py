#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条件检查器模块

负责检查 YAML 脚本意图的匹配条件。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from alice.scripting.context import ScriptContext
from alice.scripting.yaml.parser import ScriptIntent

logger = logging.getLogger(__name__)


class ConditionChecker:
    """
    条件检查器

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
    """

    def check(self, intent: ScriptIntent, context: ScriptContext) -> bool:
        """
        检查条件是否满足

        Args:
            intent: 意图
            context: 脚本上下文

        Returns:
            条件是否满足
        """
        condition = intent.condition

        if condition is None:
            return True  # 无条件，总是匹配

        # 按顺序检查所有条件类型
        checks = [
            self._check_entities,
            self._check_keywords,
            self._check_pos_tags,
            self._check_dependencies,
            self._check_subject,
            self._check_predicate,
            self._check_object,
            self._check_triples,
            self._check_semantic_roles,
            self._check_semantic_deps,
            self._check_token_count,
            self._check_turn_count,
            self._check_time,  # 新增：时间检查
        ]

        for check in checks:
            if not check(condition, context):
                return False

        return True

    def _check_entities(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查实体条件"""
        if "entities" not in condition:
            return True

        required_entities = condition["entities"]
        context_entities = context.entities

        return any(
            etype.upper() in [e.upper() for e, _ in context_entities]
            for etype in required_entities
        )

    def _check_keywords(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查关键词条件"""
        if "keywords" not in condition:
            return True

        keywords = condition["keywords"]
        return any(kw in context.text for kw in keywords)

    def _check_pos_tags(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查词性标签条件"""
        if "pos_tags" not in condition:
            return True

        required_pos = condition["pos_tags"]
        pos_list = [pos for _, pos in context.pos_tags]

        return any(pos in pos_list for pos in required_pos)

    def _check_dependencies(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查依存关系条件"""
        if "dependencies" not in condition:
            return True

        required_deps = condition["dependencies"]
        deps = context.dependencies

        return any(dep.get("relation") in required_deps for dep in deps)

    def _check_subject(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查主语条件"""
        if "subject" not in condition:
            return True

        required_subjects = condition["subject"]
        subject = context.get_subject()

        return subject and any(subj in subject for subj in required_subjects)

    def _check_predicate(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查谓语条件"""
        if "predicate" not in condition:
            return True

        required_predicates = condition["predicate"]
        predicate = context.get_predicate()

        return predicate and any(pred in predicate for pred in required_predicates)

    def _check_object(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查宾语条件"""
        if "object" not in condition:
            return True

        required_objects = condition["object"]
        obj = context.get_object()

        return obj and any(o in obj for o in required_objects)

    def _check_triples(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查三元组条件"""
        if "triples" not in condition:
            return True

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

        return True

    def _check_semantic_roles(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查语义角色条件"""
        if "semantic_roles" not in condition:
            return True

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

    def _check_semantic_deps(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查语义依存条件"""
        if "semantic_deps" not in condition:
            return True

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

    def _check_token_count(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查分词数量范围"""
        if "min_tokens" in condition:
            if len(context.tokens) < condition["min_tokens"]:
                return False

        if "max_tokens" in condition:
            if len(context.tokens) > condition["max_tokens"]:
                return False

        return True

    def _check_turn_count(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """检查对话轮数范围"""
        if "min_turns" in condition:
            if context.turn_count < condition["min_turns"]:
                return False

        if "max_turns" in condition:
            if context.turn_count > condition["max_turns"]:
                return False

        return True

    def _check_time(self, condition: Dict[str, Any], context: ScriptContext) -> bool:
        """
        检查时间条件

        支持的条件:
        - hour_gte: 小时大于等于
        - hour_gt: 小时大于
        - hour_lt: 小时小于
        - hour_lte: 小时小于等于
        - hour_eq: 小时等于
        - weekday_gte: 星期几大于等于 (0=周一，6=周日)
        - weekday_gt: 星期几大于
        - weekday_lt: 星期几小于
        - weekday_lte: 星期几小于等于
        - weekday_eq: 星期几等于

        Args:
            condition: 条件字典
            context: 脚本上下文

        Returns:
            条件是否满足
        """
        current_hour = datetime.now().hour
        current_weekday = datetime.now().weekday()

        # 检查小时条件
        if "hour_gte" in condition:
            if current_hour < condition["hour_gte"]:
                return False

        if "hour_gt" in condition:
            if current_hour <= condition["hour_gt"]:
                return False

        if "hour_lt" in condition:
            if current_hour >= condition["hour_lt"]:
                return False

        if "hour_lte" in condition:
            if current_hour > condition["hour_lte"]:
                return False

        if "hour_eq" in condition:
            if current_hour != condition["hour_eq"]:
                return False

        # 检查星期条件
        if "weekday_gte" in condition:
            if current_weekday < condition["weekday_gte"]:
                return False

        if "weekday_gt" in condition:
            if current_weekday <= condition["weekday_gt"]:
                return False

        if "weekday_lt" in condition:
            if current_weekday >= condition["weekday_lt"]:
                return False

        if "weekday_lte" in condition:
            if current_weekday > condition["weekday_lte"]:
                return False

        if "weekday_eq" in condition:
            if current_weekday != condition["weekday_eq"]:
                return False

        return True
