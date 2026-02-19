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
from collections import deque

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("提示：未安装 jieba，将使用基础分词模式")

# 导入日志和性能监控模块
try:
    from .utils.logger import DialogueLogger
    from .utils.performance import PerformanceMonitor
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

# 导入重组引擎模块
try:
    from .utils.reassembly import ReassemblyEngine, DecompositionMatcher, ReassemblyRuleSelector
    REASSEMBLY_AVAILABLE = True
except ImportError:
    REASSEMBLY_AVAILABLE = False
    print("提示：未找到重组引擎模块，将使用基础响应模式")


@dataclass
class DialogueContext:
    """对话上下文"""
    entities: deque  # 最近提及的实体
    last_intent: str = ""
    conversation_turns: int = 0

    def add_entity(self, entity: str, entity_type: str = "unknown"):
        """添加实体到上下文"""
        if len(self.entities) >= 3:  # 限制记忆长度
            self.entities.popleft()
        self.entities.append((entity, entity_type))

    def get_recent_entities(self) -> List[Tuple[str, str]]:
        """获取最近的实体"""
        return list(self.entities)


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
        """从配置文件加载规则"""
        if rules_file and os.path.exists(rules_file):
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.pronoun_mapping = config.get('pronoun_mapping', {})
                    self.transformation_rules = [
                        (pattern, replacement)
                        for pattern, replacement in config.get('transformation_rules', [])
                    ]
                return
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载规则文件失败：{e}，使用默认规则")

        # 默认规则
        self.pronoun_mapping = {
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

        self.transformation_rules = [
            (r'我觉得 (.*)', r'你为什么觉得\1 呢？'),
            (r'我不 (.*)', r'为什么不\1 呢？'),
            (r'我想 (.*)', r'为什么想\1 呢？'),
            (r'我喜欢 (.*)', r'你喜欢\1 什么地方？'),
            (r'我讨厌 (.*)', r'为什么讨厌\1 呢？'),
            (r'我害怕 (.*)', r'\1 让你感到害怕吗？'),
            (r'我希望 (.*)', r'为什么希望\1 呢？'),
        ]

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
    """好奇心脚本引擎（增强版 - 支持重组规则）"""

    def __init__(self, script_file: Optional[str] = None, 
                 rules_file: Optional[str] = None):
        self.scripts = self._load_scripts(script_file)
        self.script_history: Dict[str, int] = {}
        self.last_used_responses: Dict[str, str] = {}
        
        # 重组规则选择器
        self.reassembly_selectors: Dict[str, ReassemblyRuleSelector] = {}
        self._init_reassembly_selectors()
        
        # 反射引擎用于重组
        self.reassembly_engine = ReassemblyEngine(rules_file) if REASSEMBLY_AVAILABLE else None

    def _init_reassembly_selectors(self):
        """为每个脚本初始化重组规则选择器"""
        for script_name, script_config in self.scripts.items():
            rules = script_config.get('reassembly_rules', [])
            if rules:
                self.reassembly_selectors[script_name] = ReassemblyRuleSelector(rules)

    def _load_scripts(self, script_file: Optional[str]) -> Dict:
        """加载脚本配置"""
        if script_file and os.path.exists(script_file):
            try:
                with open(script_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载脚本文件失败：{e}，使用默认脚本")

        # 默认好奇心脚本（优化版）
        return {
            "greeting": {
                "patterns": [r".*你好.*", r".*嗨.*", r".*哈喽.*", r".*早上好.*", r".*下午好.*", r".*晚上好.*"],
                "responses": [
                    "你好！很高兴和你聊天。",
                    "嗨！今天过得怎么样？",
                    "你好呀！有什么想聊的吗？",
                    "嘿！我在这儿，想聊点什么？"
                ],
                "priority": 6
            },
            "narrative_continuation": {
                "patterns": [
                    r".*去.*了.*", r".*做.*了.*", r".*看.*了.*", r".*买.*了.*",
                    r".*发生.*了.*", r".*吃.*了.*", r".*喝.*了.*", r".*玩.*了.*",
                    r".*说.*了.*", r".*走.*了.*"
                ],
                "responses": [
                    "后来呢？发生了什么让你印象深刻的事吗？",
                    "那之后你做了什么？",
                    "听起来很有意思，能详细说说吗？",
                    "然后呢？我很好奇接下来发生了什么。",
                    "哇，那一定很有趣吧？继续说说看！"
                ],
                "priority": 5
            },
            "person_focus": {
                "patterns": [
                    r".*朋友.*", r".*家人.*", r".*同事.*", r".*同学.*",
                    r".*老板.*", r".*老师.*", r".*他.*", r".*她.*"
                ],
                "responses": [
                    "你提到的这个人，平时是个怎样的人？",
                    "听起来你对 ta 很关注，能多说说 ta 吗？",
                    "你们之间的关系怎么样？",
                    "ta 是怎么看待这件事的？",
                    "你觉得 ta 为什么会这样做呢？"
                ],
                "priority": 4
            },
            "emotional_expression": {
                "patterns": [
                    r".*难过.*", r".*开心.*", r".*生气.*", r".*焦虑.*",
                    r".*累.*", r".*烦.*", r".*害怕.*", r".*失望.*",
                    r".*喜欢.*", r".*讨厌.*", r".*压力.*", r".*郁闷.*"
                ],
                "responses": [
                    "听起来你现在感受很复杂，能跟我说说具体是什么让你有这样的感受吗？",
                    "这种感受你以前也经历过吗？",
                    "我理解你的感受，愿意多聊聊吗？",
                    "是什么让你产生了这样的情绪呢？",
                    "你希望这种感觉如何改变呢？"
                ],
                "priority": 5
            },
            "opinion_question": {
                "patterns": [r".*为什么.*", r".*怎么.*", r".*如何.*", r".*什么.*", r".*哪里.*"],
                "responses": [
                    "这个问题很有意思，你是怎么想到的？",
                    "对于这个问题，你自己有什么想法吗？",
                    "这确实值得思考，你觉得呢？",
                    "不同的人可能有不同的答案，你的看法是什么？"
                ],
                "priority": 3
            },
            "self_thought": {
                "patterns": [r".*我觉得.*", r".*我认为.*", r".*我想.*", r".*我感觉.*"],
                "responses": [
                    "你为什么会有这样的想法呢？",
                    "这种想法是从什么时候开始的？",
                    "这个想法对你的生活有什么影响？",
                    "你是怎么形成这样的看法的？"
                ],
                "priority": 5
            },
            "default": {
                "patterns": [r".*"],
                "responses": [
                    "嗯，我明白了。能再多跟我聊聊吗？",
                    "有意思，然后呢？",
                    "真的吗？我很好奇更多细节。",
                    "原来是这样啊，接下来发生了什么？",
                    "这听起来很有趣，继续说说看。",
                    "诶？能再多讲讲吗？",
                    "我在这儿听着呢，继续说吧。",
                    "嗯嗯，然后呢？"
                ],
                "priority": 1
            }
        }

    def match_script(self, text: str, semantic_info: Dict) -> Optional[str]:
        """
        匹配合适的脚本并生成响应（仅使用重组规则引擎）
        
        已禁用固定 responses 词库，直接使用重组规则进行动态响应
        """
        for script_name, script_config in self.scripts.items():
            priority = script_config.get('priority', 1)

            for pattern in script_config.get('patterns', []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 检查是否有重组规则
                    if script_name in self.reassembly_selectors and self.reassembly_engine:
                        # 使用重组规则生成响应
                        components = match.groups()
                        selector = self.reassembly_selectors[script_name]
                        rule = selector.select(avoid_repeats=True)
                        if rule:
                            response = self.reassembly_engine.reassemble(components, rule)
                            self.script_history[script_name] = self.script_history.get(script_name, 0) + 1
                            return response
                    
                    # 没有重组规则时，返回 None 让反射引擎处理
                    return None

        return None


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
        self.context = DialogueContext(entities=deque())
        self.conversation_history: List[Tuple[str, str]] = []

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

            # 3. 更新上下文
            self._update_context(semantic_info)

            # 4. 尝试脚本匹配（重组规则引擎）
            script_response = self.script_engine.match_script(standardized_text, semantic_info)
            if script_response:
                final_response = script_response
            else:
                # 5. 反射转换作为备选
                reflected_response = self.reflection_engine.transform(standardized_text, semantic_info)
                # 只有当反射引擎实际转换了文本时才使用
                if reflected_response and reflected_response != standardized_text:
                    final_response = f"{reflected_response}？"
                else:
                    # 6. 回退到默认响应（使用重组规则引擎的 default 脚本）
                    final_response = self._generic_response(standardized_text, semantic_info)

            self._record_conversation(user_input, final_response)

            # 记录日志和性能
            self._log_interaction(user_input, final_response, start_time)

            return final_response

        except Exception as e:
            # 错误处理
            if self.enable_logging and self.dialogue_logger:
                self.dialogue_logger.log_error(e, {'user_input': user_input})
            return "抱歉，出了点问题。能换个说法吗？"
    
    def _log_interaction(self, user_input: str, response: str, start_time: float):
        """记录交互日志和性能"""
        duration = (time.time() - start_time) * 1000
        
        if self.enable_logging and self.dialogue_logger:
            self.dialogue_logger.log_dialogue(user_input, response)
            self.dialogue_logger.log_performance("respond", duration)
        
        if self.perf_monitor:
            self.perf_monitor.start_timer("respond")
            self.perf_monitor.stop_timer("respond", duration_ms=duration)

    def _update_context(self, semantic_info: Dict):
        """更新对话上下文"""
        entities = semantic_info.get('entities', [])
        for entity_type, entity_name in entities:
            self.context.add_entity(entity_name, entity_type)

    def _generic_response(self, text: str, semantic_info: Dict) -> str:
        """
        生成通用回应（仅从default.responses词库获取）
        
        参数:
            text: 标准化后的文本
            semantic_info: 语义分析结果
        """
        # 从脚本引擎中获取default脚本的responses词库
        default_config = self.script_engine.scripts.get("default", {})
        generic_responses = default_config.get('responses', [])
        
        # 如果没有找到responses词库，抛出异常
        if not generic_responses:
            raise ValueError("未找到default.responses词库，请检查脚本配置文件")
        
        return random.choice(generic_responses)

    def _record_conversation(self, user_input: str, response: str):
        """记录对话历史"""
        self.conversation_history.append(('user', user_input))
        self.conversation_history.append(('alice', response))
        # 限制历史记录长度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def get_conversation_summary(self) -> Dict:
        """获取对话摘要"""
        return {
            'turns': len(self.conversation_history) // 2,
            'recent_entities': self.context.get_recent_entities(),
            'script_usage': self.script_engine.script_history
        }

    def reset(self):
        """重置对话状态"""
        self.context = DialogueContext(entities=deque())
        self.conversation_history = []
        self.script_engine.script_history = {}
        self.script_engine.last_used_responses = {}
        # 重置重组规则选择器
        for selector in self.script_engine.reassembly_selectors.values():
            selector.reset()


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
        except Exception as e:
            print(f"Alice: 抱歉，出了点问题。能换个说法吗？")
