#!/bin/bash

# 获取脚本所在目录的绝对路径，并处理大小写问题
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 确保使用正确的小写路径
if [[ "$SCRIPT_DIR" =~ .*/open-[iI]nterpreter/[iI]nterpreter/server$ ]]; then
    # 统一使用小写
    SCRIPT_DIR="${SCRIPT_DIR//[Ii]nterpreter/interpreter}"
    PROJECT_ROOT="${PROJECT_ROOT//[Ii]nterpreter/interpreter}"
fi

SUPERVISOR_CONF="$SCRIPT_DIR/supervisord.conf"
SUPERVISOR_HTTP="http://localhost:9001"
SUPERVISOR_USER="admin"
SUPERVISOR_PASS="123456"

# 设置基础环境变量
export INTERPRETER_HOME="$HOME/.interpreter"
export PROD_CODE_PATH="$INTERPRETER_HOME/.prod"
export DEV_CODE_PATH="$PROJECT_ROOT"

function print_paths() {
    echo "=== Path Information ==="
    echo "Script Directory: $SCRIPT_DIR"
    echo "Project Root: $PROJECT_ROOT"
    echo "Supervisor Config: $SUPERVISOR_CONF"
    echo "Development Code Path: $DEV_CODE_PATH"
    echo "Production Code Path: $PROD_CODE_PATH"
    echo "Interpreter Home: $INTERPRETER_HOME"
    echo "Current Directory: $(pwd)"
    echo "======================="
}

function print_system_info() {
    echo "=== System Information ==="
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "Python Version: $(python --version 2>&1)"
    echo "Current Directory: $(pwd)"
    
    # 区分环境显示 Git 信息
    if [[ "$1" == "prod" ]]; then
        cd "$PROD_CODE_PATH" 2>/dev/null && {
            echo "Production Git Branch: $(git branch --show-current 2>/dev/null)"
            echo "Production Git Commit: $(git rev-parse HEAD 2>/dev/null)"
        }
    else
        echo "Development Git Branch: $(git branch --show-current 2>/dev/null)"
        echo "Development Git Commit: $(git rev-parse HEAD 2>/dev/null)"
    fi
    echo "=========================="
}

function print_management_info() {
    echo -e "\n=== Management Information ==="
    echo "Supervisor Web Interface: http://localhost:9001"
    echo "Supervisor Username: $SUPERVISOR_USER"
    echo "Supervisor Password: $SUPERVISOR_PASS"
    echo -e "\nLog Files:"
    echo "  Supervisor Log: $INTERPRETER_HOME/logs/supervisord.log"
    echo "  Production Log: $INTERPRETER_HOME/logs/prod/server.log"
    echo "  Production Error Log: $INTERPRETER_HOME/logs/prod/server.err.log"
    echo "  Development Log: $INTERPRETER_HOME/logs/dev/server.log"
    echo "  Development Error Log: $INTERPRETER_HOME/logs/dev/server.err.log"
    echo "==========================="
}

function check_port() {
    local port=$1
    local port_info=$(lsof -i :$port 2>/dev/null)
    if [ ! -z "$port_info" ]; then
        echo "Port $port is already in use:"
        echo "=== Port $port Usage Details ==="
        echo "$port_info"
        echo "==========================="
        return 1
    fi
    return 0
}

function supervisorctl_cmd() {
    supervisorctl -s $SUPERVISOR_HTTP -u $SUPERVISOR_USER -p $SUPERVISOR_PASS "$@"
}

function check_supervisor() {
    # 检查 supervisor 是否已运行
    if pgrep supervisord > /dev/null; then
        # 尝试连接到 supervisor HTTP 接口
        if supervisorctl_cmd status >/dev/null 2>&1; then
            return 0
        else
            echo "Warning: Supervisor process exists but not responding"
            echo "You may need to manually clean up the process:"
            echo "pkill supervisord"
            return 1
        fi
    fi
    
    # 使用已有的 check_port 函数检查端口
    check_port 9001 || return 1
    
    return 1
}

function ensure_supervisor() {
    # 确保必要的目录存在
    mkdir -p "$INTERPRETER_HOME/logs/prod"
    mkdir -p "$INTERPRETER_HOME/logs/dev"
    
    if ! check_supervisor; then
        echo "Starting supervisord..."
        cd "$SCRIPT_DIR"  # 确保在正确的目录下启动
        supervisord -c "$SUPERVISOR_CONF"
        sleep 2
    fi
}

function ensure_prod_code() {
    if [ ! -d "$PROD_CODE_PATH" ]; then
        echo "Cloning production code..."
        git clone https://github.com/ovenzeze/open-interpreter.git "$PROD_CODE_PATH"
    else
        echo "Updating production code..."
        cd "$PROD_CODE_PATH"
        git checkout main
        git pull
    fi
}

function print_api_info() {
    local port=$1
    local host_ip=$(hostname -I | awk '{print $1}')
    echo -e "\n=== API Endpoints ==="
    echo "Local URLs:"
    echo "  http://localhost:$port/v1/chat/completions"
    echo "  http://localhost:$port/v1/models"
    echo -e "\nNetwork URLs:"
    echo "  http://$host_ip:$port/v1/chat/completions"
    echo "  http://$host_ip:$port/v1/models"
    echo "====================="
}

function start_prod() {
    echo "Starting production server (port 5001)..."
    print_paths
    print_system_info "prod"
    check_port 5001 || exit 1
    ensure_prod_code
    ensure_supervisor
    supervisorctl_cmd start interpreter_server_prod
    echo "Production server status:"
    supervisorctl_cmd status interpreter_server_prod
    print_api_info 5001
    print_management_info
}

function start_dev() {
    echo "Starting development server (port 5002)..."
    print_paths
    print_system_info "dev"
    check_port 5002 || exit 1
    ensure_supervisor
    supervisorctl_cmd start interpreter_server_dev
    echo "Development server status:"
    supervisorctl_cmd status interpreter_server_dev
    print_api_info 5002
    print_management_info
}

function stop_dev() {
    echo "Stopping development server..."
    supervisorctl_cmd stop interpreter_server_dev
}

function stop_prod() {
    echo "Stopping production server..."
    supervisorctl_cmd stop interpreter_server_prod
}

function status() {
    echo "Server status:"
    if supervisorctl_cmd status >/dev/null 2>&1; then
        supervisorctl_cmd status
        print_management_info
        return 0
    else
        echo "Warning: Cannot get server status"
        echo "Supervisor may not be running or not responding"
        check_port 9001
        return 1
    fi
}

function restart_supervisor() {
    echo "Restarting supervisor..."
    pkill supervisord
    sleep 2
    cd "$SCRIPT_DIR"
    supervisord -c "$SUPERVISOR_CONF"
}

case "$1" in
    "start-dev")
        start_dev
        ;;
    "start-prod")
        start_prod
        ;;
    "stop-dev")
        stop_dev
        ;;
    "stop-prod")
        stop_prod
        ;;
    "status")
        status
        ;;
    "restart")
        restart_supervisor
        ;;
    *)
        echo "Usage: $0 {start-dev|start-prod|stop-dev|stop-prod|status|restart}"
        echo "  start-dev          - Start development server (port 5002)"
        echo "  start-prod         - Start production server (port 5001)"
        echo "  stop-dev           - Stop development server"
        echo "  stop-prod          - Stop production server"
        echo "  status            - Show all server statuses"
        echo "  restart           - Restart supervisor"
        exit 1
        ;;
esac

exit 0 