# Alice API 文档

## 📖 概述

本文档详细描述了 Alice 项目的 API 接口规范，包括类、方法、参数和返回值的详细说明。

## 🏗️ 核心架构 API

### AliceBot 类

**位置**: `alice/alice_v2.py`

#### 构造函数
```python
def __init__(
    self,
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    enable_logging: bool = True,
    enable_plugins: bool = True,
    cache_size: int = 100,
    use_ltp: bool = False,
) -> None
```

**参数说明：**
- `script_file` (Optional[str]): YAML 脚本文件路径，默认为 None
- `rules_file` (Optional[str]): 反射规则文件路径，默认为 None  
- `enable_logging` (bool): 是否启用对话日志，默认为 True
- `enable_plugins` (bool): 是否启用插件系统，默认为 True
- `cache_size` (int): 缓存最大条目数，默认为 100
- `use_ltp` (bool): 是否使用 LTP 增强模式，默认为 False

#### 主要方法

##### respond()
```python
def respond(self, user_input: str) -> str
```
**功能**: 生成对用户输入的响应

**参数**: 
- `user_input` (str): 用户输入的文本

**返回值**: 
- `str`: 生成的机器人响应

**异常**: 
- 可能在内部处理异常，返回友好的错误消息

**示例**:
```python
bot = AliceBot()
response = bot.respond("今天天气很好")
print(response)  # "听起来很不错呢！你还做了什么开心的事吗？"
```

##### get_conversation_summary()
```python
def get_conversation_summary(self) -> Dict[str, Any]
```
**功能**: 获取当前对话的摘要信息

**返回值**: 
```python
{
    "turns": int,           # 对话轮次数
    "recent_turns": List,   # 最近几轮对话
    "entities": Dict,       # 提及的实体统计
    "topics": List,         # 话题列表
    "stats": Dict           # 统计信息
}
```

##### get_stats()
```python
def get_stats(self) -> Dict[str, Any]
```
**功能**: 获取系统运行统计信息

**返回值**:
```python
{
    "initialized": bool,              # 是否已初始化
    "cache": {                        # 缓存统计
        "size": int,
        "hits": int,
        "misses": int,
        "hit_rate": float
    },
    "monitor": {                      # 监控统计
        "total_requests": int,
        "avg_response_time": float,
        "error_rate": float
    },
    "dialogue_engine": Dict           # 对话引擎统计
}
```

##### reset()
```python
def reset(self) -> None
```
**功能**: 重置对话状态，清空上下文和缓存

##### cleanup()
```python
def cleanup(self) -> None
```
**功能**: 清理系统资源，关闭所有连接

## 🧠 核心引擎 API

### DialogueEngine 类

**位置**: `alice/core/dialogue_engine.py`

#### 构造函数
```python
def __init__(
    self,
    script_file: Optional[str] = None,
    rules_file: Optional[str] = None,
    enable_plugins: bool = True,
    use_ltp: bool = False,
) -> None
```

#### 核心方法

##### initialize()
```python
def initialize(self) -> bool
```
**功能**: 初始化对话引擎组件

**返回值**: 
- `bool`: 初始化是否成功

##### respond()
```python
def respond(self, user_input: str) -> str
```
**功能**: 处理用户输入并生成响应

**参数**: 
- `user_input` (str): 标准化的用户输入

**返回值**: 
- `str`: 生成的响应文本

##### get_context_summary()
```python
def get_context_summary(self) -> Dict[str, Any]
```
**功能**: 获取对话上下文摘要

**返回值**:
```python
{
    "turns": int,                    # 对话轮次数
    "recent_turns": List[Dict],      # 最近对话历史
    "entities_mentioned": Dict,      # 实体提及统计
    "current_topic": str,            # 当前话题
    "conversation_flow": Dict        # 对话流向分析
}
```

##### get_stats()
```python
def get_stats(self) -> Dict[str, Any]
```
**功能**: 获取引擎运行统计

## 🔍 处理器 API

### SemanticAnalyzer 类

**位置**: `alice/processors/semantic_analyzer.py`

#### 构造函数
```python
def __init__(
    self,
    use_ltp: bool = False,
    ltp_engine: Optional[Any] = None,
) -> None
```

#### 核心方法

##### analyze()
```python
def analyze(self, text: str) -> Dict[str, Any]
```
**功能**: 分析文本语义信息

**参数**: 
- `text` (str): 待分析的文本

**返回值**:
```python
{
    "tokens": List[str],             # 分词结果
    "sentiment": float,              # 情感分数 [-1.0, 1.0]
    "intent": str,                   # 意图类型
    "entities": List[Tuple[str, str]], # 实体列表 [("类型", "文本")]
    "original_text": str,            # 原始文本
    "standardized_text": str,        # 标准化文本
    "use_ltp": bool                  # 是否使用了 LTP
}
```

