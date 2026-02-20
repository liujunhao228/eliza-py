# Alice 脚本编写指南

## 目录
1. [简介](#简介)
2. [基本语法](#基本语法)
3. [核心概念](#核心概念)
4. [条件匹配](#条件匹配)
5. [响应模板](#响应模板)
6. [实用示例](#实用示例)
7. [最佳实践](#最佳实践)

## 简介

Alice 脚本系统使用 YAML 格式定义对话规则，通过意图(Intent)驱动的方式实现智能化对话响应。每个脚本意图包含匹配条件、优先级和响应模板，系统根据输入内容和上下文自动选择最合适的响应。

### 脚本文件结构
```
alice/
└── scripts/
    ├── mapping.yaml          # 代词映射和句式转换规则
    ├── semantic_tags.yaml    # 语义标签词库
    ├── emotion_responses.yaml # 情感驱动响应脚本
    ├── curiosity_scripts.yaml # 好奇心驱动脚本
    └── yaml_script_engine.py # 脚本引擎实现
```

## 基本语法

### 脚本意图结构
```yaml
- intent: 意图名称
  priority: 优先级数字(0-100)
  condition: 
    匹配条件对象
  templates:
    - "响应模板1"
    - "响应模板2"
  keyword_only: false  # 可选，默认false
```

### 字段说明
- **intent**: 意图的唯一标识名
- **priority**: 优先级，数值越高优先级越高(0-100)
- **condition**: 匹配条件对象，决定何时触发此意图
- **templates**: 响应模板列表，系统随机选择一个
- **keyword_only**: 是否仅关键词匹配，true时不进行代词替换

## 核心概念

### 优先级调度
```
P0 (90-100): 情感危机或极端情绪
P1 (70-89):  实体挖掘和深度对话
P2 (40-69):  叙事助推和对话延续
P3 (0-39):   通用回应和兜底响应
```

### 匹配机制
系统按照以下顺序匹配：
1. 按优先级从高到低排序
2. 依次检查每个意图的条件
3. 第一个完全匹配的意图被选中
4. 从该意图的模板中随机选择一个响应

## 条件匹配

### 1. 实体条件
```yaml
condition:
  entities: ["person", "third_person", "location"]
```
匹配用户提到的特定类型实体。

### 2. 情感条件
#### 情感标签匹配
```yaml
condition:
  sentiment_label: "positive"  # positive|negative|neutral
```

#### 情感强度匹配
```yaml
condition:
  sentiment_intensity: "strong"  # strong|moderate|weak
```

#### 具体情感类型
```yaml
condition:
  emotion_type: "joy"  # joy|anger|sadness|fear|anxiety|disgust|surprise
```

### 3. 关键词条件
```yaml
condition:
  keywords: ["喜欢", "讨厌", "想去", "觉得"]
```
匹配包含指定关键词的输入。

### 4. 词性条件
```yaml
condition:
  pos_tags: ["VERB", "NOUN"]  # 动词、名词等
```

### 5. 复合条件
```yaml
condition:
  sentiment_label: "negative"
  keywords: ["难过", "伤心"]
  entities: ["person"]
```
多个条件同时满足才触发。

## 响应模板

### 1. 基础模板
```yaml
templates:
  - "听起来很不错！"
  - "这很有意思，能详细说说吗？"
  - "我很好奇后续发展呢。"
```

### 2. 实体占位符
```yaml
templates:
  - "你提到的{person}，是个什么样的人呢？"
  - "在{location}的经历一定很特别吧？"
  - "关于{organization}，你有什么看法？"
```

### 3. 情感镜像
```yaml
templates:
  - "我能感受到你的{emotion}，这种感觉持续多久了？"
  - "听你这么说，我也觉得有点{emotion}呢。"
```

### 4. 对话延续
```yaml
templates:
  - "后来呢？"
  - "然后发生了什么？"
  - "能再详细说说那个过程吗？"
```

## 实用示例

### 示例1：情感支持脚本
```yaml
- intent: emotional_support
  priority: 85
  condition:
    sentiment_label: "negative"
    keywords: ["难过", "伤心", "痛苦"]
  templates:
    - "听起来你现在很难受，想聊聊具体发生了什么吗？"
    - "我能感受到你的痛苦，这种感觉一定很不好受。"
    - "难过的时候有人陪伴很重要，你还好吗？"

- intent: positive_reinforcement
  priority: 80
  condition:
    sentiment_label: "positive"
    keywords: ["开心", "高兴", "快乐"]
  templates:
    - "哇，听得出你现在很开心！这种好心情是因为什么呀？"
    - "真为你高兴！这种感觉一定很棒吧？"
    - "能感受到你的喜悦，这种时刻最值得珍惜呢。"
```

### 示例2：好奇心驱动脚本
```yaml
- intent: person_inquiry
  priority: 75
  condition:
    entities: ["person"]
  templates:
    - "你提到的这个人，你们关系怎么样？"
    - "听起来{person}在你生活中很重要呢。"
    - "能多说说{person}的故事吗？"

- intent: event_followup
  priority: 70
  condition:
    keywords: ["发生", "遇到", "经历"]
    pos_tags: ["VERB"]
  templates:
    - "这件事对你产生了什么影响？"
    - "当时的感受现在还记忆犹新吗？"
    - "从这次经历中学到了什么？"
```

### 示例3：叙事助推脚本
```yaml
- intent: story_continuation
  priority: 60
  condition:
    min_tokens: 10  # 至少10个词
  templates:
    - "然后呢？我很想知道后续。"
    - "接下来发生了什么有趣的事？"
    - "这个故事还有后续吗？"

- intent: detail_probe
  priority: 55
  condition:
    keywords: ["但是", "不过", "然而"]
  templates:
    - "哦？这里有个转折，能详细说说吗？"
    - "听起来有不同寻常的地方呢。"
    - "这个转折很有意思，具体情况是怎样的？"
```

### 示例4：专业咨询脚本
```yaml
- intent: career_advice
  priority: 65
  condition:
    keywords: ["工作", "职业", "上班", "面试"]
    sentiment_label: "negative"
  templates:
    - "职场压力确实不容易，你现在最困扰的是什么？"
    - "工作上的挫折很正常，你希望得到哪方面的建议？"
    - "能具体说说工作中遇到的困难吗？"

- intent: relationship_counseling
  priority: 70
  condition:
    keywords: ["感情", "恋爱", "分手", "吵架"]
    entities: ["person"]
  templates:
    - "感情问题确实复杂，你觉得核心矛盾在哪里？"
    - "和{person}的关系现状让你有什么感受？"
    - "这段关系中你最在意的是什么？"
```

## 最佳实践

### 1. 优先级设置建议
- **紧急情感支持**: 90-100
- **重要实体挖掘**: 70-89
- **一般对话延续**: 40-69
- **兜底通用回应**: 0-39

### 2. 模板设计原则
```
✅ 好的设计：
- 开放性问题，鼓励用户表达
- 体现理解和共情
- 自然流畅的语言风格
- 适当的个性化元素

❌ 避免的设计：
- 封闭式问题（只能回答是/否）
- 过于机械化的回应
- 重复使用相同模板
- 忽视上下文信息
```

### 3. 条件匹配优化
```yaml
# ✅ 推荐：具体明确的条件
condition:
  sentiment_label: "negative"
  keywords: ["焦虑", "担心"]
  entities: ["person"]

# ❌ 避免：过于宽泛的条件
condition:
  keywords: ["好", "不错"]  # 太宽泛，容易误匹配
```

### 4. 多样化响应策略
```yaml
# 为同一意图提供多种表达方式
templates:
  - "听起来你对此很有想法呢。"           # 温和型
  - "哇，这个观点很有意思！"             # 热情型  
  - "嗯，我明白你的意思。"               # 理解型
  - "能具体展开说说吗？"                 # 探究型
```

### 5. 上下文感知
```yaml
# 结合实体信息的个性化回应
- intent: personalized_greeting
  priority: 80
  condition:
    entities: ["person"]
  templates:
    - "{person}最近怎么样？"
    - "好久不见{person}了，近况如何？"
```

### 6. 错误处理和边界情况
```yaml
# 处理简短输入
- intent: short_input_response
  priority: 30
  condition:
    max_tokens: 3  # 很短的输入
  templates:
    - "能再详细说说吗？"
    - "我想更好地理解你的想法。"
    - "可以多分享一些细节吗？"

# 处理重复内容
- intent: repetition_handler
  priority: 25
  condition:
    # 检测重复模式的逻辑
  templates:
    - "我注意到你提到了类似的内容..."
    - "这个问题对你来说很重要呢。"
```

## 高级技巧

### 1. 动态模板变量
除了预定义的实体占位符，还可以结合运行时上下文：

```yaml
templates:
  - "你说{topic}的时候，语气听起来{tone}。"
  - "关于{recent_entity}，你刚才提到的感受是{emotion}。"
```

### 2. 渐进式深入
```yaml
# 第一次提及某话题
- intent: initial_mention
  priority: 60
  condition:
    # 首次提到某个实体
  templates:
    - "第一次听到{entity}，能介绍一下吗？"

# 后续深入讨论
- intent: deep_dive
  priority: 75
  condition:
    # 多次提及同一实体
  templates:
    - "看来{entity}对你影响很大，能说说具体的经历吗？"
```

### 3. 情感强度分级响应
```yaml
- intent: mild_concern
  priority: 70
  condition:
    sentiment_intensity: "weak"
    sentiment_label: "negative"
  templates:
    - "看起来有点小困扰呢，怎么回事？"

- intent: serious_support
  priority: 90
  condition:
    sentiment_intensity: "strong"
    sentiment_label: "negative"
  templates:
    - "听起来你现在承受着很大的压力，需要聊聊吗？"
```

这份指南涵盖了 Alice 脚本系统的主要功能和使用方法。通过合理运用这些概念和技巧，你可以创建出更加智能和人性化的对话体验。
提示：对于高手而言，编写脚本时，少使用关键词匹配，多使用开放性设置，更加以假乱真哦。