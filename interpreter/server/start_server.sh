#!/bin/bash

# 确保在server目录下执行
cd "$(dirname "$0")"

# 创建日志目录
mkdir -p logs

# 获取当前日期
DATE=$(date +%Y%m%d)

# 停止已存在的服务器进程
pkill -f "python -m interpreter.server.cli" || true

# 等待进程完全停止
sleep 1

# 启动服务器
if [ "$1" == "--debug" ]; then
    # Debug模式：前台运行，输出到控制台
    PYTHONPATH=../.. python -m interpreter.server.cli --debug --log-level DEBUG
else
    # 生产模式：后台运行，输出到日志文件
    PYTHONPATH=../.. python -m interpreter.server.cli \
        --log-level INFO \
        > logs/server_${DATE}.log 2>&1 &
    
    # 输出进程ID
    echo "Server started with PID $!"
fi 