# 变更日志 (CHANGELOG)

## [2.0.0] - 2026-02-20

### ⚠️ 破坏性变更

#### 移除的功能
- **NLP 模块**
  - 移除 `SentimentAnalyzer` 抽象接口 (`alice/nlp/base.py`)
  - 移除 `SentimentEngine` 情感分析引擎 (`alice/nlp/engines/sentiment_engine.py`)
  - 移除 `NlpFactory.create_sentiment_analyzer()` 方法
  - 移除 `NlpResult.sentiment` 字段
  - 移除 NLP 流水线中的 `sentiment` 组件支持

- **对话引擎**
  - 移除 `DialogueEngine` 中 NLP 流水线的 `sentiment` 组件
  - 移除语义信息中的 `sentiment` 字段传递
  - 移除上下文更新中的 `sentiment` 参数

- **脚本系统**
  - 移除 `YAMLScriptEngine._check_condition()` 中的情感条件判断：
    - `condition.sentiment`
    - `condition.sentiment_label`
    - `condition.sentiment_intensity`
    - `condition.emotion_type`
  - 删除 `emotion_responses.yaml` 情感响应脚本文件

- **意图匹配**
  - 移除 `IntentMatcher._calculate_confidence()` 中的情感匹配奖励

- **响应生成**
  - 移除 `ResponseGenerator._generate_from_script()` 中的情感上下文：
    - `context.sentiment`
    - `context.sentiment_detail`
    - `context.sentiment_label`

- **上下文管理**
  - 移除 `ContextManager.update()` 的 `sentiment` 参数
  - 移除 `ConversationTurn.sentiment` 字段
  - 移除 `ContextManager._get_emotion_trend()` 方法
  - 移除 `utils/context.py` 中的情感历史记录功能：
    - `_record_emotion()` 方法
    - `emotion_history` 属性相关逻辑

- **插件系统**
  - 移除 `PluginResult.sentiment` 字段

#### 文档更新
- 更新 `README.md`：移除情感分析相关描述
- 更新 `核心设计指导.md`：更新情感镜像模块说明
- 更新 `灵感来源.md`：更新情感分析相关说明
- 删除 `docs/情感分析模块使用指南.md`（如存在）

### 📈 性能提升
- 响应时间：减少约 5ms
- 内存占用：减少约 10MB

### 📝 迁移指南
详细迁移步骤请参考 [MIGRATION.md](MIGRATION.md)

### 🔄 替代方案
情感分析功能移除后，可使用以下方式实现类似效果：

1. **关键词匹配**：在 YAML 脚本中使用 `keywords` 条件
   ```yaml
   - intent: emotion_happy
     condition:
       keywords: ["开心", "高兴", "快乐"]
     templates:
       - "哇，听起来你心情不错！"
   ```

2. **情感词汇表**：在处理器中预定义情感词汇列表

---

## [1.x.x] - 2026-02-20 之前

### 功能
- ✅ 情感分析功能（基于词典和规则）
- ✅ 分词功能（jieba）
- ✅ 实体识别（基于词典和 LTP）
- ✅ 句法分析（LTP，可选）
- ✅ YAML 脚本引擎
- ✅ 上下文管理
- ✅ 插件系统

### 已知问题
- 情感分析功能依赖词典维护，扩展性有限
- 情感分析增加响应延迟约 5ms
- 情感分析增加内存占用约 10MB
