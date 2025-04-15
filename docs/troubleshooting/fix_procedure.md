# 代码块格式化问题修复流程

本文档提供了修复Open Interpreter代码块格式化问题的详细步骤流程，包括从问题重现到验证的全过程。

## 修复前准备

1. **环境搭建**

   ```bash
   # 克隆项目
   git clone https://github.com/ovenzeze/open-interpreter.git
   cd open-interpreter
   
   # 创建分支
   git checkout -b fix-code-format-issue
   
   # 安装依赖
   pip install -e .
   ```

2. **问题重现**

   ```bash
   # 启动服务器
   ./server.sh start-dev
   
   # 创建测试结果目录
   mkdir -p test_results/before_fix
   
   # 运行验证脚本，记录修复前的问题
   python docs/troubleshooting/validation_test.py --save-dir test_results/before_fix
   ```

## 代码修改步骤

1. **修改 `interpreter/server/utils.py` 文件**

   ```bash
   # 打开文件进行编辑
   vi interpreter/server/utils.py
   ```

2. **定位 `format_openai_stream_chunk` 函数**

   在文件中找到 `format_openai_stream_chunk` 函数(大约在第169行)，这是需要修改的核心部分。

3. **更新控制台输出处理逻辑**

   修改控制台输出部分的代码，特别是 `chunk.type == 'console' and chunk.role == 'computer'` 条件下的处理。
   确保代码块使用完整的开始和结束标记，且内容不被分割。

   ```python
   # 控制台输出特殊处理 - 改进代码块格式处理
   if chunk.type == 'console' and chunk.role == 'computer':
       content_str = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
       # 替换可能导致问题的字符
       content_str = content_str.replace('\r', '').replace('\0', '')
       
       # 处理控制台输出的不同阶段
       if chunk.start:
           # 确保使用正确的格式标记
           shell_format = chunk.format or "shell"
           response = {
               'id': chunk_id,
               'object': 'chat.completion.chunk',
               'created': current_time,
               'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
               'choices': [{
                   'index': 0,
                   'delta': {
                       'content': f"\n```{shell_format}\n"
                   },
                   'finish_reason': None
               }]
           }
       # ... 其余代码保留不变
   ```

4. **更新代码块处理逻辑**

   类似地，修改代码块处理部分(在 `chunk.type == 'code'` 条件下)，确保各种代码语言也能得到正确处理。

5. **保存文件**
   
   完成修改后保存文件。

## 修复验证

1. **重启服务**

   ```bash
   # 停止开发服务器
   ./server.sh stop-dev
   
   # 重新启动服务器
   ./server.sh start-dev
   ```

2. **运行测试脚本**

   ```bash
   # 创建测试结果目录
   mkdir -p test_results/after_fix
   
   # 运行验证测试
   python docs/troubleshooting/validation_test.py --save-dir test_results/after_fix
   ```

3. **比较修复效果**

   ```bash
   # 使用diff工具比较修改前后的结果
   for before in test_results/before_fix/*; do
     name=$(basename $before)
     after="test_results/after_fix/$name"
     if [ -f "$after" ]; then
       echo "比较文件: $name"
       diff -u "$before" "$after"
     fi
   done
   ```

4. **检查验证标准**

   确认以下验证标准都已满足:
   
   - [ ] 命令被完整显示，不再分割成多个片段
   - [ ] 代码块使用了正确的Markdown语法，包含语言标记
   - [ ] 命令和输出结果清晰区分
   - [ ] 不再有数字编号或其他混淆格式
   - [ ] 复杂命令也能正确处理

## 提交更改

1. **提交代码**

   ```bash
   # 添加修改
   git add interpreter/server/utils.py
   
   # 提交
   git commit -m "Fix: 解决代码块格式化问题，特别是shell命令被错误分割的问题"
   
   # 添加测试脚本
   git add docs/troubleshooting/validation_test.py
   git add docs/troubleshooting/code_format_fix.md
   git add docs/troubleshooting/fix_procedure.md
   
   # 提交文档
   git commit -m "Docs: 添加代码块格式化问题的文档和验证测试"
   ```

2. **创建Pull Request**

   ```bash
   # 推送到远程
   git push origin fix-code-format-issue
   ```

   然后在GitHub上创建Pull Request，详细说明修复内容和验证结果。

## 部署上线

1. **部署到开发环境**

   ```bash
   ./server.sh stop-dev
   git checkout main
   git pull
   ./server.sh start-dev
   ```

2. **部署到生产环境**

   ```bash
   ./server.sh stop-prod
   git pull
   ./server.sh start-prod
   ```

3. **监控运行情况**

   ```bash
   # 检查服务状态
   ./server.sh status
   
   # 查看日志
   ./server.sh logs interpreter-prod
   ```

## 注意事项

1. 确保修改仅限于格式化逻辑，不影响其他功能
2. 全面测试各种复杂命令情况
3. 密切关注用户反馈，确认问题是否完全解决
4. 保留原始代码备份，以便需要时回滚

## 相关文档

- [代码块格式化问题详细说明](./code_format_fix.md)
- [验证测试脚本](./validation_test.py)

最后更新: 2024-07-20 