**示例**:
```python
analyzer = SemanticAnalyzer()
result = analyzer.analyze("我觉得今天很开心")
print(result["sentiment"])  # 0.8
print(result["intent"])     # "emotion"
```

##### analyze_with_label()
```python
def analyze_with_label(self, text: str) -> Dict[str, Any]
```
**功能**: 分析文本并添加情感标签

**返回值**:
```python
{
    # 包含 analyze() 的所有字段
    "sentiment_label": str  # "positive"|"negative"|"neutral"
}
```

### TextPreprocessor 类

**位置**: `alice/processors/text_processor.py`

#### 核心方法

##### standardize_text()
```python
def standardize_text(self, text: str) -> str
```
**功能**: 标准化文本格式

**参数**: 
- `text` (str): 原始文本

**返回值**: 
- `str`: 标准化后的文本

##### segment_text()
```python
def segment_text(self, text: str) -> List[str]
```
**功能**: 对文本进行分词

**参数**: 
- `text` (str): 待分词文本

**返回值**: 
- `List[str]`: 分词结果列表

## 🔌 插件系统 API

### BasePlugin 抽象基类

**位置**: `alice/plugins/base_plugin.py`

#### 核心抽象方法

##### initialize()
```python
@abstractmethod
def initialize(self) -> bool
```
**功能**: 初始化插件资源

**返回值**: 
- `bool`: 初始化是否成功

##### process_input()
```python
@abstractmethod
def process_input(self, text: str, context: Dict[str, Any]) -> PluginResult
```
**功能**: 处理用户输入

**参数**: 
- `text` (str): 用户输入文本
- `context` (Dict): 对话上下文

**返回值**: 
- `PluginResult`: 处理结果对象

#### PluginResult 数据类
```python
@dataclass
class PluginResult:
    success: bool                    # 处理是否成功
    response: Optional[str] = None   # 生成的响应
    entities: Optional[List[tuple]] = None  # 发现的实体
    sentiment: Optional[float] = None       # 情感分数
    intent: Optional[str] = None            # 识别的意图
    metadata: Optional[Dict[str, Any]] = None  # 元数据
```

### PluginManager 类

**位置**: `alice/plugins/plugin_manager.py`

#### 核心方法

##### register_plugin()
```python
def register_plugin(
    self,
    name: str,
    plugin_class: Type[BasePlugin],
    config: Optional[Dict] = None,
) -> bool
```
**功能**: 注册新插件

**参数**: 
- `name` (str): 插件名称
- `plugin_class` (Type[BasePlugin]): 插件类
- `config` (Optional[Dict]): 插件配置

**返回值**: 
- `bool`: 注册是否成功

##### initialize_all()
```python
def initialize_all(self) -> bool
```
**功能**: 初始化所有已注册插件

**返回值**: 
- `bool`: 初始化是否全部成功

##### process_input()
```python
def process_input(self, text: str, context: Dict) -> List[PluginResult]
```
**功能**: 批量处理用户输入

**参数**: 
- `text` (str): 用户输入
- `context` (Dict): 对话上下文

**返回值**: 
- `List[PluginResult]`: 按优先级排序的处理结果

## 📊 管理器 API

### ConfigManager 类

**位置**: `alice/managers/config_manager.py`

#### 核心方法

##### get()
```python
def get(self, key: str, default: Any = None) -> Any
```
**功能**: 获取配置值

**参数**: 
- `key` (str): 配置键，支持点号分隔（如 "plugin.curiosity.priority"）
- `default` (Any): 默认值

**返回值**: 
- `Any`: 配置值

##### set()
```python
def set(self, key: str, value: Any) -> None
```
**功能**: 设置配置值

**参数**: 
- `key` (str): 配置键
- `value` (Any): 配置值

##### load_from_file()
```python
def load_from_file(self, filepath: str) -> None
```
**功能**: 从文件加载配置

**参数**: 
- `filepath` (str): 配置文件路径

### ContextManager 类

**位置**: `alice/managers/context_manager.py`

#### 核心方法

##### update()
```python
def update(
    self,
    user_input: str,
    bot_response: str,
    entities: List[tuple],
    sentiment: float,
    intent: str,
) -> None
```
**功能**: 更新对话上下文

##### get_recent_turns()
```python
def get_recent_turns(self, count: int) -> List[Dict]
```
**功能**: 获取最近的对话轮次

**参数**: 
- `count` (int): 获取轮次数

**返回值**:
```python
[
    {
        "user": str,        # 用户输入
        "bot": str,         # 机器人响应
        "timestamp": float, # 时间戳
        "entities": List,   # 实体列表
        "sentiment": float  # 情感分数
    }
]
```

