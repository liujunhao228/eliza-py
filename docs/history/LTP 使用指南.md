# LTP 依存句法分析使用指南

## 📋 概述

Alice 聊天机器人现已集成 **LTP (Language Technology Platform)** 依存句法分析模型，实现更智能的对话理解和响应生成。

### 主要功能

- 🎯 **句法结构分析**：提取句子主干（主谓宾）
- 🔄 **句法重组**：基于句法成分生成动态响应
- 📊 **依存关系识别**：识别修饰、并列等语法关系
- 💡 **句法触发规则**：根据句法结构触发特定响应

## 🚀 快速开始

### 1. 安装 LTP

```bash
# 安装 LTP（完整版，用于深度句法分析）
pip install ltp==4.2.10
```

**注意**：
- LTP 首次加载时需要下载模型（约 100MB）
- 首次启动时间较长（约 30 秒）
- 未安装 LTP 时自动降级到简化模式

### 2. 启用 LTP

```python
from alice.core import AliceBot

# 启用 LTP 句法分析
alice = AliceBot(enable_ltp=True)

# 普通模式（不使用 LTP）
alice_normal = AliceBot(enable_ltp=False)
```

### 3. 使用示例

```python
# 对话示例
response = alice.respond("我觉得今天很开心")
print(response)
# 输出：为什么你觉得今天很开心呢？

# 获取句法分析结果
from alice.utils.ltp_parser import LTPParser

parser = LTPParser()
structure = parser.parse("我和朋友去了餐厅")

print(f"主语：{structure.subject}")    # 我
print(f"谓语：{structure.predicate}")  # 去
print(f"宾语：{object}")              # 餐厅
```

## 📚 API 参考

### LTPParser 类

#### 初始化

```python
parser = LTPParser(model_path=None)
```

- `model_path`: LTP 模型路径（可选，默认自动下载）

#### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `parse(text)` | 完整句法分析 | `SentenceStructure` 对象 |
| `get_main_structure(text)` | 获取主干结构 | `{'subject': '', 'predicate': '', 'object': ''}` |
| `get_modifiers(text)` | 获取修饰语 | `{'att': [], 'adv': []}` |
| `get_dependency_tree(text)` | 获取依存树 | 依存关系字典 |
| `extract_clause_components(text)` | 提取从句成分 | 从句列表 |
| `analyze_sentiment_structure(text)` | 分析情感结构 | 情感成分字典 |

#### 使用示例

```python
from alice.utils.ltp_parser import LTPParser

parser = LTPParser()

# 完整分析
structure = parser.parse("我觉得今天很开心")
print(f"词语：{structure.words}")
print(f"词性：{structure.poses}")
print(f"主谓宾：{structure.subject} | {structure.predicate} | {structure.object}")

# 依存关系
for dep in structure.deps:
    print(f"{dep.word}({dep.dep}) --> {structure.words[dep.head-1]}")
```

### SyntaxBasedReassemblyEngine 类

基于句法的重组引擎，支持更智能的响应生成。

```python
from alice.utils.ltp_parser import SyntaxBasedReassemblyEngine

engine = SyntaxBasedReassemblyEngine(parser)

# 基于句法重组
response = engine.reassemble_with_syntax(
    "我觉得很累",
    "为什么{SUBJ}{PRED}{OBJ}？"
)
# 输出：为什么你觉得很累？

# 生成问句
question = engine.generate_syntax_question(
    "我想学习编程",
    question_type='why'  # 'why', 'what', 'how'
)
# 输出：为什么你想学习编程呢？

# 提取焦点
focus = engine.extract_focus_point("我昨天去了新餐厅")
# 输出：餐厅
```

### 便捷函数

```python
from alice.utils.ltp_parser import parse_sentence, get_main_components, analyze_with_syntax

# 快速分析句子
structure = parse_sentence("我喜欢编程")

# 获取主干
components = get_main_components("他希望改变自己")
# 返回：{'subject': '他', 'predicate': '希望', 'object': '改变'}

# 完整分析
result = analyze_with_syntax("今天天气很好")
```

## 🔧 配置说明

### 脚本配置（支持句法触发）

在脚本配置文件中添加 `syntax_triggers`：

```json
{
  "scripts": {
    "emotional_expression": {
      "id": "emotional_expression",
      "patterns": [".*(难过 | 开心 | 生气).*"],
      "responses": ["..."],
      "priority": 6,
      "reassembly_rules": [
        "你为什么感到{1}呢？",
        "{SUBJ}为什么{PRED}{OBJ}？"
      ],
      "syntax_triggers": {
        "rules": [
          {
            "predicate_emotion": ["觉得", "感到", "感觉"],
            "object_emotion": ["开心", "难过", "生气"],
            "response_templates": [
              "为什么{SUBJ}{PRED}{OBJ}？",
              "{SUBJ}是从什么时候开始{PRED}{OBJ}的？"
            ]
          }
        ]
      }
    }
  }
}
```

### 句法触发规则类型

| 触发条件 | 说明 | 示例 |
|---------|------|------|
| `predicate` | 谓语动词匹配 | `["去", "做", "看"]` |
| `predicate_emotion` | 情感谓语 | `["觉得", "感到", "感觉"]` |
| `object_emotion` | 情感宾语 | `["开心", "难过", "生气"]` |
| `subject_person` | 主语是人称 | `true` |
| `adverbial_degree` | 程度副词 | `["很", "非常", "特别"]` |

