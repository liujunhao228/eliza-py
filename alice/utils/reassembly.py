#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重组引擎 - 支持 Eliza 风格的组件引用语法和 LTP 依存句法分析

功能:
- 根据分解组件和重组规则生成动态响应
- 支持 {1}, {2}, {3} 等组件引用语法
- 支持代词映射转换
- 支持 LTP 依存句法分析结果（{SUBJ}, {PRED}, {OBJ} 等）
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any

# 导入统一配置
from alice.config import PRONOUN_MAPPING, TRANSFORMATION_RULES


class ReassemblyEngine:
    """重组引擎 - 根据分解组件生成动态响应"""

    def __init__(self, rules_file: Optional[str] = None,
                 syntax_structure: Optional[Dict[str, str]] = None):
        """
        初始化重组引擎

        参数:
            rules_file: 反射规则配置文件路径，如 None 则使用默认规则
            syntax_structure: 句法分析结果（包含 subject, predicate, object 等）
        """
        self.pronoun_mapping = dict(PRONOUN_MAPPING)
        self.transformation_rules = list(TRANSFORMATION_RULES)
        self.syntax_structure = syntax_structure or {}
        self._load_rules(rules_file)

    def _load_rules(self, rules_file: Optional[str]):
        """从配置文件加载规则"""
        if rules_file and Path(rules_file).exists():
            try:
                import json
                with open(rules_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 从配置文件加载的规则会覆盖默认配置
                    pronoun_config = config.get('pronoun_mapping', {})
                    if pronoun_config:
                        self.pronoun_mapping = pronoun_config
                    rules_config = config.get('transformation_rules', [])
                    if rules_config:
                        self.transformation_rules = [
                            (pattern, replacement)
                            for pattern, replacement in rules_config
                        ]
                return
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载规则文件失败：{e}，使用默认配置")

    def reassemble(self, components: List[str], reassembly_rule: str,
                   apply_pronoun_mapping: bool = True,
                   syntax_structure: Optional[Dict[str, str]] = None) -> str:
        """
        根据重组规则组装响应

        参数:
            components: 分解组件列表，如 ["", "难过"]
            reassembly_rule: 重组规则，如 "你为什么觉得{2}呢？"
            apply_pronoun_mapping: 是否应用代词映射
            syntax_structure: 句法分析结果（包含 subject, predicate, object 等）

        返回:
            组装后的响应，如 "你为什么觉得难过呢？"

        示例:
            >>> engine = ReassemblyEngine()
            >>> engine.reassemble(["", "难过"], "你为什么觉得{2}呢？")
            '你为什么觉得难过呢？'
        """
        response = reassembly_rule

        # 更新句法结构（如果提供）
        if syntax_structure:
            self.syntax_structure = syntax_structure

        # 替换组件引用 {1}, {2}, {3}...
        for i, comp in enumerate(components, 1):
            placeholder = f'{{{i}}}'
            # 清理组件中的多余空白
            cleaned_comp = ' '.join(comp.strip().split()) if comp else ''

            # 应用代词映射
            if apply_pronoun_mapping and self.pronoun_mapping:
                cleaned_comp = self._apply_pronoun_mapping_to_component(cleaned_comp)

            response = response.replace(placeholder, cleaned_comp)

        # 替换句法成分占位符 {SUBJ}, {PRED}, {OBJ} 等
        response = self._replace_syntax_placeholders(response, apply_pronoun_mapping)

        # 处理未匹配的占位符（移除）
        response = re.sub(r'\{\d+\}', '', response)

        return response.strip()

    def _apply_pronoun_mapping_to_component(self, text: str) -> str:
        """
        对组件应用代词映射

        参数:
            text: 组件文本

        返回:
            代词转换后的文本
        """
        transformed = text
        # 按长度降序匹配，优先匹配长的代词
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)
        return transformed

    def _replace_syntax_placeholders(self, text: str,
                                      apply_pronoun_mapping: bool = True) -> str:
        """
        替换句法成分占位符

        支持的占位符:
            {SUBJ} - 主语
            {PRED} - 谓语
            {OBJ} - 宾语
            {ATT} - 定语
            {ADV} - 状语

        参数:
            text: 包含占位符的文本
            apply_pronoun_mapping: 是否应用代词映射

        返回:
            替换后的文本
        """
        replacements = {
            '{SUBJ}': self.syntax_structure.get('subject', ''),
            '{PRED}': self.syntax_structure.get('predicate', ''),
            '{OBJ}': self.syntax_structure.get('object', ''),
            '{ATT}': self.syntax_structure.get('attribute', ''),
            '{ADV}': self.syntax_structure.get('adverbial', ''),
        }

        for placeholder, value in replacements.items():
            if value:
                transformed_value = self._apply_pronoun_mapping_to_component(value) if apply_pronoun_mapping else value
                text = text.replace(placeholder, transformed_value)
            else:
                # 移除未匹配的占位符
                text = text.replace(placeholder, '')

        return text

    def transform(self, text: str) -> str:
        """
        执行反射转换（代词映射 + 句式转换）

        参数:
            text: 原始文本

        返回:
            转换后的文本
        """
        transformed = text

        # 1. 应用代词映射（按长度降序，优先匹配长的）
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)

        # 2. 应用句式转换规则
        for pattern, replacement in self.transformation_rules:
            match = re.search(pattern, transformed)
            if match:
                # 提取捕获组
                components = match.groups()
                # 替换占位符
                for i, comp in enumerate(components, 1):
                    placeholder = f'{{{i}}}'
                    replacement = replacement.replace(placeholder, comp if comp else '')
                transformed = re.sub(pattern, replacement, transformed)
                break

        return transformed

    def apply_pronoun_mapping(self, text: str) -> str:
        """
        仅应用代词映射（不进行句式转换）

        参数:
            text: 原始文本

        返回:
            代词转换后的文本
        """
        transformed = text
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)
        return transformed


