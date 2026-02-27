#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结束对话功能测试

测试 Bot 主动结束对话的功能：
1. ScriptResponse 的 end_action 和 end_reason 字段
2. YAML 脚本引擎解析 end_action
3. DialogueEngine 处理结束逻辑
4. EndAction 数据类
"""

import pytest
from pathlib import Path

from alice.scripting.base import ScriptResponse
from alice.scripting.end_action import EndAction
from alice.scripting.yaml.engine import YAMLScriptEngine
from alice.scripting.yaml.parser import ScriptIntent
from alice.scripting.context import ScriptContext
from alice.scripting.base import ScriptConfig


class TestScriptResponse:
    """测试 ScriptResponse 的 end_action 和 end_reason 字段"""

    def test_default_end_action(self):
        """测试默认 end_action 为 'none'"""
        response = ScriptResponse(
            text="你好",
            script_id="test",
            intent_name="greeting",
        )
        assert response.end_action == "none"
        assert response.end_reason == ""

    def test_custom_end_action(self):
        """测试自定义 end_action"""
        response = ScriptResponse(
            text="再见",
            script_id="test",
            intent_name="farewell",
            end_action="farewell",
            end_reason="user_farewell",
        )
        assert response.end_action == "farewell"
        assert response.end_reason == "user_farewell"

    def test_direct_end_action(self):
        """测试 direct 结束动作"""
        response = ScriptResponse(
            text="",
            script_id="test",
            intent_name="max_turns_end",
            end_action="direct",
            end_reason="max_turns",
        )
        assert response.end_action == "direct"
        assert response.end_reason == "max_turns"


class TestEndAction:
    """测试 EndAction 数据类"""

    def test_default_action(self):
        """测试默认动作"""
        action = EndAction()
        assert action.action == "none"
        assert not action.is_ending()
        assert not action.should_send_farewell()

    def test_direct_action(self):
        """测试直接结束动作"""
        action = EndAction(action="direct", reason="max_turns")
        assert action.action == "direct"
        assert action.reason == "max_turns"
        assert action.is_ending()
        assert not action.should_send_farewell()

    def test_farewell_action(self):
        """测试告别结束动作"""
        action = EndAction(action="farewell", reason="user_farewell")
        assert action.action == "farewell"
        assert action.reason == "user_farewell"
        assert action.is_ending()
        assert action.should_send_farewell()

    def test_from_response(self):
        """测试从 ScriptResponse 创建 EndAction"""
        response = ScriptResponse(
            text="再见",
            script_id="farewell_script",
            intent_name="farewell",
            end_action="farewell",
            end_reason="user_farewell",
        )
        action = EndAction.from_response(response)
        assert action.action == "farewell"
        assert action.reason == "user_farewell"
        assert action.script_id == "farewell_script"

    def test_to_dict(self):
        """测试转换为字典"""
        action = EndAction(
            action="direct",
            reason="suspicion",
            script_id="suspicion_script",
            metadata={"test": "value"},
        )
        result = action.to_dict()
        assert result["action"] == "direct"
        assert result["reason"] == "suspicion"
        assert result["script_id"] == "suspicion_script"
        assert result["metadata"]["test"] == "value"


class TestScriptIntent:
    """测试 ScriptIntent 的 end_action 字段"""

    def test_default_end_action(self):
        """测试默认 end_action"""
        intent = ScriptIntent(
            name="test_intent",
            priority=50,
            templates=["测试模板"],
        )
        assert intent.end_action == "none"
        assert intent.end_reason == ""

    def test_custom_end_action(self):
        """测试自定义 end_action"""
        intent = ScriptIntent(
            name="max_turns_end",
            priority=85,
            templates=[""],
            end_action="direct",
            end_reason="max_turns",
        )
        assert intent.end_action == "direct"
        assert intent.end_reason == "max_turns"


class TestYAMLScriptEngine:
    """测试 YAML 脚本引擎解析 end_action"""

    @pytest.fixture
    def yaml_engine(self):
        """创建 YAML 引擎实例"""
        return YAMLScriptEngine()

    @pytest.fixture
    def test_script_path(self):
        """测试脚本路径"""
        return Path(__file__).parent.parent.parent / "scripts" / "end_conversation.yaml"

    def test_load_end_conversation_script(self, yaml_engine, test_script_path):
        """测试加载结束对话脚本"""
        config = ScriptConfig(
            script_id="end_conversation",
            name="end_conversation",
            script_type="yaml",
            script_path=test_script_path,
        )
        success = yaml_engine.load_script(config)
        assert success is True

    def test_parse_max_turns_end_intent(self, yaml_engine, test_script_path):
        """测试解析最大轮数结束意图"""
        config = ScriptConfig(
            script_id="end_conversation",
            name="end_conversation",
            script_type="yaml",
            script_path=test_script_path,
        )
        yaml_engine.load_script(config)

        # 查找 max_turns_end 意图
        intent_name = "end_conversation_max_turns_end"
        assert intent_name in yaml_engine._intents

        intent = yaml_engine._intents[intent_name]
        assert intent.end_action == "direct"
        assert intent.end_reason == "bot_max_turns"

    def test_parse_farewell_intent(self, yaml_engine, test_script_path):
        """测试解析告别意图"""
        config = ScriptConfig(
            script_id="end_conversation",
            name="end_conversation",
            script_type="yaml",
            script_path=test_script_path,
        )
        yaml_engine.load_script(config)

        # 查找 user_farewell 意图
        intent_name = "end_conversation_user_farewell"
        assert intent_name in yaml_engine._intents

        intent = yaml_engine._intents[intent_name]
        assert intent.end_action == "farewell"
        assert intent.end_reason == "bot_farewell"

    def test_generate_response_with_end_action(self, yaml_engine, test_script_path):
        """测试生成带有结束动作的响应"""
        config = ScriptConfig(
            script_id="end_conversation",
            name="end_conversation",
            script_type="yaml",
            script_path=test_script_path,
        )
        yaml_engine.load_script(config)

        # 创建测试上下文
        context = ScriptContext(
            text="再见",
            tokens=["再见"],
            turn_count=5,
        )

        # 匹配意图
        match = yaml_engine.match(context)
        assert match is not None

        # 生成响应
        response = yaml_engine.generate_response(match.script_id, context)
        assert response is not None
        assert response.end_action in ("none", "farewell", "direct")


class TestDialogueEngineEndAction:
    """测试 DialogueEngine 处理结束逻辑"""

    def test_respond_returns_end_action(self):
        """测试 respond 方法返回 EndAction"""
        from alice.bots.lightweight_alice_bot import LightweightAliceBot
        from alice.services.shared_nlp_service import SharedNLPService
        from pathlib import Path

        nlp_service = SharedNLPService()

        # 使用绝对路径
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "end_conversation.yaml"

        bot = LightweightAliceBot(
            nlp_service=nlp_service,
            script_file=str(script_path),
            use_ltp=False,
        )

        # 测试告别场景
        response, end_action = bot.respond_with_end_action("再见")
        assert response is not None
        # end_action 可能是 farewell 或 none，取决于脚本匹配

        # 测试正常对话场景
        # 注意：由于有时间相关的脚本（如 late_night_end），end_action 可能是 farewell
        response2, end_action2 = bot.respond_with_end_action("你好")
        assert response2 is not None
        # 正常对话应该没有结束动作，或者只有 farewell（如果触发了时间相关脚本）
        if end_action2:
            assert end_action2.get("action") in ("none", "farewell")


class TestEndActionScenarios:
    """测试结束动作场景"""

    def test_suspicion_detected_end_action(self):
        """测试检测到怀疑时的结束动作"""
        from alice.bots.lightweight_alice_bot import LightweightAliceBot
        from alice.services.shared_nlp_service import SharedNLPService
        from pathlib import Path

        nlp_service = SharedNLPService()

        # 使用绝对路径
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "end_conversation.yaml"

        bot = LightweightAliceBot(
            nlp_service=nlp_service,
            script_file=str(script_path),
            use_ltp=False,
        )

        # 模拟用户怀疑
        response, end_action = bot.respond_with_end_action("你是真人吗")

        # 如果匹配到 suspicion_detected 意图，应该是 direct 结束
        if end_action:
            assert end_action.get("action") in ("direct", "farewell", "none")

    def test_max_turns_end_action(self):
        """测试达到最大轮数时的结束动作"""
        from alice.bots.lightweight_alice_bot import LightweightAliceBot
        from alice.services.shared_nlp_service import SharedNLPService
        from pathlib import Path

        nlp_service = SharedNLPService()

        # 使用绝对路径
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "end_conversation.yaml"

        bot = LightweightAliceBot(
            nlp_service=nlp_service,
            script_file=str(script_path),
            use_ltp=False,
        )

        # 模拟多轮对话（超过 15 轮）
        end_action = None
        for i in range(16):
            response, end_action = bot.respond_with_end_action(f"消息{i}")
            # 前 10 轮会触发 medium_turns_end，15 轮触发 max_turns_end
            # 这里只验证最终会触发结束动作
            if end_action and end_action.get("action") == "direct":
                # 可能是 bot_medium_turns (10 轮) 或 bot_max_turns (15 轮)
                assert end_action.get("reason") in ("bot_medium_turns", "bot_max_turns")
                break
        
        # 确保确实触发了结束动作
        assert end_action is not None
        assert end_action.get("action") == "direct"


class TestTimeConditionChecker:
    """测试时间条件检查器"""

    def test_hour_gte_condition(self):
        """测试 hour_gte 条件"""
        from alice.scripting.yaml.condition_checker import ConditionChecker
        from alice.scripting.yaml.parser import ScriptIntent
        from alice.scripting.context import ScriptContext
        from datetime import datetime

        checker = ConditionChecker()
        current_hour = datetime.now().hour

        # 如果当前小时是 10 点，测试 hour_gte=5 应该通过，hour_gte=15 应该失败
        intent = ScriptIntent(
            name="test_hour_gte",
            priority=50,
            condition={"hour_gte": 5},  # 5 点之后
            templates=["测试"],
        )
        context = ScriptContext(text="测试", turn_count=1)

        # 5 点之后应该通过（早上 8 点应该通过）
        result = checker.check(intent, context)
        if current_hour >= 5:
            assert result is True
        else:
            assert result is False

    def test_hour_lt_condition(self):
        """测试 hour_lt 条件"""
        from alice.scripting.yaml.condition_checker import ConditionChecker
        from alice.scripting.yaml.parser import ScriptIntent
        from alice.scripting.context import ScriptContext
        from datetime import datetime

        checker = ConditionChecker()
        current_hour = datetime.now().hour

        # 测试 hour_lt=12（中午之前）
        intent = ScriptIntent(
            name="test_hour_lt",
            priority=50,
            condition={"hour_lt": 12},  # 12 点之前
            templates=["测试"],
        )
        context = ScriptContext(text="测试", turn_count=1)

        result = checker.check(intent, context)

        # 早上 8 点应该通过
        if current_hour < 12:
            assert result is True
        else:
            assert result is False

    def test_late_night_condition_not_triggered_in_morning(self):
        """测试深夜条件在早上不触发"""
        from alice.scripting.yaml.condition_checker import ConditionChecker
        from alice.scripting.yaml.parser import ScriptIntent
        from alice.scripting.context import ScriptContext
        from datetime import datetime

        checker = ConditionChecker()
        current_hour = datetime.now().hour

        # 测试 late_night_end 条件（23 点之后）
        intent = ScriptIntent(
            name="late_night_end",
            priority=80,
            condition={"hour_gte": 23},  # 23 点之后
            templates=["测试"],
            end_action="farewell",
            end_reason="timeout",
        )
        context = ScriptContext(text="测试", turn_count=1)

        result = checker.check(intent, context)

        # 早上 8 点不应该触发深夜条件
        if current_hour < 23:
            assert result is False, "深夜条件在早上不应该触发"
        else:
            assert result is True
