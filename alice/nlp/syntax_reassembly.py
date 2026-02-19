#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句法重组引擎模块

基于依存句法分析结果进行 Eliza 风格的组件重组
支持 {SUBJ}, {PRED}, {OBJ} 等句法占位符
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

from alice.nlp.base import SyntaxStructure

logger = logging.getLogger(__name__)


class SyntaxReassembly:
    """
    句法重组引擎

    功能:
    - 支持 Eliza 风格的 {1}, {2}, {3} 组件引用
    - 支持 LTP 句法占位符 {SUBJ}, {PRED}, {OBJ}
    - 代词映射转换
    """

    # 默认代词映射
    DEFAULT_PRONOUN_MAPPING = {
        '我': '你',
        '你': '我',
        '他': '你',
        '她': '你',
        '它': '你',
        '我们': '你们',
        '你们': '我们',
        '他们': '你们',
        '她们': '你们',
    }

    # 默认转换规则
    DEFAULT_TRANSFORMATION_RULES = [
        (r'我觉得', '你为什么觉得'),
        (r'我认为', '你为什么认为'),
        (r'我想', '你为什么想'),
        (r'我喜欢', '你为什么喜欢'),
        (r'我讨厌', '你为什么讨厌'),
    ]

    def __init__(
        self,
        rules_file: Optional[str] = None,
        pronoun_mapping: Optional[Dict[str, str]] = None,
    ):
        """
        初始化句法重组引擎

        Args:
            rules_file: 反射规则文件路径
            pronoun_mapping: 代词映射配置
        """
        self.pronoun_mapping = dict(self.DEFAULT_PRONOUN_MAPPING)
        if pronoun_mapping:
            self.pronoun_mapping.update(pronoun_mapping)

        self.transformation_rules = list(self.DEFAULT_TRANSFORMATION_RULES)

        if rules_file:
            self._load_rules(rules_file)

    def _load_rules(self, rules_file: str) -> None:
        """从配置文件加载规则"""
        path = Path(rules_file)
        if not path.exists():
            logger.warning(f"规则文件不存在：{rules_file}")
            return

        try:
            import json
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载代词映射
            pronoun_config = config.get('pronoun_mapping', {})
            if pronoun_config:
                self.pronoun_mapping.update(pronoun_config)

            # 加载转换规则
            rules_config = config.get('transformation_rules', [])
            if rules_config:
                self.transformation_rules = [
                    (pattern, replacement)
                    for pattern, replacement in rules_config
                ]

            logger.info(f"已从 {rules_file} 加载反射规则")

        except Exception as e:
            logger.warning(f"加载规则文件失败：{e}，使用默认配置")

    def reassemble(
        self,
        components: List[str],
        reassembly_rule: str,
        apply_pronoun_mapping: bool = True,
        syntax_structure: Optional[SyntaxStructure] = None,
    ) -> str:
        """
        根据重组规则组装响应

        Args:
            components: 分解组件列表，如 ["", "难过"]
            reassembly_rule: 重组规则，如 "你为什么觉得{2}呢？"
            apply_pronoun_mapping: 是否应用代词映射
            syntax_structure: 句法分析结果

        Returns:
            组装后的响应
        """
        response = reassembly_rule

        # 1. 处理组件引用 {1}, {2}, {3}...
        for i, component in enumerate(components, 1):
            placeholder = f'{{{i}}}'
            if placeholder in response:
                if apply_pronoun_mapping:
                    component = self._apply_pronoun_mapping(component)
                response = response.replace(placeholder, component or '')

        # 2. 处理句法占位符 {SUBJ}, {PRED}, {OBJ}
        if syntax_structure:
            if '{SUBJ}' in response:
                response = response.replace(
                    '{SUBJ}',
                    syntax_structure.subject or '',
                )
            if '{PRED}' in response:
                response = response.replace(
                    '{PRED}',
                    syntax_structure.predicate or '',
                )
            if '{OBJ}' in response:
                response = response.replace(
                    '{OBJ}',
                    syntax_structure.object or '',
                )

            # 处理修饰语 {MOD:word}
            for match in re.finditer(r'\{MOD:(\w+)\}', response):
                head_word = match.group(1)
                modifiers = syntax_structure.modifiers.get(head_word, [])
                modifier_text = '、'.join(modifiers) if modifiers else ''
                response = response.replace(match.group(0), modifier_text)

        # 3. 应用转换规则
        if apply_pronoun_mapping:
            for pattern, replacement in self.transformation_rules:
                response = re.sub(pattern, replacement, response)

        return response.strip()

    def _apply_pronoun_mapping(self, text: str) -> str:
        """
        应用代词映射转换

        Args:
            text: 待转换文本

        Returns:
            转换后文本
        """
        result = text
        # 按长度排序，优先替换长的代词
        sorted_pronouns = sorted(
            self.pronoun_mapping.keys(),
            key=len,
            reverse=True,
        )
        for pronoun in sorted_pronouns:
            if pronoun in result:
                mapped = self.pronoun_mapping[pronoun]
                result = result.replace(pronoun, mapped)
        return result

    def reassemble_with_syntax(
        self,
        user_input: str,
        syntax: SyntaxStructure,
        response_template: str,
    ) -> str:
        """
        使用句法结构重组响应

        Args:
            user_input: 用户输入
            syntax: 句法分析结果
            response_template: 响应模板

        Returns:
            重组后的响应
        """
        # 提取组件（简单分词）
        components = ['', syntax.subject, syntax.predicate, syntax.object]

        return self.reassemble(
            components=components,
            reassembly_rule=response_template,
            syntax_structure=syntax,
        )

    def get_response(
        self,
        user_input: str,
        syntax: Optional[SyntaxStructure],
        patterns_responses: List[tuple],
    ) -> str:
        """
        根据模式 - 响应列表生成响应

        Args:
            user_input: 用户输入
            syntax: 句法分析结果
            patterns_responses: [(pattern, response_template), ...]

        Returns:
            生成的响应
        """
        for pattern, response_template in patterns_responses:
            match = re.search(pattern, user_input)
            if match:
                components = list(match.groups()) if match.groups() else ['']
                return self.reassemble(
                    components=components,
                    reassembly_rule=response_template,
                    syntax_structure=syntax,
                )

        # 无匹配时返回默认响应
        return "我理解了。能详细说说吗？"
