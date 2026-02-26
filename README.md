# Alice & Turing Test - 双重用途研究平台

一个基于 ELIZA 原理的轻量化中文聊天机器人 + 图灵测试社会实验平台。

## 项目组成

### 1. Alice - 好奇的朋友

基于 ELIZA 原理的轻量化中文聊天机器人，扮演一个永远对你充满好奇的朋友角色。

### 2. Turing Test - 图灵测试社会实验

基于积分激励机制的博弈实验平台，研究"基于积分激励的人机辨识博弈中人类行为拟态"。

---

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ 特点

- 🎯 **轻量化设计**: 仅需 jieba 分词，无需大型 NLP 模型
- 🚀 **快速响应**: 平均响应时间 <50ms
- 💬 **好奇心驱动**: 主动询问"为什么"、"然后呢"引导对话
- 🔧 **易于定制**: YAML 脚本配置，灵活调整行为
- 📦 **开箱即用**: 安装依赖即可运行
- 🆕 **NLP 工厂模式**: 统一管理分词、实体识别引擎
- 🤖 **Bot 池架构**: 共享 NLP 服务，支持多用户并发对话

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
# 启动 Alice（命令行模式）
python main.py

# 或使用 Python API
python -c "from alice.alice_v2 import AliceBot; alice = AliceBot(); print(alice.respond('你好'))"

# 启动 Turing Test 后端服务
python start_backend.py
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
| [编码规范](docs/编码规范.md) | 异常处理、优雅降级、代码风格 |
| [配置重构说明](docs/CONFIG_REFACTORING.md) | 统一配置系统使用指南 |
| [数据结构文档](DATA_STRUCTURES.md) | 核心数据模型和数据库 Schema |
| [Bot 池实现](AI_BOT_POOL_IMPLEMENTATION.md) | 高并发 AI 对话架构说明 |
| [执行计划](EXECUTION_PLAN.md) | 项目进度和任务分解 |
| [重构报告](REFACTORING_REPORT.md) | 2026-02-26 模块化重构详细说明 |

## 🎯 核心功能

### Alice 对话功能

#### 1. 叙事延续
当用户分享经历时，Alice 会好奇地追问：
- "后来呢？发生了什么？"
- "那之后你做了什么？"

#### 2. 人物关注
当用户提到他人时，Alice 会询问：
- "ta 是个怎样的人？"
- "你们关系怎么样？"

#### 3. 自我反思
当用户表达观点时，Alice 会引导：
- "为什么会有这种想法？"
- "这个想法对你有什么影响？"

### Turing Test 博弈功能

#### 1. 积分系统
- 初始积分：100 分
- 场中判断：双倍乘数博弈
- 信心等级：低/中/高三档

#### 2. 元对话机制
- 提及"真人"、"AI"等关键词触发
- 高频元对话增加惩罚乘数
- 实时积分预测显示

#### 3. 钓鱼机器人
- 伪装成真人用户的 AI
- 威慑合谋行为
- 形成"暗黑森林"心理博弈

## 🔧 自定义配置

### 修改 Alice 脚本

编辑 `alice/scripts/emotion_responses.yaml`：

```yaml
- intent: greeting
  priority: 85
  condition:
    keywords: ["你好", "您好", "嗨"]
  templates:
    - "你的自定义响应 1"
    - "你的自定义响应 2"
```

### 修改全局配置

编辑 `config.yaml`：

```yaml
alice:
  enable_ltp: true
  max_input_length: 500

turing:
  server:
    port: 8000
  auth:
    invite_code_length: 6
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
| NerEngine (实体) | <10ms | ~10MB |
| LtpEngine (句法，可选) | <100ms | ~200MB |
| 完整对话流程 | <50ms | ~50MB |
| Bot 池并发 | >100 请求/秒 | 动态扩展 |

## 🛠️ 开发

### 运行测试

```bash
# Alice 模块测试
pytest tests/

# NLP 模块测试
python test_nlp_refactor.py

# 集成测试
python test_integration_full.py

