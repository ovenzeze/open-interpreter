#!/bin/bash

# Set base directories
export INTERPRETER_BASE="$HOME/.interpreter"
export INTERPRETER_HOME="$INTERPRETER_BASE/.prod"
export PYTHONPATH="$INTERPRETER_HOME:$PYTHONPATH"

# Prepare Python environment
function prepare_environment() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$script_dir/scripts/uv-prepare.sh" ]; then
        echo "{\"status\":\"info\",\"message\":\"✅ Preparing Python environment using uv...\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        source "$script_dir/scripts/uv-prepare.sh"
    else
        echo "{\"status\":\"error\",\"message\":\"❌ uv-prepare.sh not found\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        exit 1
    fi
}

# Setup environment variables
function setup_env_vars() {
    # Load .env file
    if [ -f .env ]; then
        echo "{\"status\":\"info\",\"message\":\"✅ Loading environment variables from .env file\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        export $(grep -v '^#' .env | xargs)
    fi
    
    # Set server ports
    export SERVER_PORT_PROD=5001
    export SERVER_PORT_DEV=5002
    # Ensure current directory is in PYTHONPATH
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    # Set log level
    export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
}

# Create necessary directories
mkdir -p "$INTERPRETER_BASE"/{logs/{prod,dev},run}

function ensure_prod_code() {
    if [ ! -d "$INTERPRETER_HOME" ]; then
        echo "{\"status\":\"info\",\"message\":\"⚠️ Cloning production code\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        git clone https://github.com/ovenzeze/open-interpreter.git "$INTERPRETER_HOME"
        cd "$INTERPRETER_HOME"
        git checkout main
    else
        echo "{\"status\":\"info\",\"message\":\"⚠️ Updating production code\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        cd "$INTERPRETER_HOME"
        git fetch origin
        git reset --hard origin/main
        git clean -fd
        git checkout main
        git pull origin main
    fi
}

# Print service information
function print_service_info() {
    local service_type=$1
    local port
    if [ "$service_type" = "prod" ]; then
        port=$SERVER_PORT_PROD
    else
        port=$SERVER_PORT_DEV
    fi
    
    echo "{\"status\":\"info\",\"message\":\"✅ Service Information\",\"details\":{
        \"serviceType\":\"$service_type\",
        \"pythonPath\":\"$PYTHON_PATH\",
        \"interpreterPath\":\"$INTERPRETER_HOME\",
        \"virtualEnv\":\"$VIRTUAL_ENV\",
        \"logDirectory\":\"$INTERPRETER_BASE/logs/$service_type\",
        \"errorLog\":\"$INTERPRETER_BASE/logs/$service_type/err.log\",
        \"outputLog\":\"$INTERPRETER_BASE/logs/$service_type/out.log\",
        \"serverPort\":\"$port\",
        \"logLevel\":\"$LOG_LEVEL\"
    },\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
}

# Check and install Node.js dependencies
function ensure_node_deps() {
    if [ ! -d "node_modules" ]; then
        echo "{\"status\":\"info\",\"message\":\"⚠️ Installing Node.js dependencies\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
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
        echo "{\"status\":\"info\",\"message\":\"✅ Starting production server\",\"python\":\"$PYTHON_PATH\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
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
        echo "{\"status\":\"error\",\"message\":\"❌ Invalid command\",\"usage\":{
            \"commands\":[
                {\"cmd\":\"start-dev\",\"desc\":\"Start development server (port 5002)\"},
                {\"cmd\":\"start-prod\",\"desc\":\"Start production server (port 5001)\"},
                {\"cmd\":\"stop-dev\",\"desc\":\"Stop development server\"},
                {\"cmd\":\"stop-prod\",\"desc\":\"Stop production server\"},
                {\"cmd\":\"status\",\"desc\":\"Show process status\"},
                {\"cmd\":\"logs\",\"desc\":\"Show logs (specify 'interpreter-dev' or 'interpreter-prod')\"},
                {\"cmd\":\"restart\",\"desc\":\"Restart all servers\"}
            ]
        },\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
        exit 1
        ;;
esac