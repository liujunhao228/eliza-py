# 迁移指南 v2.0 - 移除情感分析功能

本文档帮助您从 v1.x 版本迁移到 v2.0 版本。v2.0 是一个**破坏性变更**版本，移除了情感分析功能。

## 📋 变更概述

### 移除的功能
- `SentimentAnalyzer` 抽象接口
- `SentimentEngine` 情感分析引擎
- NLP 流水线中的 `sentiment` 组件
- YAML 脚本中的情感条件判断（`sentiment`, `sentiment_label`, `sentiment_intensity`, `emotion_type`）
- `NlpResult` 中的 `sentiment` 字段

### 保留的功能
- ✅ 分词功能（JiebaEngine）
- ✅ 实体识别（NerEngine）
- ✅ 句法分析（LtpEngine，可选）
- ✅ YAML 脚本引擎（关键词匹配、实体条件）
- ✅ 上下文管理
- ✅ 插件系统

## 🔧 代码迁移

### 1. NLP 流水线

**v1.x 代码：**
```python
from alice.nlp import NlpFactory

factory = NlpFactory()
pipeline = factory.create_pipeline(['jieba', 'ner', 'sentiment'])
result = pipeline.process("今天我很开心")

# 访问情感分数
print(f"情感分数：{result.sentiment}")
```

**v2.0 代码：**
```python
from alice.nlp import NlpFactory

factory = NlpFactory()
pipeline = factory.create_pipeline(['jieba', 'ner'])
result = pipeline.process("今天我很开心")

# sentiment 字段已移除
print(f"tokens: {result.tokens}")
print(f"entities: {result.entities}")
```

### 2. 直接使用情感分析器

**v1.x 代码：**
```python
from alice.nlp import SentimentEngine

sentiment = SentimentEngine()
score, label = sentiment.analyze_with_label("我很高兴")
print(f"分数：{score}, 标签：{label}")
```

**v2.0 代码：**
```python
# 情感分析功能已移除
# 替代方案：使用关键词匹配

# 在 YAML 脚本中使用 keywords 条件
# 示例：
# - intent: emotion_happy
#   condition:
#     keywords: ["开心", "高兴", "快乐", "愉快"]
#   templates:
#     - "哇，听起来你心情不错！"
```

### 3. YAML 脚本条件

**v1.x 脚本：**
```yaml
- intent: sentiment_positive
  priority: 85
  condition:
    sentiment_label: "positive"
  templates:
    - "听得出你现在心情不错！"

- intent: sentiment_negative
  priority: 90
  condition:
    sentiment_label: "negative"
    sentiment_intensity: "strong"
  templates:
    - "听起来这件事对你影响真的很大。"
```

**v2.0 脚本：**
```yaml
- intent: emotion_happy
  priority: 85
  condition:
    keywords: ["开心", "高兴", "快乐", "愉快", "兴奋"]
  templates:
    - "哇，听得出你现在心情不错！"

- intent: emotion_sad
  priority: 90
  condition:
    keywords: ["难过", "伤心", "悲伤", "痛苦", "沮丧"]
  templates:
    - "听起来这件事让你很难受。"
```

### 4. ContextManager 更新

**v1.x 代码：**
```python
context_manager.update(
    user_input="今天天气真好",
    bot_response="是啊，适合出去玩",
    entities=[("time", "今天")],
    sentiment=0.8,  # 情感分数
    intent="greeting"
)
```

**v2.0 代码：**
```python
context_manager.update(
    user_input="今天天气真好",
    bot_response="是啊，适合出去玩",
    entities=[("time", "今天")],
    intent="greeting"
    # sentiment 参数已移除
)
```

### 5. 插件 PluginResult

**v1.x 代码：**
```python
from alice.plugins import PluginResult

result = PluginResult(
    success=True,
    response="你好",
    entities=[("person", "小明")],
    sentiment=0.5,  # 情感分数
    intent="greeting"
)
```

**v2.0 代码：**
```python
from alice.plugins import PluginResult

result = PluginResult(
    success=True,
    response="你好",
    entities=[("person", "小明")],
    intent="greeting"
    # sentiment 字段已移除
)
```

## 📦 依赖变更

### 可移除的依赖
无（情感分析功能使用内置词典，无额外依赖）

### 性能提升
- 响应时间：预计提升 ~5ms
- 内存占用：预计减少 ~10MB

## ⚠️ 兼容性说明

### 不兼容的 API
- `alice.nlp.SentimentAnalyzer` - 已移除
- `alice.nlp.SentimentEngine` - 已移除
- `NlpFactory.create_sentiment_analyzer()` - 已移除
- `NlpResult.sentiment` - 已移除
- `ContextManager.update(sentiment=...)` - 参数已移除
- `PluginResult.sentiment` - 字段已移除

### YAML 脚本不兼容的条件
- `condition.sentiment` - 不再支持
- `condition.sentiment_label` - 不再支持
- `condition.sentiment_intensity` - 不再支持
- `condition.emotion_type` - 不再支持

## 🔄 迁移步骤

1. **备份现有代码和数据**
   ```bash
   git checkout -b backup-before-v2-migration
   ```

2. **更新代码库**
   ```bash
   git pull origin main
   ```

3. **更新 NLP 流水线调用**
   - 移除 `create_pipeline()` 中的 `'sentiment'` 组件
   - 移除所有访问 `result.sentiment` 的代码

4. **更新 YAML 脚本**
   - 将情感条件改为关键词匹配
   - 参考上方的"YAML 脚本条件"示例

5. **更新插件代码**
   - 移除 `PluginResult` 中的 `sentiment` 字段

6. **运行测试**
   ```bash
   pytest tests/
   ```

7. **验证功能**
   ```bash
   python main.py
   ```

## 📞 需要帮助？

如果在迁移过程中遇到问题，请：
1. 查看 [GitHub Issues](https://github.com/yourusername/eliza-py/issues)
2. 提交新的 Issue 并附上错误信息

## 📝 版本历史

- **v2.0.0** - 移除情感分析功能（破坏性变更）
- **v1.x** - 包含情感分析功能的最后一个版本
