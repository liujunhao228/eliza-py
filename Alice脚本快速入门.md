# Alice 脚本快速入门

## 5分钟上手指南

### 1. 基础结构
每个脚本意图包含四个核心要素：

```yaml
- intent: 意图名称        # 唯一标识
  priority: 80           # 优先级(0-100)
  condition: 条件对象     # 触发条件
  templates:             # 响应模板列表
    - "模板1"
    - "模板2"
```

### 2. 简单示例
```yaml
# 最简单的问候回应
- intent: simple_greeting
  priority: 50
  condition:
    keywords: ["你好"]
  templates:
    - "你好！有什么可以帮助你的吗？"
```

### 3. 常用条件类型

**关键词匹配**
```yaml
condition:
  keywords: ["开心", "高兴", "快乐"]
```

**情感匹配**
```yaml
condition:
  sentiment_label: "positive"  # positive|negative|neutral
```

**实体匹配**
```yaml
condition:
  entities: ["person", "location"]
```

### 4. 实战练习

创建一个处理"感谢"的脚本：

```yaml
- intent: gratitude_response
  priority: 70
  condition:
    keywords: ["谢谢", "感谢", "谢谢你"]
  templates:
    - "不客气！能帮助到你我很开心。"
    - "举手之劳，不用这么客气啦～"
    - "很高兴能帮到你！"
```

## 常见问题解答

**Q: 如何设置脚本优先级？**
A: 优先级数值越高越优先，建议：
- 紧急情感支持：90-100
- 重要话题讨论：70-89
- 一般对话延续：40-69
- 兜底回应：0-39

**Q: templates中的{变量}是什么？**
A: 这些是实体占位符，会被实际识别到的实体替换，如{person}、{location}等。

**Q: keyword_only有什么作用？**
A: 设置为true时，响应不会进行代词替换，保持原样输出。

**Q: 如何测试脚本效果？**
A: 修改配置文件指向你的脚本文件，然后运行Alice进行对话测试。

现在你已经掌握了基本的脚本编写技能！快去创建属于你自己的智能对话脚本吧！