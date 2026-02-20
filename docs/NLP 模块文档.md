# Alice NLP 模块文档

## 📚 概述

Alice NLP 模块提供统一的自然语言处理接口，采用工厂模式管理多个引擎，支持分词、句法分析、实体识别和情感分析功能。

## 🏗️ 架构设计

### 核心组件

```
alice/nlp/
├── __init__.py              # 统一导出接口
├── base.py                  # 接口和数据类定义
├── factory.py               # NLP 工厂和流水线
├── semantic_analyzer.py     # 语义分析器
├── syntax_reassembly.py     # 句法重组引擎
├── engines/
│   ├── __init__.py
│   ├── jieba_engine.py      # Jieba 分词引擎
│   ├── ltp_engine.py        # LTP 句法分析引擎
│   ├── ner_engine.py        # 规则实体识别引擎
│   └── sentiment_engine.py  # 情感分析引擎
└── dictionaries/
    ├── __init__.py
    └── dictionary_manager.py # 词典管理器
```

### 接口设计

NLP 模块定义了四个独立接口，每个引擎只实现其职责范围内的功能：

| 接口 | 职责 | 实现引擎 |
|-----|------|---------|
| `Segmenter` | 分词 | `JiebaEngine` |
| `SyntaxAnalyzer` | 句法分析 | `LtpEngine` |
| `EntityRecognizer` | 实体识别 | `NerEngine` |
| `SentimentAnalyzer` | 情感分析 | `SentimentEngine` |

## 🚀 快速开始

### 方式 1：使用 NLP 工厂

```python
from alice.nlp import NlpFactory

# 创建工厂
factory = NlpFactory({'use_ltp': False})

# 创建单个引擎
segmenter = factory.create_segmenter()
sentiment = factory.create_sentiment_analyzer()
ner = factory.create_entity_recognizer()

# 创建流水线
pipeline = factory.create_pipeline(['jieba', 'ner', 'sentiment'])
result = pipeline.process("今天我很开心，和朋友一起去了公园")

print(f"分词：{result.tokens}")
print(f"实体：{[(e.entity_type.value, e.text) for e in result.entities]}")
print(f"情感：{result.sentiment:.2f}")
```

### 方式 2：直接使用引擎

```python
from alice.nlp import JiebaEngine, SentimentEngine, NerEngine

# 分词
jieba = JiebaEngine()
tokens = jieba.segment("你好世界")

# 情感分析
sentiment = SentimentEngine()
score, label = sentiment.analyze_with_label("我很高兴")
print(f"情感：{label} ({score:.2f})")

# 实体识别
ner = NerEngine()
entities = ner.recognize("我和朋友去了北京")
for e in entities:
    print(f"{e.text} ({e.entity_type.value})")
```

### 方式 3：在 DialogueEngine 中使用

```python
from alice.core import DialogueEngine

engine = DialogueEngine(use_ltp=False)
engine.initialize()
response = engine.respond("今天天气真好")
```

## 📦 引擎详解

### JiebaEngine - 分词引擎

**职责**: 仅负责中文分词

**特性**:
- 基于 jieba 库
- 未安装 jieba 时直接报错（不降级）
- 不支持实体识别和句法分析

```python
from alice.nlp import JiebaEngine

engine = JiebaEngine()
tokens = engine.segment("今天天气真好")
# ['今天', '天气', '真', '好']
```

### LtpEngine - LTP 句法分析引擎

**职责**: 完整 NLP 分析（分词 + 词性 + 句法 + 实体）

**特性**:
- 基于 LTP (Language Technology Platform)
- 支持懒加载
- 提供主谓宾提取

```python
from alice.nlp import LtpEngine

# 初始化时自动加载模型
engine = LtpEngine()

result = engine.analyze("我和朋友去了北京")
print(f"主语：{result.syntax.subject}")
print(f"谓语：{result.syntax.predicate}")
print(f"宾语：{result.syntax.object}")
print(f"实体：{[(e.entity_type.value, e.text) for e in result.entities]}")
```

**句法结构**:
- `SBV`: 主谓关系 → 主语
- `VOB`: 动宾关系 → 宾语
- `HED`: 核心谓词 → 谓语
- `ATT`: 定中关系 → 修饰语

### NerEngine - 规则实体识别引擎

**职责**: 基于规则的实体识别

**识别目标**:
- 人称代词（我、你、他、我们...）
- 称谓/关系（朋友、家人、老师、老板...）
- 时间词（今天、昨天、最近、刚才...）
- 中文人名（常见姓氏 + 名字模式）

```python
from alice.nlp import NerEngine

engine = NerEngine()
entities = engine.recognize("今天我和朋友去了北京，见到了李老师")

for e in entities:
    print(f"{e.text} -> {e.entity_type.value}")
```

**输出示例**:
```
我 -> pronoun
朋友 -> title
今天 -> time
北京 -> location
李老师 -> person
```

**可选 LTP 增强**:
```python
from alice.nlp import LtpEngine, NerEngine

ltp = LtpEngine()
ner = NerEngine(use_ltp=True, ltp_engine=ltp)
```

### SentimentEngine - 情感分析引擎

**职责**: 基于词典的情感分析

**特性**:
- 情感极性判断（正面/负面/中性）
- 否定词处理
- 程度副词加权

```python
from alice.nlp import SentimentEngine

engine = SentimentEngine()

# 分析并获取标签
score, label = engine.analyze_with_label("今天我很开心")
print(f"分数：{score:.2f}, 标签：{label}")

# 单独获取标签
label = engine.get_label(0.8)  # 'positive'
```

