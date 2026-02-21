FROM python:3.11-slim

WORKDIR /app

# 复制依赖文件
COPY turing-test/requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY turing-test/ ./

# 创建工作目录
WORKDIR /app/backend

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
