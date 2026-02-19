# Alice 融合 Eliza 重组规则设计方案

## 📋 文档概述

**版本**: 1.0  
**更新日期**: 2026 年 2 月 19 日  
**目的**: 将 Eliza 的重组规则（Reassembly Rules）机制融合至 Alice，同时保持 Eliza 原有代码不变

---

## 🎯 设计目标

### 核心目标
1. **融合 Eliza 重组规则**: 将 Eliza 的动态响应生成机制集成到 Alice
2. **保持代码独立**: 不修改 Eliza 原有代码（`eliza.py`、`utils/`、`scripts/`）
3. **移除记忆堆栈**: 采用轻量级上下文追踪替代
4. **保持 Alice 定位**: 维持"好奇朋友"角色，不影响中文对话体验

### 设计原则
| 原则 | 说明 |
|------|------|
| **代码隔离** | Eliza 和 Alice 各自独立，互不影响 |
| **渐进增强** | 在现有 Alice 架构上增强，非颠覆式重写 |
| **配置驱动** | 重组规则通过脚本配置，非硬编码 |
| **中文优化** | 针对中文对话习惯调整，避免机械感 |

---

## 📊 Eliza 重组规则分析

### 1. Weizenbaum 表示法

Eliza 使用特殊的分解规则表示法：

```
(0 YOU 0)        → 匹配包含 "you" 的句子
(0 I AM 0)       → 匹配包含 "I am" 的句子  
(0 YOUR @FAMILY 0 YOU) → 使用语义标签 @FAMILY
```

**符号含义**:
- `0` = 任意数量单词（通配符）
- 正整数 = 特定数量单词
- `@TAG` = 语义标签（如 `@FAMILY`、`@SAD`）

### 2. 重组规则机制

重组规则使用 1-索引引用分解组件：

```json
{
  "decomp": "(0 YOU ARE 0)",
  "reassembly": [
    "Is it because you are 4 that you came to me?",
    "How long have you been 4 ?",
    "Do you believe it is normal to be 4 ?"
  ]
}
```

**示例**:
```
用户输入: "I am sad"
分解规则: (0 I AM 0)
分解结果: ["", "sad"]  (组件 1=空，组件 2="sad")
重组规则: "Why are you 2 ?"
输出: "Why are you sad ?"
```

### 3. 记忆堆栈机制

特定关键字（如 `your`）触发记忆：
```
用户: "Your advice is helpful"
→ 触发 "^" 规则
→ 生成记忆响应推入堆栈
→ 后续无匹配时弹出："Earlier you mentioned your advice"
```

---

## 🏗️ Alice 融合方案

### 1. 架构调整

```
┌─────────────────────────────────────────────────────────┐
│                      Alice Core                          │
├─────────────────────────────────────────────────────────┤
│  预处理 → 语义分析 → 脚本匹配 → 重组引擎 → 响应生成    │
│                              ↑                          │
│                         新增重组引擎                     │
└─────────────────────────────────────────────────────────┘
```

### 2. 模块设计

#### 2.1 新增：ReassemblyEngine 类

```python
class ReassemblyEngine:
    """重组引擎 - 支持组件引用语法"""
    
    def __init__(self):
        # 代词映射表（可配置）
        self.pronoun_mapping = {
            '我': '你', '我的': '你的', '我们': '你们',
            # ... 更多映射
        }
    
    def reassemble(self, components: List[str], 
                   reassembly_rule: str) -> str:
        """
        根据重组规则组装响应
        
        参数:
            components: 分解组件列表，如 ["", "难过"]
            reassembly_rule: 重组规则，如 "你为什么觉得 2 呢？"
        
        返回:
            组装后的响应，如 "你为什么觉得难过呢？"
        """
        response = reassembly_rule
        for i, comp in enumerate(components, 1):
            # 引用语法：{1}, {2}, {3}...
            placeholder = f'{{{i}}}'
            response = response.replace(placeholder, comp.strip())
        return response
```

#### 2.2 修改：CuriosityScriptEngine

