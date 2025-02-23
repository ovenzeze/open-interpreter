#!/bin/bash

# 设置基础目录
export INTERPRETER_BASE="$HOME/.interpreter"
export INTERPRETER_HOME="$INTERPRETER_BASE/.prod"
export PYTHONPATH="$INTERPRETER_HOME:$PYTHONPATH"

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

case "$1" in
    "start-dev")
        pm2 start ecosystem.config.js --only interpreter-dev
        ;;
    "start-prod")
        ensure_prod_code
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