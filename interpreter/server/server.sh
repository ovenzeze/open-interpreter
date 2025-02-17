#!/bin/bash

SUPERVISOR_CONF="./supervisord.conf"

function check_port() {
    local port=$1
    if lsof -i :$port > /dev/null; then
        echo "Port $port is already in use"
        return 1
    fi
    return 0
}

function start_dev() {
    echo "Starting development server (port 5002)..."
    check_port 5002 || exit 1
    supervisorctl -c $SUPERVISOR_CONF start interpreter_server_dev
    echo "Development server status:"
    supervisorctl -c $SUPERVISOR_CONF status interpreter_server_dev
}

function start_prod() {
    echo "Starting production server (port 5001)..."
    check_port 5001 || exit 1
    supervisorctl -c $SUPERVISOR_CONF start interpreter_server_prod
    echo "Production server status:"
    supervisorctl -c $SUPERVISOR_CONF status interpreter_server_prod
}

function stop_dev() {
    echo "Stopping development server..."
    supervisorctl -c $SUPERVISOR_CONF stop interpreter_server_dev
}

function stop_prod() {
    echo "Stopping production server..."
    supervisorctl -c $SUPERVISOR_CONF stop interpreter_server_prod
}

function status() {
    echo "Server status:"
    supervisorctl -c $SUPERVISOR_CONF status
}

function restart_supervisor() {
    echo "Restarting supervisor..."
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
    "restart")
        restart_supervisor
        ;;
    *)
        echo "Usage: $0 {start-dev|start-prod|stop-dev|stop-prod|status|restart-supervisor}"
        echo "  start-dev          - Start development server (port 5002)"
        echo "  start-prod         - Start production server (port 5001)"
        echo "  stop-dev           - Stop development server"
        echo "  stop-prod          - Stop production server"
        echo "  status            - Show all server statuses"
        echo "  restart-supervisor - Restart supervisor"
        exit 1
        ;;
esac

exit 0 