**脚本格式扩展**:
```json
{
  "emotional_expression": {
    "patterns": [".*(我觉得|我感到).*"],
    "responses": [
      "你为什么会有这样的感受呢？"
    ],
    "priority": 5,
    "reassembly_rules": [
      "你为什么觉得{2}呢？",
      "是什么让你感到{2}？",
      "这种{2}的感觉是从什么时候开始的？"
    ]
  }
}
```

**匹配逻辑调整**:
```python
def match_script(self, text: str, semantic_info: Dict) -> Optional[str]:
    for script_name, script_config in self.scripts.items():
        for pattern in script_config.get('patterns', []):
            match = re.search(pattern, text)
            if match:
                # 优先使用重组规则
                if 'reassembly_rules' in script_config:
                    components = match.groups()
                    rule = random.choice(script_config['reassembly_rules'])
                    return self.reassembly_engine.reassemble(components, rule)
                
                # 回退到普通 responses
                return random.choice(script_config.get('responses', []))
    return None
```

#### 2.3 增强：ReflectionEngine

**原实现**（保留）:
```python
self.transformation_rules = [
    (r'我觉得 (.*)', r'你为什么觉得\1 呢？'),
]
```

**增强后**（支持配置）:
```python
def load_reflection_rules(self, rules_file: str):
    """从配置文件加载反射规则"""
    with open(rules_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
        self.pronoun_mapping = config.get('pronoun_mapping', {})
        self.transformation_rules = [
            (r, p) for r, p in config.get('rules', [])
        ]
```

### 3. 记忆堆栈替代方案

#### ❌ 不采用的原因

| 原因 | 说明 |
|------|------|
| **体验突兀** | 中文对话中突然弹出旧话题显得机械 |
| **复杂度增加** | 需维护堆栈状态、判断弹出时机 |
| **角色冲突** | 与"好奇朋友"定位不符，更像治疗师 |
| **现代习惯** | 用户期望自然流畅的对话 |

#### ✅ 替代方案：轻量级上下文追踪

```python
@dataclass
class DialogueContext:
    """对话上下文"""
    entities: deque  # 最近提及的实体（最多 3 个）
    last_intent: str = ""
    conversation_turns: int = 0
    
    def add_entity(self, entity: str, entity_type: str = "unknown"):
        """添加实体到上下文"""
        if len(self.entities) >= 3:
            self.entities.popleft()
        self.entities.append((entity, entity_type))
    
    def get_recent_entities(self) -> List[Tuple[str, str]]:
        """获取最近的实体"""
        return list(self.entities)
```

**使用示例**:
```
用户: "我和朋友吵架了"
→ 提取实体：("朋友", "person")
→ 存入上下文

用户: "他很生气"
→ Alice 可自然引用："你刚才提到的朋友，他为什么生气呢？"
```

---

## 📁 文件结构

### 新增文件

```
alice/
├── core.py                          # 核心（修改）
├── scripts/
│   ├── curiosity_scripts.json       # 脚本（扩展格式）
│   └── reflection_rules.json        # 反射规则配置（新增）
└── utils/
    └── reassembly.py                # 重组引擎（新增）
```

### reflection_rules.json 示例

```json
{
  "pronoun_mapping": {
    "我": "你",
    "我的": "你的",
    "我们": "你们",
    "我自己": "你自己",
    "我妈": "你妈",
    "我爸": "你爸",
    "我朋友": "你朋友",
    "我同事": "你同事"
  },
  "transformation_rules": [
    ["我觉得 (.*)", "你为什么觉得{1}呢？"],
    ["我不 (.*)", "为什么不{1}呢？"],
    ["我想 (.*)", "为什么想{1}呢？"],
    ["我喜欢 (.*)", "你喜欢{1}什么地方？"],
    ["我讨厌 (.*)", "为什么讨厌{1}呢？"],
    ["我害怕 (.*)", "{1}让你感到害怕吗？"]
  ]
}
```

---

## 🔄 处理流程对比

### 原 Alice 流程

