# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个双重用途研究平台，包含两个主要组件：
1. **Alice** - 基于 ELIZA 原理的中文聊天机器人
2. **Turing Test** - 图灵测试社会实验平台

核心架构采用共享 NLP 服务（单例模式）和 Bot 池管理，支持高并发场景。

## 常用命令

### Python 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 Alice 聊天机器人
python alice/alice_v2.py

# 启动 Turing Test 后端服务
python start_backend.py

# 运行测试
pytest tests/
python test_nlp_refactor.py
python test_integration_full.py

# 代码格式化
black alice/
flake8 alice/
```

### 前端开发

```bash
# 进入前端目录
cd turing_test/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 核心架构

### 1. 统一配置系统

- `config.yaml` - 主配置文件
- `config.alice.yaml` - Alice 配置
- `config.turing.yaml` - Turing Test 配置
- `config/` 目录包含配置加载器、类型定义和管理器

配置支持环境变量覆盖和动态热重载。

### 2. NLP 工厂模式

- `alice/nlp/engines/` - NLP 引擎实现
  - `JiebaEngine` - 中文分词（必需，<10ms）
  - `LtpEngine` - 深度句法分析（可选，<100ms，需额外安装）
- 统一管理分词和实体识别，支持多引擎协作

### 3. Bot 池架构

- `turing_test/backend/bot_pool.py` - Bot 池管理器
- 支持动态扩缩容，共享 NLP 服务
- 通过 `config/bot_registry.py` 注册和管理 bot 类型

### 4. 双层通信架构

**Alice 层**：
- 命令行对话
- 基于 YAML 脚本的意图匹配
- 实体识别和上下文记忆

**Turing Test 层**：
- FastAPI + WebSocket 实时通信
- REST API 接口
- 积分博弈机制

### 5. 文件结构关键点

- `alice/scripts/` - YAML 对话脚本，支持优先级和条件匹配
- `alice/core/` - 对话引擎，处理意图匹配和响应生成
- `turing_test/backend/services/` - 业务逻辑服务层
- `turing_test/backend/websocket/` - 实时通信处理
- `config/validator.py` - 配置验证器

## 开发要点

### 1. 配置修改

修改配置后无需重启服务，系统支持热重载。新增配置项需要在 `config/types.py` 中定义类型。

### 2. 对话脚本扩展

在 `alice/scripts/` 下添加新的 YAML 文件，格式：
```yaml
- intent: custom_intent
  priority: 80
  condition:
    keywords: ["关键词1", "关键词2"]
  templates:
    - "响应模板1"
    - "响应模板2"
```

### 3. Bot 添加

新 bot 需要在 `config/bot_registry.py` 中注册，并实现相应的接口。

### 4. 数据库

SQLite 数据库位于 `data/turing.db`，使用 SQLAlchemy ORM 管理。

### 5. 性能优化

- NLP 服务使用单例模式避免重复加载
- Bot 汾支持并发请求处理
- 缓存机制减少重复计算

## 注意事项
全程使用中文，包括文档、注释、交流等等