class DecompositionMatcher:
    """分解规则匹配器 - 将 Weizenbaum 表示法转换为正则表达式"""

    def __init__(self, tags: Optional[Dict[str, List[str]]] = None):
        """
        初始化分解规则匹配器

        参数:
            tags: 语义标签字典，如 {'family': ['母亲', '父亲', '姐姐']}
        """
        self.tags = tags or {}

    def match(self, text: str, decomp_pattern: str) -> Optional[List[str]]:
        """
        匹配分解规则

        参数:
            text: 待匹配的文本
            decomp_pattern: 分解规则（支持 Weizenbaum 表示法或正则表达式）

        返回:
            匹配成功的组件列表，失败则返回 None
        """
        # 尝试直接作为正则表达式匹配
        try:
            pattern = self._convert_to_regex(decomp_pattern)
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return list(match.groups())
        except re.error:
            pass

        return None

    def _convert_to_regex(self, pattern: str) -> str:
        """
        将 Weizenbaum 表示法转换为正则表达式

        Weizenbaum 表示法示例:
            (0 YOU 0) → 匹配包含 "you" 的句子
            (0 I AM 0) → 匹配包含 "I am" 的句子
            (0 YOUR @FAMILY 0 YOU) → 使用语义标签

        参数:
            pattern: Weizenbaum 表示法模式

        返回:
            正则表达式模式
        """
        # 移除外层括号
        pattern = pattern.strip()
        if pattern.startswith('(') and pattern.endswith(')'):
            pattern = pattern[1:-1]

        # 分割为组件
        components = pattern.split()
        regex_parts = []

        for comp in components:
            if comp == '0':
                # 0 = 任意数量单词
                regex_parts.append(r'(.*?)')
            elif comp.isdigit() and int(comp) > 0:
                # 正整数 = 特定数量单词
                n = int(comp)
                regex_parts.append(r'((?:\S+\s+){' + str(n - 1) + r'}\S+)')
            elif comp.startswith('@'):
                # @TAG = 语义标签
                tag_name = comp[1:].lower()
                if tag_name in self.tags:
                    tag_words = '|'.join(re.escape(w) for w in self.tags[tag_name])
                    regex_parts.append(r'(' + tag_words + r')')
                else:
                    regex_parts.append(r'(\S+)')
            else:
                # 普通单词
                regex_parts.append(r'(' + re.escape(comp) + r')')

        return r'\s*'.join(regex_parts)


class ReassemblyRuleSelector:
    """重组规则选择器 - 管理重组规则的轮换和去重"""

    def __init__(self, rules: List[str]):
        """
        初始化重组规则选择器

        参数:
            rules: 重组规则列表
        """
        self.rules = rules
        self.last_used_index = -1
        self.last_used_rule = None

    def select(self, avoid_repeats: bool = True) -> Optional[str]:
        """
        选择一条重组规则

        参数:
            avoid_repeats: 是否避免重复使用同一条规则

        返回:
            选中的重组规则
        """
        if not self.rules:
            return None

        if not avoid_repeats or len(self.rules) == 1:
            self.last_used_index = (self.last_used_index + 1) % len(self.rules)
            self.last_used_rule = self.rules[self.last_used_index]
            return self.last_used_rule

        # 避免重复：选择一个未使用的规则
        available_indices = [
            i for i in range(len(self.rules))
            if i != self.last_used_index
        ]

        if not available_indices:
            # 所有规则都已使用，循环回到第一个
            self.last_used_index = 0
        else:
            import random
            self.last_used_index = random.choice(available_indices)

        self.last_used_rule = self.rules[self.last_used_index]
        return self.last_used_rule

    def reset(self):
        """重置选择器状态"""
        self.last_used_index = -1
        self.last_used_rule = None