**情感分数范围**: -1.0 (极度负面) 到 1.0 (极度正面)

**否定词处理**:
```python
engine.analyze("不开心")  # 负分
engine.analyze("不难过")  # 正分
```

**程度副词加权**:
```python
engine.analyze("很开心")    # 基础分 * 1.5
engine.analyze("非常开心")  # 基础分 * 2.0
engine.analyze("有点开心")  # 基础分 * 0.6
```

## 🗂️ 词典管理

### DictionaryManager

统一管理所有词典文件，支持热加载。

```python
from alice.nlp import DictionaryManager

manager = DictionaryManager()

# 加载情感词典
emotion_words = manager.load('emotion_words')
print(f"正面词：{emotion_words['positive']}")
print(f"负面词：{emotion_words['negative']}")

# 加载实体模式词典
entity_patterns = manager.load('entity_patterns')
print(f"代词列表：{entity_patterns['pronouns']}")

# 加载意图关键词
intent_keywords = manager.load('intent_keywords')
print(f"叙事类关键词：{intent_keywords['narrative']}")
```

### 词典文件位置

```
alice/scripts/
├── dictionaries/
│   ├── emotion_words.yaml       # 情感词典
│   ├── entity_patterns.yaml     # 实体识别模式
│   └── intent_keywords.yaml     # 意图关键词
└── rules/
    └── sentiment_rules.yaml     # 情感分析规则
```

### 自定义词典

在 `alice/scripts/dictionaries/` 目录下添加 YAML 文件：

```yaml
# custom_emotions.yaml
positive:
  - 给力的
  - 赞
  - 牛逼

negative:
  - 拉胯
  - 无语
  - emo
```

## 🔄 NLP 流水线

NlpPipeline 按顺序执行多个引擎，合并结果：

```python
from alice.nlp import NlpFactory

factory = NlpFactory({'use_ltp': True})

# 创建包含所有组件的流水线
pipeline = factory.create_pipeline(['jieba', 'syntax', 'ner', 'sentiment'])
result = pipeline.process("今天我和朋友去了北京，感到非常开心")

# 结果包含所有引擎的输出
print(f"分词：{result.tokens}")
print(f"句法：{result.syntax.subject} - {result.syntax.predicate} - {result.syntax.object}")
print(f"实体：{[(e.entity_type.value, e.text) for e in result.entities]}")
print(f"情感：{result.sentiment:.2f}")
```

## 📊 数据类

### NlpResult

NLP 分析结果的标准数据结构：

```python
@dataclass
class NlpResult:
    text: str                    # 原始文本
    tokens: List[str]            # 分词结果
    sentiment: float             # 情感分数
    entities: List[Entity]       # 实体列表
    syntax: Optional[SyntaxStructure]  # 句法结构
```

### Entity

命名实体数据类：

```python
@dataclass
class Entity:
    text: str           # 实体文本
    entity_type: EntityType  # 实体类型
    start_pos: int      # 起始位置
    end_pos: int        # 结束位置
    confidence: float   # 置信度
```

### SyntaxStructure

句法结构数据类：

```python
@dataclass
class SyntaxStructure:
    words: List[str]           # 词列表
    poses: List[str]           # 词性标注
    subject: str               # 主语
    predicate: str             # 谓语
    object: str                # 宾语
    modifiers: Dict[str, List[str]]  # 修饰语
```

## ⚠️ 注意事项

### 1. jieba 是硬依赖

未安装 jieba 时直接抛出 `DependencyError`，不做降级处理：

```python
# 未安装 jieba 时会报错
from alice.nlp import JiebaEngine  # DependencyError: jieba 库未安装
```

**解决方案**: `pip install jieba`

### 2. LTP 是可选依赖

LTP 用于深度句法分析，不安装时只影响句法分析功能：

```python
from alice.nlp import LtpEngine

# LTP 未安装时抛出 DependencyError
engine = LtpEngine()  # DependencyError: LTP 库未安装
```

**可选安装**: `pip install ltp>=4.2.10`

### 3. 词典文件必须存在

确保 `alice/scripts/dictionaries/` 目录下的 YAML 文件存在，否则 `DictionaryManager` 返回空字典。

## 🔧 高级用法

### 引擎缓存

工厂会缓存已创建的引擎：

```python
factory = NlpFactory()

# 第一次创建
engine1 = factory.create_sentiment_analyzer()

# 第二次获取（从缓存）
engine2 = factory.create_sentiment_analyzer()

assert engine1 is engine2  # True
```

### 清除缓存

```python
factory.clear_cache()
```

### 自定义引擎配置

```python
config = {
    'use_ltp': True,
    'ltp_model_path': '/path/to/model',
}
factory = NlpFactory(config=config)
```

## 📈 性能基准

| 引擎 | 响应时间 | 内存占用 | 依赖 |
|-----|---------|---------|------|
| JiebaEngine | <10ms | ~20MB | jieba |
| SentimentEngine | <5ms | ~10MB | 无 |
| NerEngine | <10ms | ~10MB | 无 |
| LtpEngine | <100ms | ~200MB | ltp |

## 🧪 测试

运行 NLP 模块测试：

```bash
python test_nlp_refactor.py
```

---

**文档版本**: v3.0
**最后更新**: 2026 年 2 月 20 日
**适用版本**: Alice v3.0+
