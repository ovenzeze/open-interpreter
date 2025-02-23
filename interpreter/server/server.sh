#!/bin/bash

# 设置基础目录
INTERPRETER_BASE="$HOME/.interpreter"
INTERPRETER_HOME="$INTERPRETER_BASE/.prod"  # 生产环境完整项目目录
export PYTHONPATH="$INTERPRETER_HOME:$PYTHONPATH"

# 定义其他路径 (基于生产环境目录)
LOGS_DIR="$INTERPRETER_HOME/logs"
CONFIG_DIR="$INTERPRETER_HOME/interpreter/server"  # 使用项目内的配置
SUPERVISOR_SOCK="$INTERPRETER_HOME/run/supervisor.sock"

# 获取当前脚本路径(用于开发环境)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 验证路径是否符合规范
if [[ ! "$SCRIPT_DIR" =~ .*/open-interpreter/interpreter/server$ ]]; then
    echo "Error: Invalid installation path. Expected path pattern: */open-interpreter/interpreter/server"
    echo "Current path: $SCRIPT_DIR"
    exit 1
fi

SUPERVISOR_CONF="$SCRIPT_DIR/supervisord.conf"
SUPERVISOR_HTTP="http://localhost:9001"
SUPERVISOR_USER="isakeem"
SUPERVISOR_PASS="isakeem123"

# 设置基础环境变量
export DEV_CODE_PATH="$PROJECT_ROOT"

function print_section_header() {
    local title=$1
    echo -e "\n\033[1;36m=== $title ===\033[0m"
}

function print_section_footer() {
    echo -e "\033[1;36m====================\033[0m\n"
}

function print_paths() {
    local env=$1
    print_section_header "Environment Information"
    echo "Interpreter Home: $INTERPRETER_HOME"
    echo "Python Path: $PYTHONPATH"
    echo "Logs Directory: $LOGS_DIR"
    echo "Config Directory: $CONFIG_DIR"
    if [[ "$env" == "prod" ]]; then
        echo "Production Code: $INTERPRETER_HOME"
    else
        echo "Development Environment:"
        echo "  Server Directory: $SCRIPT_DIR"
        echo "  Project Root: $PROJECT_ROOT"
        echo "  Supervisor Config: $SUPERVISOR_CONF"
    fi
    echo "  Current Directory: $(pwd)"
    print_section_footer
}

function print_system_info() {
    print_section_header "System Information"
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "Python Version: $(python --version 2>&1)"
    echo "Current Directory: $(pwd)"
    
    if [[ "$1" == "prod" ]]; then
        cd "$INTERPRETER_HOME" 2>/dev/null && {
            echo -e "\nGit Information:"
            echo "  Branch: $(git branch --show-current 2>/dev/null)"
            echo "  Commit: $(git rev-parse HEAD 2>/dev/null)"
        }
    else
        echo -e "\nGit Information:"
        echo "  Branch: $(git branch --show-current 2>/dev/null)"
        echo "  Commit: $(git rev-parse HEAD 2>/dev/null)"
    fi
    print_section_footer
}

function print_management_info() {
    print_section_header "Management Information"
    echo "Supervisor Access:"
    echo "  Web Interface: http://localhost:9001"
    echo "  Username: $SUPERVISOR_USER"
    echo "  Password: $SUPERVISOR_PASS"
    
    echo -e "\nLog Files:"
    echo "  Supervisor: $INTERPRETER_HOME/logs/supervisord.log"
    echo "  Production:"
    echo "    - Main: $INTERPRETER_HOME/logs/prod/server.log"
    echo "    - Error: $INTERPRETER_HOME/logs/prod/server.err.log"
    echo "  Development:"
    echo "    - Main: $INTERPRETER_HOME/logs/dev/server.log"
    echo "    - Error: $INTERPRETER_HOME/logs/dev/server.err.log"
    print_section_footer
}

function check_port() {
    local port=$1
    local port_info=$(lsof -i :$port 2>/dev/null)
    if [ ! -z "$port_info" ]; then
        print_section_header "Port $port Usage Details"
        
        # 获取进程 PID
        local pid=$(echo "$port_info" | tail -n 1 | awk '{print $2}')
        
        echo "Process Information:"
        ps -p $pid -o pid,ppid,user,%cpu,%mem,etime,command
        
        echo -e "\nPort Details:"
        echo "$port_info"
        
        # 显示日志文件最后几行
        local log_file="$INTERPRETER_HOME/logs/prod/server.log"
        if [[ -f "$log_file" ]]; then
            echo -e "\nRecent Log Entries:"
            tail -n 5 "$log_file"
        fi
        
        print_section_footer
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
    
}

