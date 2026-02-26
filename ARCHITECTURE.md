# Alice 架构文档

**版本**: 2.0  
**更新日期**: 2026 年 2 月 26 日  
**状态**: 重构完成

---

## 架构概述

Alice 采用模块化分层架构，核心设计原则：

1. **职责分离**: 各模块职责单一清晰
2. **依赖倒置**: 高层模块不依赖低层模块具体实现
3. **接口统一**: 脚本引擎、NLP 引擎使用统一接口
4. **服务共享**: NLP 等服务采用单例模式共享资源

---

## 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                    Web/API Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ server.py   │  │ alice_v2.py │  │ CLI (main)  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Core Engine Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Dialogue    │  │ Context     │  │ Response    │     │
│  │ Engine      │  │ Manager     │  │ Generator   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Script Engine Layer                    │
│  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │  YAML Script Engine │  │   Lua Script Engine │      │
│  │  ├─ Parser          │  │   ├─ Sandbox        │      │
│  │  ├─ Condition Check │  │   └─ Compiled Script│      │
│  │  └─ Template Engine │  │                     │      │
│  └─────────────────────┘  └─────────────────────┘      │
│              │                        │                 │
│              └──────────┬─────────────┘                │
│                         ▼                              │
│              ┌─────────────────────┐                   │
│              │   Script Matcher    │                   │
│              │  (统一优先级调度)    │                   │
│              └─────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ NLP Service │  │ Monitoring  │  │   Cache     │     │
│  │  (单例)     │  │  Service    │  │  Service    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   NLP Engine Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Jieba     │  │     LTP     │  │     NER     │     │
│  │   Engine    │  │    Engine   │  │    Engine   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 核心模块说明

### 1. alice.core - 核心引擎层

| 模块 | 职责 | 行数 |
|------|------|------|
| `dialogue_engine.py` | 对话流程控制、NLP 调用、脚本匹配协调 | ~788 |
| `context_manager.py` | 对话历史、实体记忆、用户画像、时间上下文 | ~611 |
| `intent_matcher.py` | 意图识别和匹配 | ~129 |
| `response_generator.py` | 基于脚本和重组规则生成响应 | ~295 |

**关键类**:
```python
class DialogueEngine:
    """对话主引擎，协调所有组件完成对话"""
    def respond(user_input: str) -> str
    
class ContextManager:
    """管理对话上下文，包括历史、实体、用户画像"""
    def update(user_input, bot_response, entities, intent)
    def get_recent_turns(n: int) -> List[ConversationTurn]
```

---

### 2. alice.scripting - 脚本引擎层

**重构后结构** (2026-02-26):

```
scripting/
├── base.py                 # 基类和接口定义
├── context.py              # ScriptContext 数据模型
├── matcher.py              # 统一脚本匹配器
├── config.py               # 脚本配置加载
├── yaml/
│   ├── engine.py           # YAML 引擎核心 (~417 行)
│   ├── parser.py           # YAML 解析器 (~175 行)
│   ├── condition_checker.py# 条件检查器 (~237 行)
│   └── template_engine.py  # 模板填充引擎 (~240 行)
└── lua/
    ├── engine.py           # Lua 引擎核心 (~389 行)
    ├── sandbox.py          # Lua 沙箱隔离 (~477 行)
    └── compiled_script.py  # 编译脚本封装 (~132 行)
```

**统一接口**:
```python
class BaseScriptEngine(ABC):
    @abstractmethod
    def load_script(config: ScriptConfig) -> bool
    
    @abstractmethod
    def match(context: ScriptContext) -> Optional[ScriptMatchResult]
    
    @abstractmethod
    def generate_response(script_id, context) -> Optional[ScriptResponse]
```

**优先级调度**:
```
P0 (90-100): 非常重要 - 问候、告别
P1 (70-89):  实体挖掘 - 人物、地点询问
P2 (40-69):  叙事助推 - "后来呢"、"然后呢"
P3 (0-39):   万能回复 - 默认响应
```

---

### 3. alice.services - 服务层

| 服务 | 模式 | 职责 |
|------|------|------|
| `SharedNLPService` | 单例 | 共享 NLP 资源，避免重复加载 |
| `UnifiedMonitor` | 多例 | 性能监控、错误追踪 |
| `DialogueLogger` | 多例 | 结构化对话日志 |
| `IntelligentCache` | 多例 | 智能缓存响应 |

**SharedNLPService 接口**:
```python
class SharedNLPService(SyntaxAnalyzer, EntityRecognizer):
    """共享 NLP 服务，单例模式"""
    
    def analyze(user_input: str) -> NlpResult
    def tokenize(text: str) -> List[str]
    def analyze_syntax(text: str) -> SyntaxStructure
    def extract_entities(text: str) -> List[Entity]
```

---

### 4. alice.nlp - NLP 引擎层

**工厂模式**:
```python
class NlpFactory:
    """NLP 引擎工厂，支持组件热插拔"""
    def create_pipeline(components: List[str]) -> NlpPipeline
    
# 组件优先级：LTP > NER > Jieba
components = ['ltp']  # 或 ['ner'] 或 ['jieba', 'ner']
```

**支持的引擎**:
- `JiebaEngine`: 基础分词和词性标注
- `LtpEngine`: 完整句法分析（依存、三元组、语义角色）
- `NerEngine`: 命名实体识别

