#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML 脚本引擎

基于 YAML 的声明式脚本引擎，支持：
- 意图匹配和条件触发
- 响应模板管理
- 优先级调度
- 热重载支持

使用示例:
    engine = YAMLScriptEngine()
    config = ScriptConfig(...)
    engine.load_script(config)
    match = engine.match(context)
"""

import hashlib
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from alice.scripting.yaml.parser import YAMLScriptParser, ScriptIntent
from alice.scripting.yaml.condition_checker import ConditionChecker
from alice.scripting.yaml.template_engine import TemplateEngine
from alice.scripting.end_action import normalize_end_reason

logger = logging.getLogger(__name__)


class OpeningMessageManager:
    """
    开场白管理器

    管理 Bot 开场白消息，支持热重载。
    """

    def __init__(self):
        self._messages: Dict[str, List[str]] = {}
        self._file_paths: Dict[str, Path] = {}
        self._file_hashes: Dict[str, str] = {}

    def load(self, script_id: str, file_path: Path) -> bool:
        if not file_path.exists():
            logger.warning(f"开场白脚本文件不存在：{file_path}")
            return False

        try:
            content = file_path.read_text(encoding='utf-8')
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            if script_id in self._file_paths:
                if self._file_hashes.get(script_id) == file_hash:
                    logger.info(f"开场白脚本未变更，跳过加载：{script_id}")
                    return True

            data = yaml.safe_load(content)
            if not data or not isinstance(data, dict):
                logger.warning(f"开场白脚本格式错误：{file_path}")
                return False

            messages = data.get('opening_messages', [])
            if not isinstance(messages, list) or not messages:
                logger.warning(f"开场白脚本没有有效的消息列表：{file_path}")
                return False

            self._messages[script_id] = messages
            self._file_paths[script_id] = file_path
            self._file_hashes[script_id] = file_hash

            logger.info(f"开场白脚本加载成功：{script_id} ({len(messages)} 条消息)")
            return True

        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 [{file_path}]: {e}")
            return False
        except Exception as e:
            logger.error(f"开场白脚本加载失败 [{script_id}]: {e}")
            return False

    def get_random(self, script_id: str) -> Optional[str]:
        messages = self._messages.get(script_id)
        if not messages:
            logger.warning(f"开场白脚本未加载：{script_id}")
            return None
        return random.choice(messages)

    def reload(self, script_id: str) -> bool:
        file_path = self._file_paths.get(script_id)
        if not file_path:
            logger.warning(f"开场白脚本未加载，无法重载：{script_id}")
            return False

        if script_id in self._messages:
            del self._messages[script_id]
        if script_id in self._file_hashes:
            del self._file_hashes[script_id]

        return self.load(script_id, file_path)

    def is_loaded(self, script_id: str) -> bool:
        """检查脚本是否已加载"""
        return script_id in self._messages

    def get_stats(self) -> Dict[str, Any]:
        return {
            'loaded_scripts': len(self._messages),
            'scripts': {
                script_id: {
                    'message_count': len(messages),
                    'file_path': str(file_path),
                }
                for script_id, messages in self._messages.items()
                if (file_path := self._file_paths.get(script_id))
            }
        }


class YAMLScriptEngine(BaseScriptEngine):
    """
    YAML 脚本引擎

    特性:
    - 声明式 YAML 配置
    - 基于条件的意图匹配
    - 响应模板管理
    - 优先级调度
    """

    def __init__(
        self,
        default_script_file: Optional[Path] = None,
        config_loader: Optional[ScriptConfigLoader] = None,
        reassembly_engine: Optional[Any] = None,
        opening_message_manager: Optional[OpeningMessageManager] = None,
    ):
        super().__init__(engine_type="yaml")

        if not YAML_AVAILABLE:
            raise ImportError("PyYAML 未安装，请运行：pip install pyyaml")

        self.default_script_file = default_script_file
        self.config_loader = config_loader or ScriptConfigLoader()
        self.reassembly_engine = reassembly_engine
        self.opening_manager = opening_message_manager or OpeningMessageManager()

        # 核心组件
        self._parser = YAMLScriptParser()
        self._condition_checker = ConditionChecker()
        self._template_engine = TemplateEngine(reassembly_engine)

        # 意图存储
        self._intents: Dict[str, ScriptIntent] = {}
        self._script_hashes: Dict[str, str] = {}

        if self.default_script_file:
            self._load_default_script()

    def _load_default_script(self) -> bool:
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

    def load_script(self, config: ScriptConfig) -> bool:
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
            content = config.script_path.read_text(encoding='utf-8')
            script_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

            if config.script_id in self.scripts:
                if self._script_hashes.get(config.script_id) == script_hash:
                    logger.info(f"YAML 脚本未变更，跳过加载：{config.script_id}")
                    return True

            scripts_data = self._parser.parse_file(config.script_path)
            if not scripts_data:
                logger.warning(f"YAML 脚本内容为空：{config.script_path}")
                return False

            intents = self._parser.parse_intents(scripts_data, config)
            if not intents:
                logger.warning(f"YAML 脚本未解析出任何意图：{config.script_path}")
                return False

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
        config = self.scripts.get(script_id)
        if not config:
            return False

        intents_to_remove = []
        for intent_name, intent in self._intents.items():
            if intent.name.startswith(f"{script_id}_"):
                intents_to_remove.append(intent_name)

        for intent_name in intents_to_remove:
            del self._intents[intent_name]

        if script_id in self._script_hashes:
            del self._script_hashes[script_id]
        if script_id in self.scripts:
            del self.scripts[script_id]

        logger.info(f"YAML 脚本已卸载：{script_id} (移除 {len(intents_to_remove)} 个意图)")
        return True

    def match(self, context: ScriptContext) -> Optional[ScriptMatchResult]:
        self._increment_stat('match_count')

        enabled_intents = [
            intent for intent in self._intents.values()
            if self.scripts.get(intent.name.split('_')[0], ScriptConfig("", "", "yaml")).enabled
        ]
        enabled_intents.sort(key=lambda i: i.priority, reverse=True)

        for intent in enabled_intents:
            if self._condition_checker.check(intent, context):
                intent.usage_count += 1
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
        intent = self._intents.get(script_id)
        if not intent:
            logger.error(f"意图不存在：{script_id}")
            return None

        if not intent.templates:
            logger.warning(f"意图没有响应模板：{script_id}")
            return None

        template = self._template_engine.select_template(intent)

        if intent.keyword_only:
            filled_template = self._template_engine.fill_template(template, context)
        elif self.reassembly_engine and user_input:
            filled_template = self._template_engine.generate_with_reassembly(
                template, context, user_input
            )
        else:
            filled_template = self._template_engine.fill_template(template, context)

        return ScriptResponse(
            text=filled_template,
            script_id=script_id,
            intent_name=intent.name,
            metadata={
                'template': template,
                'keyword_only': intent.keyword_only,
            },
            end_action=intent.end_action,
            end_reason=normalize_end_reason(intent.end_reason),
        )

    def reload_script(self, script_id: str) -> bool:
        config = self.scripts.get(script_id)
        if not config:
            logger.error(f"脚本不存在，无法重载：{script_id}")
            return False

        self.unload_script(script_id)
        return self.load_script(config)

    def get_stats(self) -> Dict[str, Any]:
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
            ],
            'opening_messages': self.opening_manager.get_stats(),
        }

    def load_opening_script(self, script_id: str, file_path: Path) -> bool:
        return self.opening_manager.load(script_id, file_path)

    def get_opening_message(self, script_id: str) -> Optional[str]:
        return self.opening_manager.get_random(script_id)

    def reload_opening_script(self, script_id: str) -> bool:
        return self.opening_manager.reload(script_id)

    def _get_extension(self) -> str:
        return "yaml"

    def _create_config_from_file(self, file_path: Path) -> Optional[ScriptConfig]:
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

    def _calculate_confidence(
        self,
        intent: ScriptIntent,
        context: ScriptContext,
    ) -> float:
        base_confidence = min(intent.priority / 100.0, 1.0)

        condition = intent.condition or {}
        keywords = condition.get("keywords", [])
        if keywords:
            matched_keywords = sum(1 for kw in keywords if kw in context.text)
            if matched_keywords > 0:
                base_confidence += min(matched_keywords * 0.1, 0.3)

        entities = condition.get("entities", [])
        if entities:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def get_intent(self, intent_name: str) -> Optional[ScriptIntent]:
        return self._intents.get(intent_name)

    def get_intents(self) -> Dict[str, ScriptIntent]:
        return self._intents.copy()

    def get_intent_names(self) -> List[str]:
        return list(self._intents.keys())

    def _fill_placeholders(self, template: str, context: ScriptContext) -> str:
        """填充模板占位符（委托给 template_engine）"""
        return self._template_engine.fill_template(template, context)

    def load_from_config_file(self, config_path: Path) -> int:
        configs = self.config_loader.load_from_yaml(config_path)
        count = 0
        for config in configs:
            if config.script_type == 'yaml' and self.load_script(config):
                count += 1
        return count
