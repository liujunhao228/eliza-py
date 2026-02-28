# 脚本引擎条件匹配（Condition）文档

本文档介绍脚本引擎支持的条件匹配类型及使用方法。

## 概述

在 YAML 脚本中，`condition` 字段用于定义意图（intent）的触发条件。只有当所有条件都满足时，该意图才会被匹配。

```yaml
intents:
  - intent: example_intent
    condition:
      # 条件定义
    response: "回复内容"
```

---

## 条件类型

### 1. 语言分析类条件

#### `keywords` - 关键词匹配

匹配用户输入中是否包含指定关键词。

```yaml
condition:
  keywords: ["你好", "您好", "嗨"]
```

- **匹配逻辑**: 任意一个关键词出现在输入文本中即匹配
- **示例**: 输入"你好啊" 匹配 `keywords: ["你好"]`

---

#### `entities` - 命名实体匹配

匹配用户输入中是否包含指定类型的命名实体。

```yaml
condition:
  entities: ["PERSON", "LOCATION", "TIME"]
```

- **匹配逻辑**: 任意一个实体类型存在即匹配
- **常见实体类型**:
  - `PERSON` - 人名
  - `LOCATION` - 地点
  - `TIME` - 时间
  - `ORGANIZATION` - 组织

---

#### `pos_tags` - 词性标签匹配

匹配用户输入中是否包含指定词性的词语。

```yaml
condition:
  pos_tags: ["n", "v", "a"]
```

- **匹配逻辑**: 任意一个词性存在即匹配
- **常见词性**:
  - `n` - 名词
  - `v` - 动词
  - `a` - 形容词
  - `d` - 副词

---

#### `dependencies` - 依存关系匹配

匹配用户输入中是否包含指定依存关系。

```yaml
condition:
  dependencies: ["SBV", "VOB", "IOB"]
```

- **匹配逻辑**: 任意一个依存关系存在即匹配
- **常见依存关系**:
  - `SBV` - 主谓关系
  - `VOB` - 动宾关系
  - `IOB` - 间接宾语

---

#### `subject` - 主语匹配

匹配用户输入的主语是否包含指定词语。

```yaml
condition:
  subject: ["你", "您", "机器人"]
```

- **匹配逻辑**: 主语中包含任意一个指定词语即匹配

---

#### `predicate` - 谓语匹配

匹配用户输入的谓语是否包含指定词语。

```yaml
condition:
  predicate: ["是", "喜欢", "想要"]
```

- **匹配逻辑**: 谓语中包含任意一个指定词语即匹配

---

#### `object` - 宾语匹配

匹配用户输入的宾语是否包含指定词语。

```yaml
condition:
  object: ["苹果", "香蕉", "水果"]
```

- **匹配逻辑**: 宾语中包含任意一个指定词语即匹配

---

#### `triples` - 三元组匹配

匹配用户输入的主谓宾三元组。

```yaml
condition:
  triples:
    - subject: "你"
      predicate: "喜欢"
    - "水果"  # 简单匹配：三元组的任何部分包含该词
```

- **匹配逻辑**: 
  - 字典形式：精确匹配三元组的指定部分
  - 字符串形式：三元组的任何部分包含该词即匹配

---

#### `semantic_roles` - 语义角色匹配

匹配用户输入中是否包含指定语义角色。

```yaml
condition:
  semantic_roles: ["Agent", "Patient", "Time"]
```

- **匹配逻辑**: 任意一个语义角色存在即匹配

---

#### `semantic_deps` - 语义依存匹配

匹配用户输入中是否包含指定语义依存关系。

```yaml
condition:
  semantic_deps: ["体验者", "对象", "时间"]
```

- **匹配逻辑**: 任意一个语义依存关系存在即匹配

---

### 2. 上下文类条件

#### `min_tokens` / `max_tokens` - 分词数量范围

限制用户输入的分词数量范围。

```yaml
condition:
  min_tokens: 5   # 最少 5 个词
  max_tokens: 20  # 最多 20 个词
```

- **匹配逻辑**: 分词数量在 `[min_tokens, max_tokens]` 范围内即匹配
- **用途**: 区分简短回复和详细回复

---