---

## 对话流程

```
用户输入
    │
    ▼
┌─────────────────┐
│ 文本预处理       │ 标准化、清理
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ NLP 分析         │ 分词、实体、句法
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 构建 ScriptContext│ 整合所有语义信息
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ ScriptMatcher   │ 统一匹配所有引擎
│  ├─ Lua 引擎     │ 按优先级竞争
│  └─ YAML 引擎    │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 响应生成         │ 脚本响应 > 重组规则 > 回退
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 更新上下文       │ 历史记录、实体记忆
└─────────────────┘
    │
    ▼
机器人响应
```

---

## 数据模型

### ScriptContext
```python
@dataclass
class ScriptContext:
    """脚本执行的上下文环境"""
    text: str                    # 标准化文本
    tokens: List[str]            # 分词结果
    entities: List[Tuple[str, str]]  # (类型，文本)
    syntax: Optional[Dict]       # 句法结构
    pos_tags: List[Tuple[str, str]]  # (词，词性)
    dependencies: List[Dict]     # 依存关系
    triples: List[Tuple]         # 语义三元组
    turn_count: int              # 对话轮数
    time_context: Dict           # 时间上下文
    user_profile: Dict           # 用户画像
```

### ScriptMatchResult
```python
@dataclass
class ScriptMatchResult:
    """脚本匹配结果"""
    script_id: str
    script_type: str      # "lua" | "yaml"
    intent_name: str
    priority: int         # 0-100
    confidence: float     # 0.0-1.0
    metadata: Dict
```

---

## 配置系统

### 统一配置入口
```python
from config import settings, get_config_manager

# 方式 1: 直接访问
script_file = settings.alice.script_file

# 方式 2: 配置管理器
config_mgr = get_config_manager()
script_file = config_mgr.get('alice.script_file')
```

### 配置文件结构
```yaml
alice:
  script_file: "alice/scripts/emotion_responses.yaml"
  rules_file: "alice/scripts/rules/mapping.yaml"
  enable_ltp: true
  enable_ner: true
  
scripting:
  enable_lua: true
  enable_yaml: true
  lua:
    script_dir: "alice/scripts/lua"
    sandbox_mode: true
```

---

## 测试策略

### 测试金字塔
```
        ┌───┐
       │ E2E │      少量
      ├─────┤
     │Integration│  适中
    ├─────────────┤
   │   Unit Tests  │ 大量
  └─────────────────┘
```

### 测试覆盖率要求
- `alice.scripting.*`: 100% (核心引擎)
- `alice.core.*`: ≥90%
- `alice.services.*`: ≥85%
- `alice.nlp.*`: ≥80%

### 运行测试
```bash
# 完整测试套件
pytest tests/ -v

# 仅脚本引擎测试
pytest tests/scripting/ -v

# 仅单元测试
pytest tests/unit/ -v

# 生成覆盖率报告
pytest --cov=alice --cov-report=html
```

---

## 性能指标

| 操作 | 目标 | 实测 |
|------|------|------|
| 单次对话响应 | <50ms | ~35ms |
| NLP 分析 (Jieba) | <10ms | ~5ms |
| NLP 分析 (LTP) | <100ms | ~80ms |
| 脚本匹配 | <5ms | ~2ms |
| 缓存命中率 | >30% | ~45% |
| 并发支持 | >100 req/s | ~150 req/s |

---

## 安全考虑

### Lua 沙箱
```python
class LuaSandbox:
    """Lua 脚本沙箱，隔离危险操作"""
    - 禁止文件 IO
    - 禁止系统调用
    - 禁止网络访问
    - 执行超时保护 (默认 1 秒)
```

### 输入验证
```python
def validate_input(text: str) -> bool:
    - 长度限制 (默认 500 字符)
    - 敏感词过滤
    - 编码验证
```

---

## 扩展指南

### 添加新的 NLP 引擎
```python
from alice.nlp.base import Tokenizer

class MyTokenizer(Tokenizer):
    def tokenize(self, text: str) -> List[str]:
        # 自定义分词逻辑
        pass

# 注册到工厂
factory.register('my_tokenizer', MyTokenizer)
```

### 添加新的脚本引擎
```python
from alice.scripting.base import BaseScriptEngine

class JsonScriptEngine(BaseScriptEngine):
    def load_script(self, config: ScriptConfig) -> bool:
        # 加载 JSON 脚本
        pass
    
    def match(self, context: ScriptContext) -> Optional[ScriptMatchResult]:
        # 匹配逻辑
        pass
```

---

## 故障排查

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| LTP 初始化失败 | 模型文件缺失 | 检查 `ltp/models/` 目录 |
| Lua 引擎不可用 | lupa 未安装 | `pip install lupa` |
| 脚本加载失败 | YAML 格式错误 | 验证 YAML 语法 |
| 响应慢 | NLP 引擎过载 | 启用缓存或降级到 Jieba |

### 日志级别
```python
# 开发环境
log_level = "DEBUG"

# 生产环境
log_level = "WARNING"
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-02-26 | 模块化重构，拆分大文件 |
| 1.5 | 2026-02-20 | 添加 Bot 池架构 |
| 1.0 | 2026-02-01 | 初始版本 |
