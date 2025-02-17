#!/bin/bash

# 保存当前分支名
current_branch=$(git rev-parse --abbrev-ref HEAD)

# 检查是否存在保存的状态
if [ -d ".workspace_states/$current_branch" ]; then
    # 恢复IDE配置文件
    cp -r .workspace_states/$current_branch/.vscode . 2>/dev/null || true
    cp -r .workspace_states/$current_branch/.cursor . 2>/dev/null || true
    echo "Workspace state restored for branch: $current_branch"
else
    echo "No saved workspace state found for branch: $current_branch"
fi 