```
用户输入 → 预处理 → 语义分析 → 脚本匹配 → 响应生成
                                    ↓
                              直接返回 responses 中的响应
```

### 融合后流程

```
用户输入 → 预处理 → 语义分析 → 脚本匹配
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            有重组规则                        无重组规则
                    ↓                               ↓
            提取分解组件                    直接返回 responses
                    ↓
            应用重组规则
                    ↓
            生成动态响应
```

---

## 📊 脚本格式对比

### 原格式

```json
{
  "emotional_expression": {
    "patterns": [".*难过.*", ".*开心.*"],
    "responses": ["听起来你现在感受很复杂..."],
    "priority": 5
  }
}
```

### 扩展格式

```json
{
  "emotional_expression": {
    "patterns": [".*(感到 | 觉得).*?(难过 | 开心).*"],
    "responses": ["听起来你现在感受很复杂..."],
    "priority": 5,
    "reassembly_rules": [
      "你为什么感到{2}呢？",
      "是什么让你{2}？",
      "这种{2}的感觉持续多久了？"
    ],
    "enable_reassembly": true
  }
}
```

---

## 🎯 实现优先级

### Phase 1: 核心功能（1 周）
- [ ] 实现 `ReassemblyEngine` 类
- [ ] 扩展脚本格式支持 `reassembly_rules`
- [ ] 更新 `CuriosityScriptEngine` 匹配逻辑

### Phase 2: 配置化（3 天）
- [ ] 创建 `reflection_rules.json`
- [ ] 支持从配置加载代词映射和转换规则
- [ ] 更新文档

### Phase 3: 优化（2 天）
- [ ] 响应去重机制
- [ ] 上下文实体追踪增强
- [ ] 性能测试

---

## 📈 预期效果

### 优势

| 优势 | 说明 |
|------|------|
| **动态响应** | 根据用户输入生成更个性化的响应 |
| **减少重复** | 重组规则 + 响应轮换，降低重复率 |
| **配置灵活** | 脚本配置即可调整行为 |
| **保持独立** | Eliza 代码完全不受影响 |

### 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 重组规则复杂度高 | 提供简化语法，仅支持 {1}, {2} 等基础引用 |
| 中文分词误差 | 使用 jieba 分词 + 规则校验 |
| 响应不自然 | 人工审核脚本，确保口语化 |

---

## 🔒 代码隔离保证

### Eliza 代码（不变）

```
eliza.py              ← 不变
utils/
  ├── rules.py        ← 不变
  ├── response.py     ← 不变
  ├── rank.py         ← 不变
  └── startup.py      ← 不变
scripts/
  ├── doctor.json     ← 不变
  └── general.json    ← 不变
```

### Alice 代码（修改/新增）

```
alice/
  ├── core.py         ← 修改：集成重组引擎
  ├── scripts/
  │   └── *.json      ← 修改：扩展格式
  └── utils/
      └── reassembly.py ← 新增
```

---

## 📝 总结

本设计方案在保持 Eliza 原有代码不变的前提下，将重组规则机制融合至 Alice：

1. **新增 `ReassemblyEngine`**: 支持组件引用语法生成动态响应
2. **扩展脚本格式**: 添加 `reassembly_rules` 字段
3. **移除记忆堆栈**: 采用轻量级上下文实体追踪
4. **配置驱动**: 代词映射和转换规则可配置

此方案保持了 Alice 的"好奇朋友"定位，同时增强了响应生成的灵活性和个性化程度。

---

## 附录：重组规则语法参考

### 基础语法

| 语法 | 含义 | 示例 |
|------|------|------|
| `{1}` | 引用第 1 个分解组件 | "你为什么{1}" |
| `{2}` | 引用第 2 个分解组件 | "是什么让你{2}" |
| `{n}` | 引用第 n 个分解组件 | 依此类推 |

### 示例

```
模式：".*(感到 | 觉得).*?(难过 | 开心).*"
用户输入："我感到很难过"
分解组件：["感到", "难过"]
重组规则："你为什么{1}{2}呢？"
输出："你为什么感到难过呢？"
```
