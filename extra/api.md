# Open Interpreter HTTP API Documentation

## Overview

This document describes the HTTP API for Open Interpreter, which provides both native functionality and OpenAI-compatible interfaces.

## Base Configuration

The API configuration is defined in [api.json](./api.json).

- Base URL: `http://localhost:5001`
- API Version: `v1`
- Authentication: Bearer token
- Content Type: `application/json`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:5001` |
| `api_key` | Authentication token | `your-api-key` |

## Endpoints

### 1. Native Chat (`/v1/chat`)

Provides direct access to Open Interpreter's chat functionality with code execution capabilities.

#### Request

```http
POST {{base_url}}/v1/chat
Content-Type: application/json
Authorization: Bearer {{api_key}}
```

```json
{
  "messages": [
    {
      "role": "user",
      "type": "message",
      "content": "Write a Python function to calculate fibonacci numbers"
    }
  ],
  "stream": true,
  "auto_run": true,
  "config": {
    "llm": {
      "model": "bedrock/anthropic.claude-3-sonnet",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }
}
```

#### Response

```json
{
  "messages": [
    {
      "role": "assistant",
      "type": "message",
      "content": "I'll help you write a Python function to calculate Fibonacci numbers."
    },
    {
      "role": "assistant",
      "type": "code",
      "format": "python",
      "content": "def fibonacci(n):\n    if n <= 0:\n        return []\n    elif n == 1:\n        return [0]\n    elif n == 2:\n        return [0, 1]\n    \n    fib = [0, 1]\n    for i in range(2, n):\n        fib.append(fib[i-1] + fib[i-2])\n    return fib\n\n# Test the function\nprint(fibonacci(10))"
    },
    {
      "role": "computer",
      "type": "console",
      "format": "output",
      "content": "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"
    }
  ]
}
```

### 2. OpenAI Compatible (`/v1/chat/completions`)

Provides OpenAI-compatible interface for easy integration with existing applications.

#### Request

```http
POST {{base_url}}/v1/chat/completions
Content-Type: application/json
Authorization: Bearer {{api_key}}
```

```json
{
  "model": "bedrock/anthropic.claude-3-sonnet",
  "messages": [
    {
      "role": "user",
      "content": "Write a Python function to calculate fibonacci numbers"
    }
  ],
  "stream": true,
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 3. System Health (`/v1/health`)

Provides system health and status information.

#### Request

```http
GET {{base_url}}/v1/health
```

#### Response

```json
{
  "status": "healthy",
  "version": "0.4.3",
  "llm": {
    "model": "bedrock/anthropic.claude-3-sonnet",
    "status": "ready"
  }
}
```

## Message Types

All messages share these common fields:
- `role`: "user", "assistant", or "computer"
- `type`: Specifies the type of content
- `recipient`: (Optional) "user" or "assistant", specifies who should receive the message

### 1. User Message
```json
{
  "role": "user",
  "type": "message",
  "content": "string"
}
```

### 2. Assistant Message
```json
{
  "role": "assistant",
  "type": "message",
  "content": "string"
}
```

### 3. Code Message
```json
{
  "role": "assistant",
  "type": "code",
  "format": "python",
  "content": "string"
}
```

### 4. Computer Output
```json
{
  "role": "computer",
  "type": "console",
  "format": "output",
  "content": "string"
}
```

### 5. Image Message
```json
{
  "role": "user",
  "type": "image",
  "format": "path",
  "content": "path/to/image.png"
}
```

### 6. File Message
```json
{
  "role": "user",
  "type": "file",
  "content": "/path/to/file.pdf"
}
```

## Streaming Response Format

When `stream: true`, the response will be a series of server-sent events. Each chunk includes `start` and `end` boolean fields to indicate the beginning and end of a message:

```jsonl
{"role": "assistant", "type": "message", "start": true}
{"role": "assistant", "type": "message", "content": "partial response"}
{"role": "assistant", "type": "message", "end": true}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

## Testing

You can import the [api.json](./api.json) file into Postman or similar tools for testing. The collection includes example requests and responses for all endpoints.

## Security Considerations

1. Always use HTTPS in production
2. Keep your API key secure
3. Set appropriate rate limits
4. Monitor code execution resources
5. Implement proper authentication and authorization 