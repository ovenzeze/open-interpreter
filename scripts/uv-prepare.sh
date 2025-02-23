#!/bin/bash

# 设置基础目录
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

# 检查uv是否安装
function ensure_uv() {
    if ! command -v uv &> /dev/null; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
    echo "uv is available: $(uv --version)"
}

# 检查并创建虚拟环境
function ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        uv venv
    fi
    
    # 激活虚拟环境
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "Activating virtual environment..."
        source "$VENV_DIR/bin/activate"
    elif [ "$VIRTUAL_ENV" != "$(pwd)/$VENV_DIR" ]; then
        echo "Switching virtual environment..."
        deactivate
        source "$VENV_DIR/bin/activate"
    fi
    
    echo "Using Python: $(which python)"
    echo "Virtual env: $VIRTUAL_ENV"
}

# 从pyproject.toml安装依赖
function install_dependencies() {
    if [ ! -f "pyproject.toml" ]; then
        echo "Error: pyproject.toml not found"
        exit 1
    fi
    
    echo "Installing PyTorch dependencies first..."
    # 针对 M1/M2 Mac
    if [[ "$(uname -m)" == "arm64" ]]; then
        uv pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu
    else
        # 针对 Intel Mac
        uv pip install torch torchvision
    fi
    
    echo "Installing base dependencies first..."
    uv pip install shortuuid fastapi uvicorn python-dotenv

    echo "Installing project dependencies from pyproject.toml..."
    # 移除 --no-deps 标志，允许安装所有依赖
    uv pip install -e ".[os,safe,local,server]"
}

# 设置环境变量
function setup_env_vars() {
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    export PYTHON_PATH="$VIRTUAL_ENV/bin/python"
    export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
}

# 主执行流程
echo "=== Starting environment setup with uv ==="
ensure_uv
ensure_venv
install_dependencies
setup_env_vars
echo "=== Environment setup completed ==="

# 打印环境信息
echo "========== Environment Information =========="
echo "Python Path: $PYTHON_PATH"
echo "Virtual Environment: $VIRTUAL_ENV"
echo "Python Version: $(python --version)"
echo "Pip Version: $(pip --version)"
echo "UV Version: $(uv --version)"
echo "========================================"
