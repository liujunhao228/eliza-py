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
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import uvicorn

# 导入配置
from turing_test.backend.config import settings

# 导入 FastAPI 应用
from turing_test.backend.main import app


if __name__ == "__main__":
    print(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📊 监听地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"🔧 Debug 模式: {settings.DEBUG}")
    print()

    uvicorn.run(
        "turing_test.backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