### 重组规则占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{1}`, `{2}`, `{3}` | 传统分解组件 | "后来{1}发生了什么？" |
| `{SUBJ}` | 主语 | "{SUBJ}为什么{PRED}？" |
| `{PRED}` | 谓语 | "为什么{SUBJ}{PRED}{OBJ}？" |
| `{OBJ}` | 宾语 | "{SUBJ}对{OBJ}的感受？" |
| `{ATT}` | 定语 | "{SUBJ}的{ATT}{OBJ}" |
| `{ADV}` | 状语 | "{SUBJ}{ADV}{PRED}" |

## 📊 依存关系类型

LTP 支持的主要依存关系：

### 核心关系

| 关系 | 说明 | 示例 |
|------|------|------|
| `SBV` | 主谓关系 | 我 (SBV) → 觉得 |
| `VOB` | 动宾关系 | 喜欢 (VOB) → 编程 |
| `IOB` | 间宾关系 | 给 (IOB) → 他 |
| `DBL` | 双宾关系 | 送 (DBL) → 礼物 |
| `COO` | 并列关系 | 和 (COO) → 朋友 |

### 修饰关系

| 关系 | 说明 | 示例 |
|------|------|------|
| `ATT` | 定中关系 | 美丽的 (ATT) → 花 |
| `ADV` | 状中结构 | 轻轻地 (ADV) → 走 |
| `CMP` | 动补结构 | 跑 (CMP) → 快 |
| `POB` | 介宾关系 | 在 (POB) → 家里 |
| `HED` | 核心关系 | 句子核心 |

## 🧪 测试

运行测试验证 LTP 功能：

```bash
# 运行 LTP 模块测试
python tests/test_ltp_parser.py

# 运行完整测试套件
pytest tests/
```

## 🔍 调试模式

### 查看句法分析详情

```python
from alice.utils.ltp_parser import LTPParser

parser = LTPParser()
sentence = "我觉得今天很开心"

# 获取完整依存树
tree = parser.get_dependency_tree(sentence)

print(f"词语：{tree['words']}")
for dep in tree['dependencies']:
    print(f"{dep['word']}({dep['pos']}) --[{dep['dep']}]--> {dep['head_word']}")
```

### 性能监控

```python
import time
from alice.core import AliceBot

alice = AliceBot(enable_ltp=True)

start = time.time()
response = alice.respond("测试消息")
duration = time.time() - start

print(f"响应时间：{duration*1000:.2f}ms")
print(f"回复：{response}")
```

## ⚙️ 高级配置

### 自定义模型路径

```python
from alice.utils.ltp_parser import LTPParser

# 使用本地模型（避免每次下载）
parser = LTPParser(model_path="/path/to/ltp/model")
```

### 降级处理

未安装 LTP 时自动降级：

```python
# 无需额外配置，自动降级到简化模式
alice = AliceBot(enable_ltp=True)  # 未安装 LTP 时使用简化分析
```

### 性能优化

```python
# 预加载模型（避免首次请求延迟）
from alice.utils.ltp_parser import LTPParser

# 启动时预加载
parser = LTPParser()

# 后续使用同一实例
structure1 = parser.parse("句子 1")
structure2 = parser.parse("句子 2")
```

## 📝 最佳实践

### 1. 选择合适的模式

| 场景 | 推荐模式 | 理由 |
|------|---------|------|
| 开发测试 | `enable_ltp=True` | 完整句法分析功能 |
| 生产环境（性能优先） | `enable_ltp=False` | 响应更快，资源占用少 |
| 深度对话分析 | `enable_ltp=True` | 更精准的句法理解 |

### 2. 脚本设计建议

```json
{
  "scripts": {
    "example": {
      "patterns": [".*"],
      "reassembly_rules": [
        "传统组件引用：{1}",
        "句法成分引用：{SUBJ}{PRED}{OBJ}",
        "混合使用：{1}让{SUBJ}{PRED}"
      ]
    }
  }
}
```

### 3. 错误处理

```python
try:
    alice = AliceBot(enable_ltp=True)
    response = alice.respond("测试")
except Exception as e:
    print(f"LTP 错误：{e}")
    # 自动降级到普通模式
    alice = AliceBot(enable_ltp=False)
```

## 🔮 未来功能

- [ ] 更多句法触发规则类型
- [ ] 从句分析增强
- [ ] 语义角色标注（SRL）
- [ ] 事件抽取
- [ ] 对话状态追踪

## 📚 参考资料

- [LTP 官方文档](https://ltp.ai/docs/)
- [依存句法分析原理](https://www.aclweb.org/anthology/C14-1008.pdf)
- [Eliza 重组规则设计](./重组规则使用指南.md)

## ⚠️ 注意事项

1. **性能考虑**：LTP 首次加载较慢（约 30 秒），后续使用正常
2. **内存占用**：LTP 模型约占用 200-500MB 内存
3. **网络要求**：首次使用需要下载模型（约 100MB）
4. **降级方案**：未安装 LTP 时自动使用简化分析器

---

**版本**: 2.0  
**更新日期**: 2026 年 2 月  
**兼容性**: Python 3.7+, LTP 4.2.10+
