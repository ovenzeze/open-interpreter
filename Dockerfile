###########################################################################################
# This Dockerfile runs an LMC-compatible websocket server at / on port 8000.              #
# To learn more about LMC, visit https://docs.openinterpreter.com/protocols/lmc-messages. #
###########################################################################################

FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建非root用户
RUN useradd -m -r -s /bin/bash interpreter
RUN chown -R interpreter:interpreter /app

# 切换到非root用户
USER interpreter

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    MAX_SESSIONS=1000 \
    MAX_REQUESTS_PER_MINUTE=60 \
    MAX_MEMORY_USAGE=1073741824

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "-m", "interpreter.server.cli", "--host", "0.0.0.0", "--port", "5001", "--log-level", "INFO"]