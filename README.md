# Alice - 好奇的朋友

一个基于 ELIZA 原理的轻量化中文聊天机器人，扮演一个永远对你充满好奇的朋友角色。

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ 特点

- 🎯 **轻量化设计**: 仅需 jieba 分词，无需大型 NLP 模型
- 🚀 **快速响应**: 平均响应时间 <200ms
- 💬 **好奇心驱动**: 主动询问"为什么"、"然后呢"引导对话
- 🔧 **易于定制**: JSON 脚本配置，灵活调整行为
- 📦 **开箱即用**: 安装依赖即可运行

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/eliza-py.git
cd eliza-py

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
# 启动 Alice
python alice/core.py
```

### 示例对话

```
Alice: 你好！我是 Alice，你的好奇朋友。有什么想聊的吗？
你：我昨天去了一个新开的餐厅
Alice: 后来呢？发生了什么让你印象深刻的事吗？
你：那里的装修很有特色，服务员也很热情
Alice: 听起来很有意思，能详细说说吗？
你：菜品也很美味
Alice: 哇，那一定很有趣吧？继续说说看！
你：再见
Alice: 再见！很高兴和你聊天！
```

## 📖 文档

| 文档 | 描述 |
|------|------|
| [快速开始指南](docs/快速开始指南.md) | 5 分钟上手教程 |
| [程序设计方案](docs/程序设计方案.md) | 架构设计和技术实现 |
| [重组规则融合方案](docs/Alice 融合 Eliza 重组规则设计方案.md) | Eliza 重组规则集成设计 |
| [重组规则使用指南](docs/重组规则使用指南.md) | 重组规则配置和使用教程 |
| [详细实施计划](docs/详细实施计划.md) | 开发路线图和时间表 |

## 🎯 核心功能

### 1. 叙事延续
当用户分享经历时，Alice 会好奇地追问：
- "后来呢？发生了什么？"
- "那之后你做了什么？"

### 2. 人物关注
当用户提到他人时，Alice 会询问：
- "ta 是个怎样的人？"
- "你们关系怎么样？"

### 3. 情感回应
当用户表达情感时，Alice 会回应：
- "这种感受从哪来的？"
- "你希望如何改变？"

### 4. 自我反思
当用户表达观点时，Alice 会引导：
- "为什么会有这种想法？"
- "这个想法对你有什么影响？"

## 🔧 自定义配置

### 修改脚本

编辑 `alice/scripts/curiosity_scripts.json`：

```json
{
  "narrative_continuation": {
    "patterns": [".*去.*了.*"],
    "responses": [
      "你的自定义响应 1",
      "你的自定义响应 2"
    ],
    "priority": 5
  }
}
```

### 编程使用

```python
from alice.core import AliceBot

alice = AliceBot()
response = alice.respond("你好")
print(response)
```

## 📊 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 响应时间 | ≤2 秒 | ~50-200ms |
| 内存占用 | <50MB | ~20MB |
| 对话自然度 | ≥70% | 待测试 |

## 🛠️ 开发

### 运行测试

```bash
pip install pytest pytest-cov
pytest tests/
```

### 代码格式化

```bash
black alice/
flake8 alice/
```

## 📝 项目结构

```
eliza-py/
├── alice/
│   ├── core.py                    # 核心对话引擎
│   └── scripts/
│       └── curiosity_scripts.json # 好奇心脚本
├── docs/                          # 项目文档
├── scripts/                       # ELIZA 原始脚本
├── utils/                         # 工具函数
├── requirements.txt               # 依赖配置
└── README.md                      # 项目说明
```

## 🎓 技术原理

Alice 基于 ELIZA 的经典"镜像反射"原理：

1. **模式匹配**: 使用正则表达式识别用户意图
2. **代词转换**: 将"我"转换为"你"进行反问
3. **脚本响应**: 根据匹配的意图选择响应模板
4. **上下文记忆**: 保持最近 3 轮的对话实体

与原始 ELIZA 的区别：
- 支持中文分词（jieba）
- 简化的情感分析
- 基于优先级的脚本调度
- 响应去重机制

## 📚 参考资料

- Weizenbaum, J. (1966). [ELIZA—a computer program for the study of natural language communication between man and machine](https://dl.acm.org/doi/10.1145/365153.365168). Communications of the ACM.
- [ELIZA 原始实现](https://github.com/rdimaio/eliza-py)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

Alice 是一个基于规则的聊天机器人，不具备心理咨询或医疗建议的功能。如有心理健康问题，请咨询专业人士。
