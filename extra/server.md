# Open Interpreter 服务器实现文档

## 概述

本文档描述了 Open Interpreter 服务器的实现细节，包括配置、API接口、消息处理和安全考虑等方面。

## 基础配置

### 环境要求

```python
# 必需的Python包
flask==3.1.0
python-dotenv==1.0.1
requests==2.32.3
```

### 环境变量

| 变量名 | 描述 | 示例 |
|--------|------|------|
| `LITELLM_MODEL` | LLM模型配置 | `bedrock/anthropic.claude-3-sonnet` |
| `PORT` | 服务器端口 | `5001` |

## 服务器核心组件

### 1. 基础设置

```python
from flask import Flask, request, jsonify
from interpreter import interpreter
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

### 2. Interpreter 配置

```python
interpreter.llm.model = os.environ.get('LITELLM_MODEL', 'gpt-3.5-turbo')
interpreter.llm.context_window = 10000
interpreter.llm.max_tokens = 4096
interpreter.auto_run = True
```

## API 端点实现

### 1. Chat 端点 (`/v1/chat`)

处理聊天请求并支持代码执行。

#### 请求格式

```json
{
  "messages": [
    {
      "role": "user",
      "type": "message",
      "content": "Write a Python function"
    }
  ],
  "stream": true,
  "auto_run": true,
  "config": {
    "llm": {
      "model": "bedrock/anthropic.claude-3-sonnet",
      "temperature": 0.7
    }
  }
}
```

#### 实现细节

```python
@app.route('/v1/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    
    try:
        response_messages = []
        for chunk in interpreter.chat(messages, stream=stream):
            if stream:
                # 处理流式响应
                yield format_stream_chunk(chunk)
            else:
                # 收集完整响应
                response_messages.append(chunk)
                
        if not stream:
            return jsonify({"messages": response_messages})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 2. OpenAI 兼容端点 (`/v1/chat/completions`)

提供 OpenAI 兼容的接口。

#### 请求格式

```json
{
  "model": "bedrock/anthropic.claude-3-sonnet",
  "messages": [
    {
      "role": "user",
      "content": "Hello"
    }
  ],
  "stream": true
}
```

#### 实现细节

```python
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    messages = convert_to_interpreter_messages(data.get('messages', []))
    stream = data.get('stream', False)
    
    try:
        if stream:
            return stream_response(messages)
        else:
            return format_openai_response(messages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 3. 系统健康检查 (`/v1/health`)

提供系统状态信息。

```python
@app.route('/v1/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": interpreter.__version__,
        "llm": {
            "model": interpreter.llm.model,
            "status": "ready"
        }
    })
```

## 消息处理

### 1. 流式响应格式化

```python
def format_stream_chunk(chunk):
    """格式化流式响应块"""
    if isinstance(chunk, dict):
        # 添加 start/end 标记
        if 'start' not in chunk:
            chunk['start'] = False
        if 'end' not in chunk:
            chunk['end'] = False
        return json.dumps(chunk) + '\n'
```

### 2. 消息转换

```python
def convert_to_interpreter_messages(messages):
    """转换 OpenAI 格式消息到 Interpreter 格式"""
    converted = []
    for msg in messages:
        converted.append({
            "role": msg["role"],
            "type": "message",
            "content": msg["content"]
        })
    return converted
```

## 安全考虑

1. **认证机制**
```python
def verify_api_key():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise Unauthorized("Missing or invalid API key")
```

2. **资源限制**
```python
def check_resource_limits():
    """检查系统资源使用情况"""
    # 实现资源限制逻辑
    pass
```

3. **错误处理**
```python
@app.errorhandler(Exception)
def handle_error(error):
    return jsonify({
        "error": {
            "code": error.__class__.__name__,
            "message": str(error)
        }
    }), getattr(error, 'code', 500)
```

## 最佳实践

1. 使用环境变量管理配置
2. 实现请求日志记录
3. 添加适当的错误处理
4. 实现速率限制
5. 定期清理临时文件
6. 监控系统资源使用

## 部署建议

1. 使用生产级 WSGI 服务器（如 Gunicorn）
2. 启用 HTTPS
3. 设置适当的超时时间
4. 配置错误监控
5. 实现健康检查
6. 使用容器化部署 