#### `min_turns` / `max_turns` - 对话轮数范围

限制当前对话的轮数范围。

```yaml
condition:
  min_turns: 3   # 第 3 轮及之后
  max_turns: 5   # 第 5 轮及之前
```

- **匹配逻辑**: 当前轮数在 `[min_turns, max_turns]` 范围内即匹配
- **轮数计数**: 从 **0** 开始，每次对话 `+= 1`
- **用途**: 
  - 开场白：`max_turns: 1`
  - 特定轮次彩蛋：`min_turns: 5, max_turns: 5`
  - 长对话结束：`min_turns: 10`

---

### 3. 时间类条件

#### 小时条件

| 条件 | 说明 |
|------|------|
| `hour_gte` | 小时大于等于 |
| `hour_gt` | 小时大于 |
| `hour_lt` | 小时小于 |
| `hour_lte` | 小时小于等于 |
| `hour_eq` | 小时等于 |

```yaml
# 早上问候（5 点 -12 点）
condition:
  hour_gte: 5
  hour_lt: 12

# 深夜问候（23 点之后）
condition:
  hour_gte: 23
```

---

#### 星期条件

| 条件 | 说明 |
|------|------|
| `weekday_gte` | 星期几大于等于 |
| `weekday_gt` | 星期几大于 |
| `weekday_lt` | 星期几小于 |
| `weekday_lte` | 星期几小于等于 |
| `weekday_eq` | 星期几等于 |

**星期数值**: `0=周一, 1=周二, ..., 4=周五, 5=周六, 6=周日`

```yaml
# 周末问候（周六或周日）
condition:
  weekday_gte: 5

# 工作日问候（周一至周五）
condition:
  weekday_lt: 5

# 仅周一触发
condition:
  weekday_eq: 0
```

---

## 组合使用示例

### 示例 1: 分时段问候

```yaml
intents:
  - intent: good_morning
    condition:
      keywords: ["你好", "早"]
      hour_gte: 5
      hour_lt: 12
    response: "早上好！今天精神不错吧~"

  - intent: good_afternoon
    condition:
      keywords: ["你好"]
      hour_gte: 12
      hour_lt: 18
    response: "下午好！"

  - intent: good_night
    condition:
      keywords: ["你好", "嗨"]
      hour_gte: 18
    response: "晚上好呀！"
```

---

### 示例 2: 对话轮次控制

```yaml
intents:
  # 开场白（第 1 轮）
  - intent: opening
    condition:
      min_turns: 1
      max_turns: 1
    response: "你好呀！我是 AI 助手，很高兴认识你~"

  # 第 5 轮彩蛋
  - intent: turn5_easter_egg
    condition:
      min_turns: 5
      max_turns: 5
    response: "哇，我们已经聊了 5 轮了！送你一个小彩蛋 🎉"

  # 长对话结束（10 轮之后）
  - intent: long_chat_end
    condition:
      min_turns: 10
    response: "聊了很久啦，下次再聊！"
```

---

### 示例 3: 周末专属回复

```yaml
intents:
  # 周末闲聊
  - intent: weekend_chat
    condition:
      weekday_gte: 5  # 周六或周日
      min_tokens: 5
    response: "周末愉快！有什么好玩的事吗？"

  # 工作日快速回复
  - intent: weekday_quick
    condition:
      weekday_lt: 5   # 周一至周五
      max_tokens: 10
    response: "收到！"
```

---

### 示例 4: 复杂条件组合

```yaml
intents:
  # 周末早上且输入较长时的回复
  - intent: weekend_long_morning
    condition:
      weekday_gte: 5
      hour_gte: 8
      hour_lt: 12
      min_tokens: 10
    response: "周末早上好啊！看你说了这么多，是有什么有趣的事情想分享吗？"
```

---

## 注意事项

1. **所有条件为 AND 关系**: 必须同时满足所有条件才会匹配
2. **条件为空时**: 不设置 `condition` 或设置为空字典时，总是匹配
3. **轮数计数**: `turn_count` 从 **0** 开始计数
4. **星期数值**: `0=周一, 6=周日`（Python `datetime.weekday()` 标准）
5. **时间检查**: 使用服务器本地时间

---
