#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好奇心插件模块

实现 Alice 的核心功能：好奇的朋友角色。
"""

import logging
import random
from typing import Any, Dict, List, Optional

from alice.plugins.base_plugin import BasePlugin, PluginResult
from alice.utils.script_engine import ScriptEngine
from alice.utils.reassembly import ReassemblyEngine

logger = logging.getLogger(__name__)


class CuriosityPlugin(BasePlugin):
    """
    好奇心插件
    
    实现 Alice 的核心对话功能：
    - 叙事助推：维持对话流
    - 实体深度挖掘：对人、事、物表现好奇
    - 情感镜像与验证：捕捉并反射情绪
    - 认知探索：引导用户思考
    - Meta 对话：处理对 Alice 的提问
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化好奇心插件
        
        Args:
            config: 配置字典，可包含：
                - script_file: 脚本文件路径
                - rules_file: 反射规则文件路径
                - priority: 插件优先级
        """
        default_config = {
            "script_file": None,
            "rules_file": None,
        }
        config = config or default_config
        
        super().__init__(config)
        self.priority = self.config.get("priority", 50)
        
        self.script_engine: Optional[ScriptEngine] = None
        self.reassembly_engine: Optional[ReassemblyEngine] = None
        self.script_history: Dict[str, int] = {}
        self.last_used_responses: Dict[str, str] = {}

    def initialize(self) -> bool:
        """初始化脚本引擎和重组引擎"""
        try:
            script_file = self.config.get("script_file")
            rules_file = self.config.get("rules_file")
            
            self.script_engine = ScriptEngine(script_file=script_file)
            self.reassembly_engine = ReassemblyEngine(rules_file=rules_file)
            
            logger.info("好奇心插件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"好奇心插件初始化失败：{e}")
            return False

    def process_input(self, text: str, context: Dict[str, Any]) -> PluginResult:
        """
        处理用户输入并生成响应
        
        Args:
            text: 用户输入文本
            context: 对话上下文
            
        Returns:
            插件处理结果
        """
        if not self.script_engine:
            return PluginResult(
                success=False,
                response="系统未初始化",
            )
        
        try:
            # 匹配脚本
            match = self.script_engine.match(text)
            
            if not match:
                return PluginResult(
                    success=False,
                    response=None,
                )
            
            # 生成响应
            response = self._generate_response(match)
            
            if response:
                # 更新历史记录
                self.script_history = self.script_engine.get_usage_statistics()
                if match.script_id:
                    self.last_used_responses[match.script_id] = response
                
                return PluginResult(
                    success=True,
                    response=response,
                    metadata={
                        "script_id": match.script_id,
                        "match_type": match.match_type,
                    },
                )
            else:
                return PluginResult(
                    success=False,
                    response=None,
                )
                
        except Exception as e:
            logger.error(f"好奇心插件处理失败：{e}")
            return PluginResult(
                success=False,
                response="抱歉，我走神了...",
                metadata={"error": str(e)},
            )

    def _generate_response(self, match) -> Optional[str]:
        """
        生成响应：优先使用重组规则
        
        Args:
            match: 脚本匹配结果
            
        Returns:
            生成的响应
        """
        response = None
        
        # 尝试使用重组规则
        if match.reassembly_rules and match.components:
            response = self._apply_reassembly(match)
        
        # 如果重组失败，使用预定义响应
        if response is None and match.responses:
            response = self._select_response(match)
        
        return response

    def _apply_reassembly(self, match) -> Optional[str]:
        """
        应用重组规则生成响应
        
        Args:
            match: 脚本匹配结果
            
        Returns:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None
        
        rules = match.reassembly_rules
        selected_rule = self._select_reassembly_rule(rules, match.script_id)
        
        if not selected_rule:
            return None
        
        response = self.reassembly_engine.reassemble(
            components=match.components,
            reassembly_rule=selected_rule,
            apply_pronoun_mapping=True,
        )
        
        return response.strip() if response else None

    def _select_reassembly_rule(self, rules: List[str], script_id: str) -> Optional[str]:
        """
        选择重组规则（避免重复）
        
        Args:
            rules: 重组规则列表
            script_id: 脚本 ID
            
        Returns:
            选中的规则
        """
        if not rules:
            return None
        
        last_rule = self.last_used_responses.get(f"{script_id}_rule", "")
        available_rules = [r for r in rules if r != last_rule]
        
        if available_rules:
            selected = random.choice(available_rules)
        else:
            selected = random.choice(rules)
        
        self.last_used_responses[f"{script_id}_rule"] = selected
        return selected

    def _select_response(self, match) -> Optional[str]:
        """
        从预定义响应中选择
        
        Args:
            match: 脚本匹配结果
            
        Returns:
            选中的响应
        """
        if not match.responses:
            return None
        
        last_response = self.last_used_responses.get(match.script_id, "")
        available_responses = [r for r in match.responses if r != last_response]
        
        if available_responses:
            selected = random.choice(available_responses)
        else:
            selected = random.choice(match.responses)
        
        return selected

    def get_stats(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        return {
            "name": self.name,
            "script_history": self.script_history,
            "last_used_responses": self.last_used_responses,
        }

    def reset(self) -> None:
        """重置插件状态"""
        if self.script_engine:
            self.script_engine.reset()
        self.script_history.clear()
        self.last_used_responses.clear()

    def cleanup(self) -> None:
        """清理插件资源"""
        self.reset()
