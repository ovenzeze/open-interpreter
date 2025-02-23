#!/bin/bash

# 设置基础目录
export INTERPRETER_BASE="$HOME/.interpreter"
export INTERPRETER_HOME="$INTERPRETER_BASE/.prod"
export PYTHONPATH="$INTERPRETER_HOME:$PYTHONPATH"

# 准备Python环境
function prepare_environment() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$script_dir/scripts/uv-prepare.sh" ]; then
        echo "Preparing Python environment using uv..."
        source "$script_dir/scripts/uv-prepare.sh"
    else
        echo "Error: uv-prepare.sh not found"
        exit 1
    fi
}

# 添加环境变量配置
function setup_env_vars() {
    # 设置服务端口
    export SERVER_PORT_PROD=5001
    export SERVER_PORT_DEV=5002
    # 确保当前目录在PYTHONPATH中
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    # 设置日志级别
    export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
}

# 创建必要的目录
mkdir -p "$INTERPRETER_BASE"/{logs/{prod,dev},run}

function ensure_prod_code() {
    if [ ! -d "$INTERPRETER_HOME" ]; then
        echo "Cloning production code..."
        git clone https://github.com/ovenzeze/open-interpreter.git "$INTERPRETER_HOME"
        cd "$INTERPRETER_HOME"
        git checkout main
    else
        echo "Updating production code..."
        cd "$INTERPRETER_HOME"
        git fetch origin
        git reset --hard origin/main
        git clean -fd
        git checkout main
        git pull origin main
    fi
}

# 添加服务信息打印函数
function print_service_info() {
    local service_type=$1
    local port
    if [ "$service_type" = "prod" ]; then
        port=$SERVER_PORT_PROD
    else
        port=$SERVER_PORT_DEV
    fi
    
    echo "========== Service Information =========="
    echo "Service Type: $service_type"
    echo "Python Path: $PYTHON_PATH"
    echo "Open Interpreter Path: $INTERPRETER_HOME"
    echo "Virtual Environment: $VIRTUAL_ENV"
    echo "Log Directory: $INTERPRETER_BASE/logs/$service_type"
    echo "Error Log: $INTERPRETER_BASE/logs/$service_type/err.log"
    echo "Output Log: $INTERPRETER_BASE/logs/$service_type/out.log"
    echo "Server Port: $port"
    echo "Log Level: $LOG_LEVEL"
    echo "========================================"
}

# 检查并安装Node.js依赖
function ensure_node_deps() {
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        if command -v yarn &> /dev/null; then
            yarn install
        else
            npm install
        fi
    fi
}

case "$1" in
    "start-dev")
        prepare_environment
        setup_env_vars
        print_service_info "dev"
        pm2 start ecosystem.config.js --only interpreter-dev
        ;;
    "start-prod")
        prepare_environment
        setup_env_vars
        ensure_prod_code
        print_service_info "prod"
        echo "Starting production server with Python: $PYTHON_PATH"
        pm2 start ecosystem.config.js --only interpreter-prod
        ;;
    "stop-dev")
        pm2 stop interpreter-dev
        ;;
    "stop-prod")
        pm2 stop interpreter-prod
        ;;
    "status")
        pm2 list
        pm2 logs --lines 20
        ;;
    "logs")
        pm2 logs "$2"
        ;;
    "restart")
        pm2 restart ecosystem.config.js
        ;;
    *)
        echo "Usage: $0 {start-dev|start-prod|stop-dev|stop-prod|status|logs|restart}"
        echo "  start-dev   - Start development server (port 5002)"
        echo "  start-prod  - Start production server (port 5001)"
        echo "  stop-dev    - Stop development server"
        echo "  stop-prod   - Stop production server"
        echo "  status      - Show process status"
        echo "  logs [name] - Show logs (specify 'interpreter-dev' or 'interpreter-prod')"
        echo "  restart     - Restart all servers"
        exit 1
        ;;
esac