## 💾 缓存 API

### IntelligentCache 类

**位置**: `alice/cache/intelligent_cache.py`

#### 构造函数
```python
def __init__(self, max_size: int = 100) -> None
```

#### 核心方法

##### get()
```python
def get(self, key: str) -> Optional[Any]
```
**功能**: 获取缓存值

**参数**: 
- `key` (str): 缓存键

**返回值**: 
- `Optional[Any]`: 缓存值或 None

##### set()
```python
def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None
```
**功能**: 设置缓存值

**参数**: 
- `key` (str): 缓存键
- `value` (Any): 缓存值
- `ttl` (Optional[int]): 过期时间（秒）

##### get_stats()
```python
def get_stats(self) -> Dict[str, Any]
```
**功能**: 获取缓存统计信息

**返回值**:
```python
{
    "size": int,          # 当前缓存大小
    "max_size": int,      # 最大大小
    "hits": int,          # 命中次数
    "misses": int,        # 未命中次数
    "hit_rate": float,    # 命中率
    "evictions": int      # 淘汰次数
}
```

## 📈 监控 API

### UnifiedMonitor 类

**位置**: `alice/utils/monitor.py`

#### 核心方法

##### record_interaction()
```python
def record_interaction(
    self,
    request_time: float,
    response_time: float,
    success: bool,
    metadata: Optional[Dict] = None,
) -> None
```
**功能**: 记录一次交互数据

##### log_error()
```python
def log_error(self, operation: str, error: Exception, context: Dict) -> None
```
**功能**: 记录错误信息

##### get_stats()
```python
def get_stats(self) -> Dict[str, Any]
```
**功能**: 获取监控统计

## 📋 异常处理

### 自定义异常类

```python
class AliceException(Exception):
    """Alice 基础异常类"""
    pass

class InitializationError(AliceException):
    """初始化错误"""
    pass

class ProcessingError(AliceException):
    """处理错误"""
    pass

class ConfigurationError(AliceException):
    """配置错误"""
    pass
```

### 异常处理最佳实践

```python
try:
    response = bot.respond(user_input)
except InitializationError as e:
    logger.error(f"初始化失败: {e}")
    response = "系统正在初始化，请稍后再试"
except ProcessingError as e:
    logger.error(f"处理失败: {e}")
    response = "抱歉，我没有理解你说的话"
except Exception as e:
    logger.critical(f"未知错误: {e}")
    response = "系统出现了一些问题"
```

## 🔧 配置选项

### 环境变量配置

```python
# 系统配置
ALICE_USE_LTP = "true"          # 启用 LTP
ALICE_CACHE_SIZE = "200"        # 缓存大小
ALICE_LOG_LEVEL = "INFO"        # 日志级别

# 插件配置
ALICE_PLUGIN_CURIOSITY_ENABLED = "true"
ALICE_PLUGIN_CURIOSITY_PRIORITY = "50"

# 性能配置
ALICE_MIN_COMPLEXITY = "10"     # LTP 最小复杂度阈值
ALICE_RESPONSE_TIMEOUT = "30"   # 响应超时时间
```

### 配置文件格式

```json
{
  "system": {
    "use_ltp": true,
    "cache_size": 200,
    "log_level": "INFO"
  },
  "plugins": {
    "curiosity": {
      "enabled": true,
      "priority": 50,
      "config": {
        "min_response_delay": 1.0,
        "max_response_delay": 3.0
      }
    }
  },
  "performance": {
    "min_complexity": 10,
    "response_timeout": 30
  }
}
```

## 🧪 测试接口

### 单元测试示例

```python
import pytest
from alice.alice_v2 import AliceBot

def test_basic_respond():
    bot = AliceBot()
    response = bot.respond("你好")
    assert isinstance(response, str)
    assert len(response) > 0

def test_semantic_analysis():
    from alice.processors import SemanticAnalyzer
    analyzer = SemanticAnalyzer()
    result = analyzer.analyze("我觉得很开心")
    assert -1.0 <= result["sentiment"] <= 1.0
    assert result["intent"] in ["emotion", "general"]
```

## 📊 性能基准

### 响应时间指标

| 操作 | 平均时间 | 95%时间 | 99%时间 |
|------|----------|---------|---------|
| 基础响应 | 25ms | 50ms | 100ms |
| LTP 增强 | 150ms | 250ms | 400ms |
| 插件处理 | 50ms | 100ms | 200ms |

### 内存使用

| 配置 | 内存占用 |
|------|----------|
| 基础模式 | 50-80MB |
| LTP 模式 | 150-250MB |
| 完整模式 | 200-300MB |

---
**API 版本**: v2.0  
**最后更新**: 2026年2月19日  
**兼容性**: Python 3.7+