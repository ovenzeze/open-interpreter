#!/bin/bash

SUPERVISOR_CONF="interpreter/server/supervisord.conf"

function check_port() {
    local port=$1
    if lsof -i :$port > /dev/null; then
        echo "端口 $port 已被占用"
        return 1
    fi
    return 0
}

function start_dev() {
    echo "启动开发环境服务器 (端口 5002)..."
    check_port 5002 || exit 1
    supervisorctl -c $SUPERVISOR_CONF start interpreter_server_dev
    echo "开发服务器状态："
    supervisorctl -c $SUPERVISOR_CONF status interpreter_server_dev
}

function start_prod() {
    echo "启动生产环境服务器 (端口 5001)..."
    check_port 5001 || exit 1
    supervisorctl -c $SUPERVISOR_CONF start interpreter_server_prod
    echo "生产服务器状态："
    supervisorctl -c $SUPERVISOR_CONF status interpreter_server_prod
}

function stop_dev() {
    echo "停止开发环境服务器..."
    supervisorctl -c $SUPERVISOR_CONF stop interpreter_server_dev
}

function stop_prod() {
    echo "停止生产环境服务器..."
    supervisorctl -c $SUPERVISOR_CONF stop interpreter_server_prod
}

function status() {
    echo "服务器状态："
    supervisorctl -c $SUPERVISOR_CONF status
}

function restart_supervisor() {
    echo "重启 supervisor..."
    pkill supervisord
    sleep 2
    supervisord -c $SUPERVISOR_CONF
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
    "restart-supervisor")
        restart_supervisor
        ;;
    *)
        echo "用法: $0 {start-dev|start-prod|stop-dev|stop-prod|status|restart-supervisor}"
        echo "  start-dev          - 启动开发环境服务器 (端口 5002)"
        echo "  start-prod         - 启动生产环境服务器 (端口 5001)"
        echo "  stop-dev           - 停止开发环境服务器"
        echo "  stop-prod          - 停止生产环境服务器"
        echo "  status            - 显示所有服务器状态"
        echo "  restart-supervisor - 重启 supervisor"
        exit 1
        ;;
esac

exit 0 