# Bot 池测试
python test_bot_pool.py
```

### 代码格式化

```bash
black alice/
flake8 alice/
```

## 📝 项目结构

```
eliza-py/
├── alice/                          # Alice 聊天机器人核心
│   ├── alice_v2.py                 # 主入口类
│   ├── server.py                   # Web 服务器
│   ├── core/                       # 核心对话引擎
│   │   ├── dialogue_engine.py      # 对话主引擎
│   │   ├── context_manager.py      # 上下文管理
│   │   ├── intent_matcher.py       # 意图匹配器
│   │   └── response_generator.py   # 响应生成器
│   ├── scripting/                  # 脚本引擎（重构后）
│   │   ├── base.py                 # 基类定义
│   │   ├── context.py              # 脚本上下文
│   │   ├── matcher.py              # 统一匹配器
│   │   ├── config.py               # 配置加载
│   │   ├── yaml/                   # YAML 脚本引擎
│   │   │   ├── engine.py           # 引擎核心
│   │   │   ├── parser.py           # YAML 解析器
│   │   │   ├── condition_checker.py# 条件检查器
│   │   │   └── template_engine.py  # 模板引擎
│   │   └── lua/                    # Lua 脚本引擎
│   │       ├── engine.py           # Lua 引擎
│   │       ├── sandbox.py          # 沙箱隔离
│   │       └── compiled_script.py  # 编译脚本
│   ├── nlp/                        # NLP 模块
│   │   ├── engines/                # NLP 引擎（jieba/LTP）
│   │   └── dictionaries/           # 词典管理
│   ├── processors/                 # 文本处理器
│   ├── services/                   # 共享服务（重构后）
│   │   ├── shared_nlp_service.py   # 共享 NLP 服务
│   │   └── monitoring_service.py   # 监控服务
│   ├── cache/                      # 缓存管理
│   ├── utils/                      # 工具函数
│   └── bots/                       # Bot 实现
│       └── lightweight_alice_bot.py# 轻量级 Bot
│
├── turing_test/                    # Turing Test 平台
│   ├── backend/                    # 后端服务
│   │   ├── api/                    # REST API
│   │   ├── websocket/              # WebSocket 处理
│   │   ├── models/                 # 数据库模型
│   │   ├── schemas/                # API Schema
│   │   ├── services/               # 业务服务
│   │   └── bot_pool.py             # Bot 池管理器
│   └── frontend/                   # Vue 3 前端（开发中）
│       ├── src/
│       │   ├── api/                # API 封装
│       │   ├── components/         # 通用组件
│       │   ├── views/              # 页面组件
│       │   └── stores/             # 状态管理
│       └── dist/                   # 构建输出
│
├── config/                         # 统一配置模块
│   ├── __init__.py                 # 导出 settings
│   ├── types.py                    # 配置类型定义
│   └── loader.py                   # 配置加载器
│
├── tests/                          # 测试套件
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   └── scripting/                  # 脚本引擎测试
│
├── docs/                           # 项目文档
├── config.yaml                     # 主配置文件
├── requirements.txt                # 依赖配置
└── README.md                       # 项目说明
```

## 🎓 技术原理

### Alice 原理

Alice 基于 ELIZA 的经典"镜像反射"原理：

1. **模式匹配**: 使用 YAML 脚本识别用户意图
2. **代词转换**: 将"我"转换为"你"进行反问
3. **实体识别**: 识别人物、地点、时间等实体
4. **上下文记忆**: 保持最近对话的上下文信息

与原始 ELIZA 的区别：
- 支持中文分词（jieba）
- 基于 YAML 的脚本引擎
- 实体识别
- 基于优先级的脚本调度
- 共享 NLP 服务架构

### Turing Test 原理

图灵测试平台基于信号检测理论和演化博弈论：

1. **非对称收益**: 打破合作均衡，防止合谋刷分
2. **信心等级**: 测量用户元认知能力
3. **元对话机制**: 高风险高回报的博弈设计
4. **钓鱼机器人**: 威慑合谋行为，形成"暗黑森林"心理

### 技术栈

**后端**:
- Python 3.7+
- FastAPI (Turing Test 后端)
- Flask (Alice Web 界面)
- SQLAlchemy (ORM)
- jieba / LTP (NLP)
- PyYAML (脚本配置)
- lupa (可选，Lua 脚本支持)

**前端** (开发中):
- Vue 3 + TypeScript
- Vite (构建工具)
- Pinia (状态管理)
- Element Plus (UI)

**架构特性**:
- 共享 NLP 服务（单例模式）
- Bot 池管理（动态扩缩容）
- WebSocket 实时通信
- 统一配置系统
- 模块化脚本引擎（Lua/YAML 双引擎）
- 统一监控服务

### 模块化架构（2026-02-26 重构后）

**核心模块**:
- `alice.core`: 对话引擎、上下文管理、响应生成
- `alice.scripting`: 统一脚本引擎（Lua/YAML）
- `alice.services`: 共享服务层（NLP、监控）
- `alice.nlp`: NLP 引擎抽象和实现

**重构成果**:
- 删除 1500+ 行重复代码
- 拆分超大文件（1055 行 → 417 行）
- 100% 脚本测试通过率
- 模块化设计提升可维护性

详见：[重构报告](REFACTORING_REPORT.md)

## 📊 项目进度

| 模块 | 进度 | 状态 |
|------|------|------|
| Alice 核心对话 | 100% | ✅ 已完成 |
| NLP 引擎 | 100% | ✅ 已完成 |
| Bot 池架构 | 100% | ✅ 已完成 |
| Turing 后端 API | 95% | ✅ 基本完成 |
| Turing 前端 | 60% | 🟡 开发中 |
| 集成测试 | 90% | ✅ 基本完成 |

## 📚 参考资料

- Weizenbaum, J. (1966). [ELIZA—a computer program for the study of natural language communication between man and machine](https://dl.acm.org/doi/10.1145/365153.365168). Communications of the ACM.

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

Alice 是一个基于规则的聊天机器人，不具备心理咨询或医疗建议的功能。如有心理健康问题，请咨询专业人士。
