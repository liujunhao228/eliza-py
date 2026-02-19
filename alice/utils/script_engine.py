#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用脚本引擎模块 - 支持 Eliza 风格的脚本匹配和重组规则

功能:
- 加载和管理脚本配置文件
- 根据正则表达式模式匹配用户输入
- 支持重组规则生成动态响应
- 支持响应轮换和去重
"""

import json
import os
import re
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScriptMatch:
    """脚本匹配结果"""
    script_id: str
    script_name: str
    priority: int
    matched_pattern: str
    components: List[str]
    responses: List[str]
    reassembly_rules: Optional[List[str]] = None


class ScriptEngine:
    """
    通用脚本引擎 - 管理脚本匹配和响应生成
    
    支持功能:
    - 脚本配置文件加载
    - 正则表达式模式匹配
    - 优先级排序
    - 重组规则支持
    - 响应轮换和去重
    """

    def __init__(self, script_file: Optional[str] = None):
        """
        初始化脚本引擎

        参数:
            script_file: 脚本配置文件路径 (JSON 格式)
        """
        self.script_file = script_file
        self.scripts: Dict[str, Dict] = {}
        self.script_order: List[str] = []  # 按优先级排序的脚本 ID
        
        # 响应历史（用于去重）
        self.last_used_responses: Dict[str, str] = {}
        self.script_history: Dict[str, int] = {}
        
        # 加载脚本配置
        if script_file:
            self._load_scripts(script_file)

    def _load_scripts(self, script_file: str):
        """
        从 JSON 文件加载脚本配置

        参数:
            script_file: 脚本文件路径

        异常:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式无效
        """
        if not os.path.exists(script_file):
            raise FileNotFoundError(f"脚本文件不存在：{script_file}")

        with open(script_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        scripts_data = config.get('scripts', {})
        
        # 验证并加载每个脚本
        for script_id, script_data in scripts_data.items():
            self._validate_script(script_id, script_data)
            self.scripts[script_id] = script_data
        
        # 按优先级排序（优先级高的先匹配）
        self._sort_scripts_by_priority()

    def _validate_script(self, script_id: str, script_data: Dict):
        """
        验证脚本配置的有效性

        参数:
            script_id: 脚本 ID
            script_data: 脚本数据

        异常:
            ValueError: 脚本配置无效
        """
        required_fields = ['patterns', 'responses']
        for field in required_fields:
            if field not in script_data:
                raise ValueError(f"脚本 '{script_id}' 缺少必需字段：{field}")

        # fallback 脚本允许 patterns 为空（作为默认响应）
        is_fallback = script_data.get('is_fallback', False)
        if not is_fallback:
            if not isinstance(script_data['patterns'], list) or len(script_data['patterns']) == 0:
                raise ValueError(f"脚本 '{script_id}' 的 patterns 必须是非空列表")

        if not isinstance(script_data['responses'], list) or len(script_data['responses']) == 0:
            raise ValueError(f"脚本 '{script_id}' 的 responses 必须是非空列表")

    def _sort_scripts_by_priority(self):
        """按优先级对脚本进行排序（优先级高的在前）"""
        self.script_order = sorted(
            self.scripts.keys(),
            key=lambda sid: self.scripts[sid].get('priority', 0),
            reverse=True
        )

    def match(self, text: str) -> Optional[ScriptMatch]:
        """
        匹配最适合的脚本

        匹配规则:
        - 按优先级从高到低遍历脚本
        - 对每个脚本的所有模式进行匹配
        - 返回第一个匹配成功的脚本
        - default 脚本（标记为 is_fallback）作为最后备选，无模式时触发

        参数:
            text: 待匹配的文本

        返回:
            ScriptMatch 对象，无匹配返回 None
        """
        # 首先尝试匹配所有非 fallback 脚本
        for script_id in self.script_order:
            script = self.scripts[script_id]
            
            # 跳过 fallback 脚本（留给最后处理）
            if script.get('is_fallback', False):
                continue
            
            patterns = script.get('patterns', [])
            
            for pattern in patterns:
                match_result = self._match_pattern(text, pattern)
                if match_result is not None:
                    components = list(match_result.groups()) if match_result.groups() else [text]
                    
                    return ScriptMatch(
                        script_id=script_id,
                        script_name=script.get('name', script_id),
                        priority=script.get('priority', 0),
                        matched_pattern=pattern,
                        components=components,
                        responses=script.get('responses', []),
                        reassembly_rules=script.get('reassembly_rules')
                    )
        
        # 无匹配时，检查是否有 fallback 脚本
        fallback_script = self._get_fallback_script()
        if fallback_script:
            script_id, script = fallback_script
            return ScriptMatch(
                script_id=script_id,
                script_name=script.get('name', script_id),
                priority=script.get('priority', 0),
                matched_pattern='__fallback__',
                components=[text],
                responses=script.get('responses', []),
                reassembly_rules=script.get('reassembly_rules')
            )
        
        return None

    def _get_fallback_script(self) -> Optional[Tuple[str, Dict]]:
        """
        获取 fallback 脚本（用于无匹配时的默认响应）

        返回:
            (script_id, script_data) 元组，无 fallback 脚本返回 None
        """
        # 优先查找标记为 is_fallback 的脚本
        for script_id, script in self.scripts.items():
            if script.get('is_fallback', False):
                return (script_id, script)
        
        # 兼容旧版本：查找名为 'default' 的脚本
        if 'default' in self.scripts:
            return ('default', self.scripts['default'])
        
        return None

    def _match_pattern(self, text: str, pattern: str) -> Optional[re.Match]:
        """
        匹配单个模式

        参数:
            text: 待匹配的文本
            pattern: 正则表达式模式

        返回:
            匹配结果，失败返回 None
        """
        try:
            return re.search(pattern, text, re.IGNORECASE)
        except re.error:
            return None

    def select_response(self, match: ScriptMatch, 
                        use_reassembly: bool = True,
                        use_responses: bool = True) -> Optional[str]:
        """
        从匹配的脚本中选择响应

        参数:
            match: 脚本匹配结果
            use_reassembly: 是否使用重组规则生成响应
            use_responses: 是否使用预定义响应列表

        返回:
            选中的响应文本
        """
        response = None
        
        # 优先使用重组规则（如果可用）
        if use_reassembly and match.reassembly_rules and match.components:
            response = self._generate_reassembly_response(match)
        
        # 如果重组失败或未启用，使用预定义响应
        if response is None and use_responses and match.responses:
            response = self._select_from_responses(match)
        
        # 更新历史记录
        if response and match.script_id:
            self.last_used_responses[match.script_id] = response
            self.script_history[match.script_id] = self.script_history.get(match.script_id, 0) + 1
        
        return response

    def _generate_reassembly_response(self, match: ScriptMatch) -> Optional[str]:
        """
        使用重组规则生成响应

        参数:
            match: 脚本匹配结果

        返回:
            生成的响应文本
        """
        if not match.reassembly_rules:
            return None
        
        # 选择一个重组规则（避免重复）
        rule = self._select_reassembly_rule(match.reassembly_rules, match.script_id)
        if not rule:
            return None
        
        # 替换占位符 {1}, {2}, {3}...
        response = rule
        for i, comp in enumerate(match.components, 1):
            placeholder = f'{{{i}}}'
            cleaned_comp = ' '.join(comp.strip().split()) if comp else ''
            # 应用代词映射
            cleaned_comp = self._apply_pronoun_mapping(cleaned_comp)
            response = response.replace(placeholder, cleaned_comp)
        
        # 清理未匹配的占位符
        response = re.sub(r'\{\d+\}', '', response)
        
        return response.strip() if response else None

    def _select_reassembly_rule(self, rules: List[str], script_id: str) -> Optional[str]:
        """
        选择一条重组规则（避免重复）

        参数:
            rules: 重组规则列表
            script_id: 脚本 ID

        返回:
            选中的规则
        """
        if not rules:
            return None
        
        # 获取上次使用的规则
        last_response = self.last_used_responses.get(script_id, '')
        
        # 尝试选择一个未使用的规则
        available_rules = [r for r in rules if r != last_response]
        
        if available_rules:
            selected = random.choice(available_rules)
        else:
            # 所有规则都已使用，随机选择一个
            selected = random.choice(rules)
        
        return selected

    def _select_from_responses(self, match: ScriptMatch) -> Optional[str]:
        """
        从预定义响应列表中选择一个响应

        参数:
            match: 脚本匹配结果

        返回:
            选中的响应文本
        """
        if not match.responses:
            return None
        
        # 获取上次使用的响应
        last_response = self.last_used_responses.get(match.script_id, '')
        
        # 尝试选择一个未使用的响应
        available_responses = [r for r in match.responses if r != last_response]
        
        if available_responses:
            selected = random.choice(available_responses)
        else:
            # 所有响应都已使用，随机选择一个
            selected = random.choice(match.responses)
        
        return selected

    def _apply_pronoun_mapping(self, text: str) -> str:
        """
        应用代词映射

        参数:
            text: 原始文本

        返回:
            代词转换后的文本
        """
        pronoun_mapping = {
            '我': '你',
            '我的': '你的',
            '我们': '你们',
            '我自己': '你自己',
            '我妈': '你妈',
            '我爸': '你爸',
            '我老婆': '你老婆',
            '我老公': '你老公',
            '我朋友': '你朋友',
            '我同事': '你同事',
            '我同学': '你同学',
            '我老板': '你老板',
            '我老师': '你老师',
        }
        
        transformed = text
        # 按长度降序匹配，优先匹配长的代词
        sorted_pronouns = sorted(pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)
        
        return transformed

    def match_and_respond(self, text: str, 
                          use_reassembly: bool = True,
                          use_responses: bool = True) -> Optional[str]:
        """
        匹配脚本并生成响应

        参数:
            text: 待匹配的文本
            use_reassembly: 是否使用重组规则
            use_responses: 是否使用预定义响应

        返回:
            生成的响应文本，无匹配返回 None
        """
        match = self.match(text)
        if not match:
            return None
        
        return self.select_response(match, use_reassembly, use_responses)

    def get_usage_statistics(self) -> Dict[str, int]:
        """
        获取脚本使用统计

        返回:
            脚本 ID 到使用次数的映射
        """
        return dict(self.script_history)

    def reset(self):
        """重置引擎状态"""
        self.last_used_responses.clear()
        self.script_history.clear()

    def reload_scripts(self):
        """重新加载脚本配置"""
        if self.script_file:
            self.scripts.clear()
            self.script_order.clear()
            self._load_scripts(self.script_file)
