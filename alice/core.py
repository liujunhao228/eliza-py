#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alice - 好奇的朋友聊天机器人核心模块
基于 ELIZA 原理，采用轻量化设计实现中文对话
"""

import os
import re
import json
import random
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("提示：未安装 jieba，将使用基础分词模式")

# 导入日志和性能监控模块
try:
    from alice.utils.logger import DialogueLogger
    from alice.utils.performance import PerformanceMonitor
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

# 导入重组引擎模块
try:
    from alice.utils.reassembly import ReassemblyEngine, DecompositionMatcher, ReassemblyRuleSelector
    REASSEMBLY_AVAILABLE = True
except ImportError:
    REASSEMBLY_AVAILABLE = False
    print("提示：未找到重组引擎模块，部分功能可能不可用")

# 导入通用脚本引擎模块（必需）
from alice.utils.script_engine import ScriptEngine, ScriptMatch


from alice.utils.context import ContextManager, ConversationHistory


class TextPreprocessor:
    """文本预处理器"""

    def __init__(self):
        # 中文标点符号映射（全角转半角）
        self.punctuation_map = {
            '，': ',', '。': '.', '！': '!', '？': '?',
            '；': ';', '：': ':', '"': '"', "'": "'",
            '、': ',', '「': '"', '」': '"', '『': '"', '』': '"'
        }
        # 全角转半角映射
        self.fullwidth_map = {
            chr(0xFF01 + i): chr(0x21 + i) for i in range(94)  # 标点
        }
        self.fullwidth_map[' '] = ' '
        self.fullwidth_map['。'] = '.'

    def standardize_text(self, text: str) -> str:
        """文本标准化"""
        # 全角转半角
        for full, half in self.fullwidth_map.items():
            text = text.replace(full, half)
        # 统一标点符号
        for full, half in self.punctuation_map.items():
            text = text.replace(full, half)
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def segment_text(self, text: str) -> List[str]:
        """中文分词"""
        if JIEBA_AVAILABLE:
            return list(jieba.cut(text))
        else:
            # 基础分词：按字符分割
            return list(text)


class SemanticAnalyzer:
    """语义分析器（轻量化版本）"""

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        # 情感词库（简化版）
        self.positive_words = {
            '好', '棒', '喜欢', '开心', '高兴', '快乐', '幸福', '满意',
            '爱', '美好', '顺利', '成功', '优秀', '赞美', '感谢'
        }
        self.negative_words = {
            '坏', '差', '讨厌', '难过', '生气', '焦虑', '痛苦', '失望',
            '恨', '烦恼', '压力', '累', '困', '烦', '糟糕', '失败'
        }
        # 意图关键词映射
        self.intent_keywords = {
            'narrative': ['去', '做', '看', '买', '发生', '出现', '开始', '结束'],
            'emotion': ['感觉', '觉得', '心情', '情绪', '感受'],
            'person': ['朋友', '家人', '同事', '同学', '老师', '老板'],
            'relationship': ['关系', '相处', '吵架', '矛盾', '误会'],
            'question': ['为什么', '怎么', '如何', '什么', '哪里', '何时']
        }

    def analyze(self, text: str) -> Dict:
        """分析文本语义"""
        words = self.preprocessor.segment_text(text)

        analysis = {
            'tokens': words,
            'sentiment': self._analyze_sentiment(words),
            'intent': self._detect_intent(words),
            'entities': self._extract_entities(words, text),
            'original_text': text
        }
        return analysis

    def _analyze_sentiment(self, tokens: List[str]) -> float:
        """简单情感分析"""
        pos_count = sum(1 for token in tokens if any(pw in token for pw in self.positive_words))
        neg_count = sum(1 for token in tokens if any(nw in token for nw in self.negative_words))

        if pos_count + neg_count == 0:
            return 0.0
        return (pos_count - neg_count) / (pos_count + neg_count)

    def _detect_intent(self, tokens: List[str]) -> str:
        """意图检测"""
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            # 改进：检查 tokens 中是否包含关键词或其子串
            score = sum(1 for token in tokens if any(kw in token for kw in keywords))
            intent_scores[intent] = score

        # 返回得分最高的意图
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        return 'general'

    def _extract_entities(self, tokens: List[str], text: str) -> List[str]:
        """提取关键实体（简化版）"""
        entities = []
        # 人称代词
        pronouns = ['我', '你', '他', '她', '它', '我们', '你们', '他们', '她们']
        for pronoun in pronouns:
            if pronoun in tokens:
                entities.append(('pronoun', pronoun))

        # 时间词
        time_words = ['今天', '昨天', '明天', '刚才', '最近', '上周', '下周']
        for tw in time_words:
            if tw in tokens:
                entities.append(('time', tw))

        return entities


class ReflectionEngine:
    """反射转换引擎（增强版 - 支持重组规则）"""

    def __init__(self, rules_file: Optional[str] = None):
        # 代词映射表
        self.pronoun_mapping = {}
        self.transformation_rules = []
        self._load_rules(rules_file)

    def _load_rules(self, rules_file: Optional[str]):
        """从配置文件加载规则

        严禁回退：规则文件必须存在且有效，否则抛出异常。
        """
        if not rules_file:
            raise RuntimeError("错误：规则文件路径不能为空")
        
        if not os.path.exists(rules_file):
            raise RuntimeError(f"错误：规则文件不存在：{rules_file}")
        
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.pronoun_mapping = config.get('pronoun_mapping', {})
                self.transformation_rules = [
                    (pattern, replacement)
                    for pattern, replacement in config.get('transformation_rules', [])
                ]
        except json.JSONDecodeError as e:
            raise RuntimeError(f"错误：规则文件 JSON 格式无效：{rules_file} - {e}")
        except IOError as e:
            raise RuntimeError(f"错误：无法读取规则文件：{rules_file} - {e}")

    def transform(self, text: str, semantic_info: Optional[Dict] = None) -> str:
        """执行反射转换"""
        # 1. 应用代词映射（按长度排序，优先匹配长的）
        transformed = text
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)

        # 2. 应用句式转换规则
        for pattern, replacement in self.transformation_rules:
            match = re.search(pattern, transformed)
            if match:
                transformed = re.sub(pattern, replacement, transformed)
                break

        return transformed

    def transform_with_reassembly(self, text: str, components: List[str],
                                   reassembly_rule: str) -> str:
        """
        使用重组规则执行反射转换

        参数:
            text: 原始文本
            components: 分解组件列表
            reassembly_rule: 重组规则（支持 {1}, {2} 等占位符）

        返回:
            转换后的响应
        """
        # 1. 先应用代词映射到组件
        transformed_components = [
            self._apply_pronoun_mapping(comp) for comp in components
        ]

        # 2. 应用重组规则
        response = reassembly_rule
        for i, comp in enumerate(transformed_components, 1):
            placeholder = f'{{{i}}}'
            response = response.replace(placeholder, comp.strip() if comp else '')

        # 3. 清理未匹配的占位符
        response = re.sub(r'\{\d+\}', '', response)

        return response.strip()

    def _apply_pronoun_mapping(self, text: str) -> str:
        """应用代词映射"""
        transformed = text
        sorted_pronouns = sorted(self.pronoun_mapping.keys(), key=len, reverse=True)
        for pronoun in sorted_pronouns:
            replacement = self.pronoun_mapping[pronoun]
            transformed = transformed.replace(pronoun, replacement)
        return transformed


class CuriosityScriptEngine:
    """
    好奇心脚本引擎 - 基于通用 ScriptEngine 的封装

    内部使用通用的 ScriptEngine 模块。
    严禁回退：脚本引擎模块必须存在，否则启动时抛出异常。
    """

    def __init__(self, script_file: Optional[str] = None,
                 rules_file: Optional[str] = None):
        """
        初始化好奇心脚本引擎

        参数:
            script_file: 脚本配置文件路径
            rules_file: 反射规则文件路径（用于代词映射）
        """
        self.script_file = script_file
        self.rules_file = rules_file

        # 脚本引擎是必需模块，直接初始化
        self.engine = ScriptEngine(script_file=script_file)

        self.script_history: Dict[str, int] = {}
        self.last_used_responses: Dict[str, str] = {}

        # 重组引擎（必需）
        if rules_file:
            self.reassembly_engine = ReassemblyEngine(rules_file)
        else:
            self.reassembly_engine = ReassemblyEngine()

    def match_script(self, text: str, semantic_info: Dict) -> Optional[str]:
        """
        匹配合适的脚本并生成响应

        匹配流程:
        1. 使用 ScriptEngine 匹配脚本
        2. 优先使用重组规则生成响应（利用分解组件）
        3. 如果重组失败，使用预定义响应

        参数:
            text: 待匹配的文本
            semantic_info: 语义分析结果（用于情感分析和上下文集成）

        返回:
            生成的响应，无匹配返回 None
        """
        # 1. 使用通用脚本引擎匹配
        match = self.engine.match(text)
        if not match:
            return None

        # 2. 生成响应：优先使用重组规则
        response = self._generate_response(match, semantic_info)

        # 3. 更新历史记录
        self.script_history = self.engine.get_usage_statistics()
        if match.script_id and response:
            self.last_used_responses[match.script_id] = response

        return response

    def _generate_response(self, match, semantic_info: Dict) -> Optional[str]:
        """
        生成响应：优先使用重组规则

        参数:
            match: 脚本匹配结果
            semantic_info: 语义分析结果

        返回:
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

        参数:
            match: 脚本匹配结果

        返回:
            重组后的响应
        """
        if not self.reassembly_engine:
            return None

        # 选择重组规则（避免重复）
        rules = match.reassembly_rules
        selected_rule = self._select_reassembly_rule(rules, match.script_id)
        if not selected_rule:
            return None

        # 使用重组引擎生成响应
        response = self.reassembly_engine.reassemble(
            components=match.components,
            reassembly_rule=selected_rule,
            apply_pronoun_mapping=True
        )

        return response.strip() if response else None

    def _select_reassembly_rule(self, rules: List[str], script_id: str) -> Optional[str]:
        """
        选择重组规则（避免重复）

        参数:
            rules: 重组规则列表
            script_id: 脚本 ID

        返回:
            选中的规则
        """
        if not rules:
            return None

        last_rule = self.last_used_responses.get(f"{script_id}_rule", '')
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

        参数:
            match: 脚本匹配结果

        返回:
            选中的响应
        """
        if not match.responses:
            return None

        last_response = self.last_used_responses.get(match.script_id, '')
        available_responses = [r for r in match.responses if r != last_response]

        if available_responses:
            selected = random.choice(available_responses)
        else:
            selected = random.choice(match.responses)

        return selected

    def reset(self) -> None:
        """重置引擎状态"""
        self.engine.reset()
        self.script_history.clear()
        self.last_used_responses.clear()


