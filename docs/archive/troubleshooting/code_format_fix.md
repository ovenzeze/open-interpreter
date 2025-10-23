# 代码块格式化问题修复指南

## 问题背景

Open Interpreter 的 LLM 接口目前存在代码块格式化输出问题，特别是在处理 shell 命令和其他代码时出现了严重的格式混乱现象。这些问题直接影响了用户体验和系统可用性。

### 主要症状

1. **命令被不合理地分割**：单个完整的命令被拆分成多个小片段，每个片段前都添加了 `shell` 标记
   ```
   shell
   ifconfig | 
   shell
   grep "inet6"
   ```
   正确的格式应该是：
   ```shell
   ifconfig | grep "inet6"
   ```

2. **代码块格式不正确**：没有使用标准的 Markdown 代码块格式
   正确的格式应为：
   ````
   ```shell
   命令内容
   ```
   ````

3. **命令输出结果展示混乱**：
   - 使用了无意义的数字编号
   - 没有清晰区分命令和输出结果
   - 没有使用代码块格式化输出结果

4. **命令拆分错误**：比如将 `grep` 拆成了 `g` 和 `rep`，这完全是错误的处理方式

## 问题根源分析

通过对代码库的分析，我们确定问题出现在 `interpreter/server/utils.py` 文件的 `format_openai_stream_chunk` 函数中。这个函数负责将流式输出的内容块格式化为前端可接收的形式。

问题产生的根本原因：

1. **流式处理机制**：LLM 接口将输出按 token 分割成小块进行流式传输
2. **缺乏完整性保护**：没有机制确保命令或代码作为一个整体被处理
3. **格式化逻辑缺陷**：每个小块被单独格式化，而不是在适当的上下文中处理

## 修复方案

### 1. 修改文件

需要修改的核心文件：`interpreter/server/utils.py`

### 2. 修改内容

我们需要优化 `format_openai_stream_chunk` 函数的三个主要部分：

#### a) 控制台输出处理（主要是 shell 命令）

```python
# 控制台输出特殊处理 - 改进代码块格式处理
if chunk.type == 'console' and chunk.role == 'computer':
    content_str = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
    # 替换可能导致问题的字符
    content_str = content_str.replace('\r', '').replace('\0', '')
    
    # 处理控制台输出的不同阶段 - 统一使用完整代码块
    if chunk.start:
        # 控制台输出开始 - 使用完整代码块标记
        shell_format = chunk.format or "shell"  # 默认使用shell，但尊重指定的格式
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': f"\n```{shell_format}\n"  # 使用完整的语言标记
                },
                'finish_reason': None
            }]
        }
    elif chunk.end:
        # 控制台输出结束 - 完整结束标记
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': "\n```\n"  # 完整的代码块结束标记
                },
                'finish_reason': None
            }]
        }
    else:
        # 控制台输出内容 - 直接整体传递内容，不做额外分割
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': content_str  # 保持内容完整性
                },
                'finish_reason': None
            }]
        }
    return f"data: {to_single_line_json(response)}\n\n"
```

#### b) 代码块处理（各种编程语言）

```python
# 代码块特殊处理 - 改进代码块的格式处理
if chunk.type == 'code':
    content = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
    # 清理内容中可能导致问题的字符
    content = content.replace('\r', '').replace('\0', '')
    
    # 如果是代码块开始 - 使用更明确的语言标记
    if chunk.start:
        # 确保有语言标记，如果没有则使用合适的默认值
        lang = chunk.format or 'python'  # 默认使用python作为更常见的选择
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': f"\n```{lang}\n"  # 明确的语言标记
                },
                'finish_reason': None
            }]
        }
    # 如果是代码块结束
    elif chunk.end:
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': "\n```\n"  # 完整的结束标记
                },
                'finish_reason': None
            }]
        }
    # 普通代码内容 - 保持完整性
    else:
        response = {
            'id': chunk_id,
            'object': 'chat.completion.chunk',
            'created': current_time,
            'model': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
            'choices': [{
                'index': 0,
                'delta': {
                    'content': content  # 不分割代码内容
                },
                'finish_reason': None
            }]
        }
    return f"data: {to_single_line_json(response)}\n\n"
```

#### c) 普通文本处理

```python
# 普通消息内容处理
content = str(chunk.content) if not isinstance(chunk.content, str) else chunk.content
# 清理内容中可能导致问题的字符
content = content.replace('\r', '').replace('\0', '')

# 改进普通文本块处理...（其余代码与原有处理类似）
```

## 验证方案

为确保修复的有效性，我们设计了完整的验证流程：

### 1. 创建验证测试脚本

创建 `validation_test.py` 文件，用于测试代码块格式化：

```python
import requests
import json
import time

