import os

# 获取后端目录
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

# 数据库配置
DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_DIR, 'data', 'turing.db')}"

# 邀请码配置
INVITE_CODE_LENGTH = 6

# 匹配配置
MATCH_TIMEOUT = 30  # 秒，等待真人超时后匹配 AI

# AI 配置
AI_BOT_NAME = "小图"
AI_TYPING_DELAY_BASE = 1.0  # 基础延迟（秒）
AI_TYPING_DELAY_PER_CHAR = 0.05  # 每字符额外延迟（秒）

# 会话配置
MIN_CHAT_TURNS = 3  # 最少对话轮数才能结束

# 服务器配置
HOST = "0.0.0.0"
PORT = 8000