class AliceBot:
    """Alice 聊天机器人"""

    def __init__(self, script_file: Optional[str] = None,
                 rules_file: Optional[str] = None,
                 enable_logging: bool = False):
        # 确定规则文件路径
        if rules_file is None:
            # 使用默认路径
            default_rules = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'scripts', 'reflection_rules.json'
            )
            if os.path.exists(default_rules):
                rules_file = default_rules

        self.preprocessor = TextPreprocessor()
        self.analyzer = SemanticAnalyzer()
        self.reflection_engine = ReflectionEngine(rules_file)
        self.script_engine = CuriosityScriptEngine(script_file, rules_file)
        
        # 使用 ContextManager 替代简化的 DialogueContext
        self.context_manager = ContextManager(max_items=10)
        self.conversation_history = ConversationHistory(max_turns=20)

        # 日志和性能监控（可选）
        self.enable_logging = enable_logging
        if enable_logging and LOGGING_AVAILABLE:
            self.dialogue_logger = DialogueLogger()
            self.perf_monitor = PerformanceMonitor()
        else:
            self.dialogue_logger = None
            self.perf_monitor = None

    def respond(self, user_input: str) -> str:
        """生成回复"""
        start_time = time.time()

        try:
            # 1. 预处理
            standardized_text = self.preprocessor.standardize_text(user_input)

            # 2. 语义分析
            semantic_info = self.analyzer.analyze(standardized_text)

            # 3. 更新上下文（包含情感分析和话题追踪）
            self.context_manager.update_context(semantic_info, user_input)

            # 4. 脚本匹配（必须匹配，无回退逻辑）
            script_response = self.script_engine.match_script(standardized_text, semantic_info)
            if script_response:
                final_response = script_response
            else:
                # 严禁回退：脚本匹配失败直接抛出异常
                raise RuntimeError(f"错误：无法为输入 '{user_input}' 生成响应 - 无匹配的脚本规则")

            # 5. 记录对话
            self._record_conversation(user_input, final_response)

            # 记录日志和性能
            self._log_interaction(user_input, final_response, start_time)

            return final_response

        except Exception as e:
            # 错误处理
            if self.enable_logging and self.dialogue_logger:
                self.dialogue_logger.log_error(e, {'user_input': user_input})
            raise  # 重新抛出异常，严禁降级处理

    def _log_interaction(self, user_input: str, response: str, start_time: float):
        """记录交互日志和性能"""
        duration = (time.time() - start_time) * 1000

        if self.enable_logging and self.dialogue_logger:
            self.dialogue_logger.log_dialogue(user_input, response)
            self.dialogue_logger.log_performance("respond", duration)

        if self.perf_monitor:
            self.perf_monitor.start_timer("respond")
            self.perf_monitor.stop_timer("respond", duration_ms=duration)

    def _record_conversation(self, user_input: str, response: str):
        """记录对话历史"""
        self.conversation_history.add_turn(user_input, response)

    def get_conversation_summary(self) -> Dict:
        """获取对话摘要"""
        context_state = self.context_manager.get_context_state()
        return {
            'turns': len(self.conversation_history.history),
            'recent_entities': self.context_manager.get_recent_persons(limit=3),
            'current_topic': context_state.get('current_topic', ''),
            'emotion_trend': context_state.get('emotion_trend', 'neutral'),
            'script_usage': self.script_engine.script_history,
            'recent_events': self.context_manager.get_recent_events(limit=2),
        }

    def reset(self):
        """重置对话状态"""
        self.context_manager.reset()
        self.conversation_history.clear()
        self.script_engine.script_history = {}
        self.script_engine.last_used_responses = {}
        # 重置脚本引擎
        self.script_engine.reset()


# 主程序入口
if __name__ == "__main__":
    alice = AliceBot()

    print("Alice: 你好！我是 Alice，你的好奇朋友。有什么想聊的吗？")
    print("Alice: 输入 'quit' 或 '再见' 结束对话。\n")

    while True:
        try:
            user_input = input("你：").strip()
            if user_input.lower() in ['再见', 'quit', 'exit', 'bye']:
                print("Alice: 再见！很高兴和你聊天！")
                break

            if not user_input:
                continue

            response = alice.respond(user_input)
            print(f"Alice: {response}")

        except KeyboardInterrupt:
            print("\nAlice: 再见！")
            break
        except RuntimeError as e:
            # 严禁回退：运行时错误直接抛出
            print(f"Alice: {e}")
            break
        except Exception as e:
            # 其他异常也抛出
            raise