def test_command_formatting(command, server_url="http://localhost:5001"):
    """测试命令格式化"""
    print(f"测试命令: {command}")

    # 发送命令到服务器
    response = requests.post(
        f"{server_url}/v1/chat/completions", 
        json={
            "messages": [{"role": "user", "content": f"执行并解释这个命令: {command}"}],
            "stream": True
        },
        headers={"Content-Type": "application/json"},
        stream=True
    )

    # 收集结果
    output = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: ") and line != "data: [DONE]":
                data = json.loads(line[6:])
                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    output += content
                    print(content, end="", flush=True)

    # 保存输出到文件，便于分析
    with open(f"test_output_{int(time.time())}.txt", "w") as f:
        f.write(output)
    
    print("\n-------测试完成-------\n")
    return output

# 测试用例 - 覆盖各种复杂命令场景
test_cases = [
    "ifconfig | grep inet6 | grep -v fe80::",
    "ls -la | grep '.py'",
    "for i in {1..5}; do echo $i; done",
    "find . -name '*.py' | xargs wc -l | sort -nr | head -n 5"
]

# 执行测试
for cmd in test_cases:
    test_command_formatting(cmd)
```

### 2. 验证流程步骤

1. **修改前测试**：
   ```bash
   # 启动未修改的服务器
   ./server.sh start-dev
   
   # 运行测试脚本，记录原始问题
   python validation_test.py
   
   # 保存测试结果
   mkdir -p test_results/before_fix
   mv test_output_* test_results/before_fix/
   ```

2. **应用修复**：
   ```bash
   # 修改utils.py文件
   vi interpreter/server/utils.py
   # 应用上述修改
   
   # 重启服务器
   ./server.sh stop-dev
   ./server.sh start-dev
   ```

3. **修改后测试**：
   ```bash
   # 运行相同的测试脚本
   python validation_test.py
   
   # 保存测试结果
   mkdir -p test_results/after_fix
   mv test_output_* test_results/after_fix/
   ```

4. **结果比较与分析**：
   ```bash
   # 使用diff工具比较修改前后的输出
   for before in test_results/before_fix/*; do
     name=$(basename $before)
     after="test_results/after_fix/$name"
     if [ -f "$after" ]; then
       echo "比较文件: $name"
       diff -u "$before" "$after"
     fi
   done
   ```

### 3. 验证成功标准

成功修复需满足以下标准：

1. **命令完整性**：
   - shell命令作为完整的代码块显示，不再被分割成多个片段
   - 不再出现命令被错误分割的情况（如 `grep` 被分割为 `g` 和 `rep`）

2. **格式正确性**：
   - 所有命令都包含在正确的Markdown代码块中
   - 代码块有正确的语言标记（如 `shell`、`python` 等）
   - 代码块有清晰的开始 ``` 和结束 ``` 标记

3. **输出清晰性**：
   - 命令和结果有明确区分
   - 不再有数字编号或其他混淆格式
   - 输出结果易于阅读和理解

### 4. 高级验证 - 复杂场景测试

为测试修复在各种复杂情况下的稳定性，添加以下测试：

```python
def advanced_tests():
    """复杂命令测试"""
    complex_commands = [
        # 长管道命令
        "ps aux | grep python | awk '{print $2}' | xargs kill -9",
        
        # 包含多种特殊字符的命令
        "echo \"Testing 'quotes' and \\\"escapes\\\" with $variables and $(commands)\"",
        
        # 多行脚本
        """cat << EOF > test.sh
#!/bin/bash
for i in {1..5}; do
  echo "Line $i"
done
EOF
chmod +x test.sh
./test.sh
rm test.sh""",

        # 嵌套命令
        "find . -type f -name \"*.md\" -exec grep -l \"code\" {} \\; | wc -l"
    ]
    
    for cmd in complex_commands:
        test_command_formatting(cmd)

# 执行高级测试
advanced_tests()
```

## 部署建议

1. **分阶段部署**：
   - 先在开发环境测试
   - 然后部署到少量生产服务器
   - 最后全量部署

2. **回滚准备**：
   - 保留原始代码副本
   - 准备快速回滚方案，以应对潜在问题

3. **监控与反馈**：
   - 部署后监控系统日志
   - 收集用户反馈，确认问题是否彻底解决

## 预防措施

为防止类似问题在未来再次发生：

1. **添加自动化测试**：
   - 将此测试脚本添加到项目的测试套件中
   - 确保每次代码修改都会运行这些测试

2. **代码审查重点**：
   - 在代码审查中特别关注流式处理和格式化相关的修改
   - 增加对流式输出格式的检查机制

3. **文档更新**：
   - 更新开发文档，说明流式处理中的格式化注意事项
   - 记录本次问题的处理经验，供未来参考

## 相关资源

- [Markdown 代码块规范](https://www.markdownguide.org/basic-syntax/#code-blocks)
- [OpenAI 流式接口文档](https://platform.openai.com/docs/api-reference/streaming)

## 维护者

本文档由系统开发团队维护，如有问题请联系技术支持团队。

最后更新: 2024-07-20 