#!/bin/bash

# 设置基础目录
export INTERPRETER_BASE="$HOME/.interpreter"
export INTERPRETER_HOME="$INTERPRETER_BASE/.prod"
export PYTHONPATH="$INTERPRETER_HOME:$PYTHONPATH"

# Poetry 环境检查和配置
function ensure_poetry_env() {
    # 检查 poetry 是否已安装
    if ! command -v poetry &> /dev/null; then
        echo "Poetry not found. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    # 获取当前项目的虚拟环境信息
    local venv_path=""
    if poetry env info -p &> /dev/null; then
        venv_path=$(poetry env info -p)
    fi
    
    # 检查当前是否已在虚拟环境中
    if [ -n "$VIRTUAL_ENV" ]; then
        if [ "$VIRTUAL_ENV" = "$venv_path" ]; then
            echo "Already in the correct virtual environment: $VIRTUAL_ENV"
        else
            echo "Switching from $VIRTUAL_ENV to project's virtual environment"
            deactivate 2>/dev/null || true
            source "$venv_path/bin/activate"
        fi
    else
        if [ -n "$venv_path" ]; then
            echo "Activating existing virtual environment: $venv_path"
            source "$venv_path/bin/activate"
        else
            echo "Creating new virtual environment..."
            poetry install
            venv_path=$(poetry env info -p)
            source "$venv_path/bin/activate"
        fi
    fi
    
    # 设置并验证Python解释器路径
    PYTHON_PATH="$(poetry env info -p)/bin/python"
    if [ ! -f "$PYTHON_PATH" ]; then
        echo "Error: Python interpreter not found at $PYTHON_PATH"
        exit 1
    fi
    
    echo "Using Python interpreter: $PYTHON_PATH"
    export PYTHON_PATH
}

# 确保 Poetry 环境在任何操作之前准备就绪
ensure_poetry_env

# 添加环境变量配置
function setup_env_vars() {
    # 设置服务端口
    export SERVER_PORT_PROD=5001
    # 使用 ensure_poetry_env 中设置的 PYTHON_PATH
    echo "Using Python path: $PYTHON_PATH"
    # 设置日志级别
    export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
}

# 在ensure_poetry_env后调用
setup_env_vars

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
    echo "========== Service Information =========="
    echo "Service Type: $service_type"
    echo "Python Path: $PYTHON_PATH"
    echo "Open Interpreter Path: $INTERPRETER_HOME"
    echo "Virtual Environment: $(poetry env info --path)"
    echo "Log Directory: $INTERPRETER_BASE/logs/$service_type"
    echo "Error Log: $INTERPRETER_BASE/logs/$service_type/err.log"
    echo "Output Log: $INTERPRETER_BASE/logs/$service_type/out.log"
    echo "Server Port: ${service_type}-prod && echo $SERVER_PORT_PROD || echo $SERVER_PORT_DEV"
    echo "Log Level: $LOG_LEVEL"
    echo "========================================"
}

case "$1" in
    "start-dev")
        ensure_poetry_env
        setup_env_vars
        print_service_info "dev"
        pm2 start ecosystem.config.js --only interpreter-dev
        ;;
    "start-prod")
        ensure_poetry_env
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