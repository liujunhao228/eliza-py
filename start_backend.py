"""
启动后端服务

运行 FastAPI 后端服务。

使用方法:
    python start_backend.py

或使用 uvicorn 直接运行:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

import uvicorn

# 导入配置
from config import get_config_manager

config_mgr = get_config_manager()

# 向后兼容的配置常量
APP_NAME = "Turing Test Backend"
APP_VERSION = "0.1.0"
HOST = config_mgr.get('turing.server.host', '0.0.0.0')
PORT = config_mgr.get('turing.server.port', 8000)
DEBUG = config_mgr.get('debug', False)
LOG_LEVEL = config_mgr.get('log_level', 'INFO')

# 导入 FastAPI 应用
from turing_test.backend.main import app


if __name__ == "__main__":
    print(f"🚀 启动 {APP_NAME} v{APP_VERSION}")
    print(f"📊 监听地址：http://{HOST}:{PORT}")
    print(f"📚 API 文档：http://{HOST}:{PORT}/docs")
    print(f"🔧 Debug 模式：{DEBUG}")
    print()

    uvicorn.run(
        "turing_test.backend.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower(),
    )
