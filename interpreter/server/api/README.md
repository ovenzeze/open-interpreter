# Open Interpreter API 文档

本文档描述了 Open Interpreter HTTP Server 的 API 接口。完整的 Postman 配置文件可在 `postman_collection.json` 中找到。

## 基础信息

- 基础 URL: `http://localhost:5001`
- 认证方式: Bearer Token
- 内容类型: `application/json`

## 认证

所有请求都需要包含以下 Header：
```http
Authorization: Bearer your-api-key
Content-Type: application/json
```

## API 端点

### 健康检查

```http
GET /v1/health
```

响应示例：
```json
{
    "llm": {
        "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        "status": "ready"
    },
    "status": "healthy",
    "version": "0.4.3"
}
```

### 会话管理

#### 创建会话

```http
POST /v1/sessions
```

响应示例：
```json
{
    "created_at": "2025-02-16T17:10:28.301493",
    "session_id": "6534e54b-7261-4526-9325-11feb682040e"
}
```

#### 获取会话列表

```http
GET /v1/sessions
```

#### 获取会话消息

```http
GET /v1/sessions/{session_id}/messages
```

### 聊天接口

#### 原生聊天

```http
POST /v1/chat
```

请求体示例：
```json
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

#### OpenAI 兼容聊天

```http
POST /v1/chat/completions
```

请求体示例：
```json
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

## 流式响应

所有聊天接口都支持流式响应，只需将 `stream` 参数设置为 `true`。流式响应使用 Server-Sent Events (SSE) 格式。

## 错误处理

服务器使用标准的 HTTP 状态码：

- 400: 请求参数错误
- 401: 未授权访问
- 403: 禁止访问
- 404: 资源不存在
- 429: 请求过于频繁
- 500: 服务器内部错误

## 速率限制

- 每个 IP 每分钟最多 60 个请求
- 每个会话每分钟最多 10 个请求

响应头包含以下信息：
- X-RateLimit-Limit
- X-RateLimit-Remaining
- X-RateLimit-Reset