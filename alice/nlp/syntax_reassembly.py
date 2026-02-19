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
from typing import List, Dict, Optional, Any, Tuple

from alice.nlp.base import SyntaxStructure

# 尝试导入 yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class SyntaxReassembly:
    """
    句法重组引擎

    功能:
    - 支持 Eliza 风格的 {1}, {2}, {3} 组件引用
    - 支持 LTP 句法占位符 {SUBJ}, {PRED}, {OBJ}
    - 代词映射转换

    配置说明:
    - 从 YAML 文件加载代词映射和转换规则
    - 配置文件格式参考 alice/scripts/mapping.yaml
    """

    def __init__(
        self,
        rules_file: Optional[str] = None,
        pronoun_mapping: Optional[Dict[str, str]] = None,
        transformation_rules: Optional[List[Tuple[str, str]]] = None,
    ):
        """
        初始化句法重组引擎

        Args:
            rules_file: YAML 规则文件路径（包含 pronoun_mapping 和 transformation_rules）
            pronoun_mapping: 代词映射配置（可选，用于覆盖 YAML 配置）
            transformation_rules: 转换规则（可选，用于覆盖 YAML 配置）
        """
        self.pronoun_mapping: Dict[str, str] = {}
        self.transformation_rules: List[Tuple[str, str]] = []

        if rules_file:
            self._load_rules(rules_file)

        # 可选：覆盖配置
        if pronoun_mapping:
            self.pronoun_mapping.update(pronoun_mapping)
        if transformation_rules:
            self.transformation_rules.extend(transformation_rules)

    def _load_rules(self, rules_file: str) -> None:
        """
        从 YAML 配置文件加载规则

        Args:
            rules_file: YAML 规则文件路径
        """
        if not YAML_AVAILABLE:
            logger.warning("PyYAML 未安装，无法加载 YAML 规则文件")
            return

        path = Path(rules_file)
        if not path.exists():
            logger.warning(f"规则文件不存在：{rules_file}")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning(f"规则文件为空：{rules_file}")
                return

            # 加载代词映射
            pronoun_config = config.get('pronoun_mapping', {})
            if pronoun_config:
                self.pronoun_mapping = dict(pronoun_config)
                logger.info(f"已加载 {len(self.pronoun_mapping)} 条代词映射规则")

            # 加载转换规则
            rules_config = config.get('transformation_rules', [])
            if rules_config:
                self.transformation_rules = [
                    (str(pattern), str(replacement))
                    for pattern, replacement in rules_config
                ]
                logger.info(f"已加载 {len(self.transformation_rules)} 条句式转换规则")

            logger.info(f"已从 {rules_file} 加载反射规则")

        except Exception as e:
            logger.warning(f"加载规则文件失败：{e}")

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
