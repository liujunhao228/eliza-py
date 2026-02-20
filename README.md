# Alice - 好奇的朋友

一个基于 ELIZA 原理的轻量化中文聊天机器人，扮演一个永远对你充满好奇的朋友角色。

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ 特点

- 🎯 **轻量化设计**: 仅需 jieba 分词，无需大型 NLP 模型
- 🚀 **快速响应**: 平均响应时间 <50ms
- 💬 **好奇心驱动**: 主动询问"为什么"、"然后呢"引导对话
- 🔧 **易于定制**: YAML 脚本配置，灵活调整行为
- 📦 **开箱即用**: 安装依赖即可运行
- 🆕 **NLP 工厂模式**: 统一管理分词、实体识别、情感分析引擎

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/eliza-py.git
cd eliza-py

# 安装依赖
pip install -r requirements.txt

# （可选）安装 LTP 进行深度句法分析
pip install ltp>=4.2.10
```

### 运行

```bash
# 启动 Alice
python main.py

# 或使用 Python API
python -c "from alice.alice_v2 import AliceBot; alice = AliceBot(); print(alice.respond('你好'))"
```

### 示例对话

```
Alice: 你好！我是 Alice。有什么想聊的吗？
你：我昨天和朋友去了一家新餐厅
Alice: 你提到的这个朋友，ta 是个怎样的人呀？
你：是我很好的同事，我们认识很久了
Alice: 听起来你们关系很好，能多说说你们是怎么认识的吗？
你：后来我们一起去了餐厅
Alice: 那家餐厅给你留下了什么印象呢？
你：菜品很美味，环境也很好
Alice: 哇，那一定是很愉快的经历吧？
你：再见
Alice: 再见！很高兴和你聊天！
```

## 📖 文档

| 文档 | 描述 |
|------|------|
| [NLP 模块文档](docs/NLP 模块文档.md) | NLP 工厂和引擎使用指南 |
| [项目模块文档](docs/项目模块文档.md) | 整体架构和模块说明 |
| [情感分析指南](docs/情感分析模块使用指南.md) | 情感分析功能使用教程 |
| [开发者指南](docs/开发者指南.md) | 开发环境和贡献指南 |
| [编码规范](docs/编码规范.md) | 代码规范和最佳实践 |

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

编辑 `alice/scripts/emotion_responses.yaml`：

```yaml
- intent: sentiment_positive
  priority: 85
  condition:
    sentiment_label: "positive"
  templates:
    - "你的自定义响应 1"
    - "你的自定义响应 2"
```

### 编程使用

```python
from alice.alice_v2 import AliceBot

alice = AliceBot()
response = alice.respond("你好")
print(response)
```

## 🚀 性能基准

| 引擎 | 响应时间 | 内存占用 |
|-----|---------|---------|
| JiebaEngine (分词) | <10ms | ~20MB |
| SentimentEngine (情感) | <5ms | ~10MB |
| NerEngine (实体) | <10ms | ~10MB |
| LtpEngine (句法，可选) | <100ms | ~200MB |
| 完整对话流程 | <50ms | ~50MB |

## 🛠️ 开发

### 运行测试

```bash
pip install pytest pytest-cov
pytest tests/

# NLP 模块测试
python test_nlp_refactor.py
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
│   ├── alice_v2.py              # 主入口类
│   ├── core/                    # 核心对话引擎
│   ├── nlp/                     # NLP 模块（v3.0 重构）
│   │   ├── engines/             # NLP 引擎
│   │   └── dictionaries/        # 词典管理
│   ├── processors/              # 处理器
│   ├── plugins/                 # 插件系统
│   ├── scripts/                 # YAML 脚本
│   └── utils/                   # 工具函数
├── docs/                        # 项目文档
├── requirements.txt             # 依赖配置
└── README.md                    # 项目说明
```

## 🎓 技术原理

Alice 基于 ELIZA 的经典"镜像反射"原理：

1. **模式匹配**: 使用 YAML 脚本识别用户意图
2. **代词转换**: 将"我"转换为"你"进行反问
3. **情感分析**: 基于词典的情感极性判断
4. **实体识别**: 识别人物、地点、时间等实体
5. **上下文记忆**: 保持最近对话的上下文信息

与原始 ELIZA 的区别：
- 支持中文分词（jieba）
- 基于 YAML 的脚本引擎
- 情感分析和实体识别
- 基于优先级的脚本调度

## 📚 参考资料

- Weizenbaum, J. (1966). [ELIZA—a computer program for the study of natural language communication between man and machine](https://dl.acm.org/doi/10.1145/365153.365168). Communications of the ACM.

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

Alice 是一个基于规则的聊天机器人，不具备心理咨询或医疗建议的功能。如有心理健康问题，请咨询专业人士。