function ensure_supervisor() {
    local env=$1
    local config_path
    local log_dir
    
    if [[ "$env" == "prod" ]]; then
        config_path="$CONFIG_DIR/supervisord.conf"
        log_dir="$LOGS_DIR/prod"
    else
        config_path="$SCRIPT_DIR/supervisord.conf"
        log_dir="$LOGS_DIR/dev"
    fi
    
    # 确保目录存在
    mkdir -p "$log_dir"
    
    # 检查 supervisor 是否已运行
    if ! check_supervisor; then
        echo "Starting supervisord for $env environment..."
        supervisord -c "$config_path"
        sleep 2
    fi
}

function ensure_directories() {
    # 创建必要的目录结构
    mkdir -p "$LOGS_DIR"/{prod,dev}
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$INTERPRETER_HOME/run"
}

function ensure_prod_code() {
    echo "Setting up production environment..."
    
    # 确保基础目录存在
    mkdir -p "$INTERPRETER_BASE"
    
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
    
    # 确保必要的目录存在
    mkdir -p "$LOGS_DIR"/{prod,dev}
    mkdir -p "$INTERPRETER_HOME/run"
}

function print_api_info() {
    local port=$1
    local host_ip=$(hostname -I | awk '{print $1}')
    print_section_header "API Endpoints"
    echo "Local Access:"
    echo "  - Chat: http://localhost:$port/v1/chat/completions"
    echo "  - Models: http://localhost:$port/v1/models"
    echo -e "\nNetwork Access:"
    echo "  - Chat: http://$host_ip:$port/v1/chat/completions"
    echo "  - Models: http://$host_ip:$port/v1/models"
    print_section_footer
}

function check_health() {
    local port=$1
    local max_retries=5
    local retry_interval=2
    
    echo "Checking server health on port $port..."
    
    for ((i=1; i<=max_retries; i++)); do
        if curl -s "http://localhost:$port/health" >/dev/null; then
            echo "Server is healthy"
            return 0
        fi
        echo "Attempt $i of $max_retries: Server not responding, waiting ${retry_interval}s..."
        sleep $retry_interval
    done
    
    echo "Server health check failed after $max_retries attempts"
    return 1
}

function start_prod() {
    print_section_header "Starting Production Server"
    echo "Initializing production environment on port 5001..."
    
    # 准备生产环境
    ensure_prod_code
    
    # 切换到生产目录并验证环境
    cd "$INTERPRETER_HOME" || exit 1
    verify_python_env "prod" || exit 1
    
    # 其他检查
    print_paths "prod"
    print_system_info "prod"
    check_port 5001 || exit 1
    
    # 使用生产环境配置启动服务
    ensure_supervisor "prod"
    supervisorctl_cmd start interpreter_server_prod
    
    # 健康检查
    check_health 5001 || {
        echo "Production server failed health check"
        supervisorctl_cmd stop interpreter_server_prod
        exit 1
    }
    
    echo -e "\nProduction server is now running!"
    print_section_footer
}

function start_dev() {
    echo "Starting development server (port 5002)..."
    
    # 使用开发环境
    cd "$SCRIPT_DIR"
    
    print_paths "dev"
    print_system_info "dev"
    check_port 5002 || exit 1
    
    # 确保supervisor在开发环境运行
    ensure_supervisor "dev"
    
    supervisorctl_cmd start interpreter_server_dev
    
    check_health 5002 || {
        echo "Development server failed health check"
        supervisorctl_cmd stop interpreter_server_dev
        exit 1
    }
    
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
    local status_ok=false
    
    if supervisorctl_cmd status >/dev/null 2>&1; then
        supervisorctl_cmd status
        status_ok=true
    else
        echo "Warning: Cannot get server status"
        echo "Supervisor may not be running or not responding"
        check_port 9001
    fi
    
    print_management_info
    
    if [ "$status_ok" = true ]; then
        return 0
    else
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

function verify_python_env() {
    print_section_header "Python Environment"
    
    # 显示环境信息
    echo "Current Directory: $(pwd)"
    echo "Interpreter Home: $INTERPRETER_HOME"
    echo "Python Binary: $(which python)"
    echo "Python Version: $(python --version 2>&1)"
    echo "PYTHONPATH: $PYTHONPATH"
    
    if [[ "$1" == "prod" ]]; then
        cd "$INTERPRETER_HOME" || {
            echo "Error: Cannot change to production directory"
            return 1
        }
    fi
    
    # 验证interpreter包的位置和版本
    echo -e "\nInterpreter Package Location:"
    python -c "import interpreter; print(f'  {interpreter.__file__}')" || {
        echo "Error: interpreter package not found in PYTHONPATH"
        return 1
    }
    
    echo -e "\nPackage Version:"
    python -c "import interpreter; print(f'  interpreter: {interpreter.__version__}')"
    
    print_section_footer
    return 0
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