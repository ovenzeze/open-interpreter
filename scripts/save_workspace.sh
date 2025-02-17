#!/bin/bash

# 保存当前分支名
current_branch=$(git rev-parse --abbrev-ref HEAD)

# 创建工作区状态目录
mkdir -p .workspace_states/$current_branch

# 复制IDE配置文件
cp -r .vscode .workspace_states/$current_branch/ 2>/dev/null || true
cp -r .cursor .workspace_states/$current_branch/ 2>/dev/null || true

echo "Workspace state saved for branch: $current_branch" 