# Open Interpreter HTTP Server

Open Interpreter HTTP Server 是一个基于 Flask 的 HTTP 服务，提供了与 Open Interpreter 交互的 REST API 接口。它支持原生的聊天功能以及 OpenAI 兼容的接口，可以轻松集成到各种应用中。

## 功能特点

- 支持 Open Interpreter 原生 API
- 提供 OpenAI 兼容接口
- 支持流式响应
- 会话管理
- 代码执行能力
- 完整的错误处理
- 详细的日志记录

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件并配置以下变量：

```env
LITELLM_MODEL=bedrock/anthropic.claude-3-sonnet-20240229-v1:0
LOG_LEVEL=INFO
API_KEY=your-secret-key
RATE_LIMIT_PER_MINUTE=60
SESSION_RATE_LIMIT_PER_MINUTE=10
MAX_TOKENS=4096
TEMPERATURE=0.7
```

### 启动服务器

```bash
python -m interpreter.server.cli --host 0.0.0.0 --port 5001
```

## API 端点

所有请求需要包含以下 Header：
```http
Authorization: Bearer your-api-key
Content-Type: application/json
```

### 1. 健康检查

```http
GET /v1/health
```

响应示例：
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
}
```

### 2. 会话管理

#### 创建会话
```http
POST /v1/sessions
```

响应示例：
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-02-12T10:00:00Z",
    "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
}
```

#### 获取会话列表
```http
GET /v1/sessions
```

响应示例：
```json
{
    "sessions": [
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2024-02-12T10:00:00Z",
            "message_count": 10
        }
    ]
}
```

#### 获取会话消息
```http
GET /v1/sessions/<session_id>/messages
```

响应示例：
```json
{
    "messages": [
        {
            "role": "user",
            "type": "message",
            "content": "Hello!",
            "created_at": "2024-02-12T10:00:00Z"
        },
        {
            "role": "assistant",
            "type": "message",
            "content": "Hi! How can I help you today?",
            "created_at": "2024-02-12T10:00:01Z"
        }
    ]
}
```

### 3. 聊天接口

#### 原生聊天
```http
POST /v1/chat
Content-Type: application/json

请求体：
{
    "messages": [
        {
            "role": "user",
            "type": "message",
            "content": "Hello!"
        }
    ],
    "session_id": "optional-session-id",
    "stream": false,
    "config": {
        "llm": {
            "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    }
}
```

响应示例：
```json
{
    "message": {
        "role": "assistant",
        "type": "message",
        "content": "Hello! How can I help you today?",
        "created_at": "2024-02-12T10:00:00Z"
    },
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

流式响应格式：
```
event: message
data: {"role": "assistant", "type": "message", "content": "Hello", "created_at": "2024-02-12T10:00:00Z"}

event: message
data: {"role": "assistant", "type": "message", "content": "! How can I ", "created_at": "2024-02-12T10:00:00Z"}

event: message
data: {"role": "assistant", "type": "message", "content": "help you today?", "created_at": "2024-02-12T10:00:00Z"}

event: done
data: {"session_id": "550e8400-e29b-41d4-a716-446655440000"}
```

#### OpenAI 兼容接口
```http
POST /v1/chat/completions
Content-Type: application/json

{
    "messages": [
        {
            "role": "user",
            "content": "Hello!"
        }
    ],
    "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 4096
}
```

响应示例：
```json
{
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "Hello! How can I help you today?"
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 9,
        "completion_tokens": 12,
        "total_tokens": 21
    }
}
```

## 消息格式

### NCU 消息结构

每条消息都包含以下字段：

```python
{
    "role": "user" | "assistant" | "computer",  # 必填，消息发送者角色
    "type": "message" | "code" | "image" | "console" | "file" | "confirmation",  # 必填，消息类型
    "format": "text" | "python" | "javascript" | "shell" | "html" | "path" | "base64.png" | "base64.jpeg",  # 可选，内容格式
    "content": str,  # 必填，消息内容
    "recipient": "user" | "assistant"  # 可选，消息接收者
}
```

## 错误处理

服务器使用标准的 HTTP 状态码和详细的错误消息：

### 常见错误码

- 400: 请求参数错误
- 401: 未授权访问
- 403: 禁止访问
- 404: 资源不存在
- 429: 请求过于频繁
- 500: 服务器内部错误

### 错误响应示例

1. 无效的会话 ID
```json
{
    "error": {
        "message": "Session not found",
        "type": "session_error",
        "code": "session_not_found"
    }
}
```

2. 无效的请求参数
```json
{
    "error": {
        "message": "Invalid message format",
        "type": "validation_error",
        "code": "invalid_message"
    }
}
```

3. 认证失败
```json
{
    "error": {
        "message": "Invalid API key",
        "type": "auth_error",
        "code": "invalid_api_key"
    }
}
```

4. 速率限制
```json
{
    "error": {
        "message": "Too many requests",
        "type": "rate_limit_error",
        "code": "rate_limit_exceeded",
        "retry_after": 60
    }
}
```

## 安全措施

### 认证
- 所有 API 请求必须包含有效的 API Key
- API Key 通过环境变量配置
- 建议定期轮换 API Key

### 速率限制
- 每个 IP 每分钟最多 60 个请求
- 每个会话每分钟最多 10 个请求
- 超出限制将返回 429 状态码
- 响应头包含剩余请求配额信息：
  - X-RateLimit-Limit
  - X-RateLimit-Remaining
  - X-RateLimit-Reset

### 数据安全
- 所有通信必须使用 HTTPS
- 敏感数据在日志中自动脱敏
- 会话数据定期清理
- 代码执行在隔离环境中进行

## 开发指南

### 项目结构

```
interpreter/server/
├── __init__.py
├── app.py           # Flask 应用主文件
├── cli.py          # 命令行接口
├── core/           # 核心功能模块
├── errors.py       # 错误处理
├── session.py      # 会话管理
├── utils.py        # 工具函数
└── logs/           # 日志文件
```

### 运行测试

```bash
python tests/server/test_endpoints.py
```

### 日志配置

日志文件位置：
- 错误日志：`interpreter/server/logs/server_err.log`
- 输出日志：`interpreter/server/logs/server_out.log`

## 部署

### 使用 Supervisor

配置文件示例 (`supervisord.conf`):

```ini
[program:interpreter_server]
directory=/path/to/open-interpreter
command=python -m interpreter.server.cli --host 0.0.0.0 --port 5001
autostart=true
autorestart=true
stderr_logfile=interpreter/server/logs/server_err.log
stdout_logfile=interpreter/server/logs/server_out.log
```

### 环境要求

- Python 3.9+
- Flask
- Waitress (生产环境)
- python-dotenv

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License 