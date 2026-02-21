# 图灵测试社交实验平台

一个用于研究性学习的图灵测试社交实验平台。用户可以随机匹配到真人或 AI 进行聊天，并通过对话判断对方身份。

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 初始化数据库和邀请码

```bash
cd backend
python init_db.py
```

这会创建数据库并生成 100 个邀请码，保存在 `invite_codes.txt` 文件中。

### 启动服务器

```bash
cd backend
python main.py
```

服务器将在 http://localhost:8000 启动。

### 访问网站

打开浏览器访问：http://localhost:8000

## 📁 项目结构

```
turing-test/
├── backend/
│   ├── main.py              # FastAPI 入口（含管理员 API）
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 模式
│   ├── auth.py              # 邀请码鉴权
│   ├── matcher.py           # 匹配引擎
│   ├── ai_bot.py            # Eliza AI 集成
│   ├── websocket.py         # WebSocket 管理
│   └── init_db.py           # 数据库初始化脚本
├── frontend/
│   ├── index.html           # 登录页
│   ├── lobby.html           # 大厅/匹配页
│   ├── chat.html            # 聊天页
│   ├── result.html          # 问卷 + 揭晓页
│   ├── profile.html         # 个人中心/战绩页
│   ├── admin.html           # 管理员后台
│   └── css/
│       └── style.css        # 样式
├── data/
│   └── turing.db            # SQLite 数据库
├── requirements.txt
└── README.md
```

## 🎮 使用流程

1. **登录**：使用邀请码登录，设置昵称
2. **匹配**：点击"开始匹配"进入匹配队列
3. **聊天**：与匹配到的对手（真人或 AI）聊天
4. **判断**：对话结束后提交你的判断
5. **揭晓**：查看真相和准确率

## 🔧 配置说明

编辑 `backend/config.py` 修改配置：

```python
# 数据库配置
DATABASE_URL = "sqlite:///./data/turing.db"

# 匹配超时（秒）
MATCH_TIMEOUT = 30

# AI 配置
AI_TYPING_DELAY_BASE = 1.0  # 基础延迟
AI_TYPING_DELAY_PER_CHAR = 0.05  # 每字符延迟

# 最少对话轮数
MIN_CHAT_TURNS = 3
```

## 📊 API 接口

### 用户接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/login` | POST | 验证邀请码 |
| `/api/register` | POST | 注册/登录 |
| `/api/user/{id}` | GET | 获取用户信息 |
| `/api/user/{id}/history` | GET | 获取用户对话历史 |
| `/api/match` | POST | 开始匹配 |
| `/api/match/ai` | POST | 直接匹配 AI |
| `/api/session/{id}` | GET | 获取会话信息 |
| `/api/session/{id}/end` | POST | 结束会话 |
| `/api/survey` | POST | 提交问卷 |
| `/api/stats/{user_id}` | GET | 获取用户统计 |
| `/ws/{user_id}` | WebSocket | 聊天连接 |

### 管理员接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/admin` | GET | 管理员后台页面 |
| `/api/admin/stats` | GET | 获取管理员统计数据 |
| `/api/admin/invite-codes` | GET | 获取邀请码统计 |
| `/api/admin/recent-sessions` | GET | 获取最近会话记录 |
| `/api/admin/export/{type}` | GET | 导出数据（messages/surveys/sessions/users） |
| `/api/admin/invite-codes/generate` | POST | 生成新邀请码 |
| `/api/admin/invite-codes/list` | GET | 获取邀请码列表 |

## 🔐 邀请码管理

生成新的邀请码：

```bash
cd backend
python init_db.py --count 50
```

查看邀请码使用统计：

```bash
cd backend
python init_db.py --stats
```

## 🐳 Docker 部署（可选）

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "main.py"]
```

构建并运行：

```bash
docker build -t turing-test .
docker run -p 8000:8000 -v $(pwd)/data:/app/data turing-test
```

## 📝 数据导出

数据库使用 SQLite 存储，可以直接用 SQLite 工具打开：

```bash
sqlite3 data/turing.db

# 导出对话记录
sqlite3 data/turing.db ".mode csv" ".output messages.csv" "SELECT * FROM messages;"

# 导出问卷结果
sqlite3 data/turing.db ".mode csv" ".output surveys.csv" "SELECT * FROM survey_results;"
```

## 🛠️ 开发说明

### 添加新的 AI 回复规则

编辑 `backend/ai_bot.py`，在 `patterns` 字典中添加关键词回复：

```python
self.patterns = {
    "你的关键词": ["回复 1", "回复 2", "回复 3"],
    # ...
}
```

### 修改匹配逻辑

编辑 `backend/matcher.py` 中的 `MatchEngine` 类。

## 📄 许可证

本项目用于学校研究性学习实验。

## 🙏 致谢

基于 Eliza 聊天机器人灵感开发的简化版 AI 对话系统。
