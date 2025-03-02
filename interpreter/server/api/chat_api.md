# 聊天 API

## 接口说明

聊天API提供了与Open Interpreter进行交互的核心功能。它支持发送用户消息并获取助手响应，包括代码执行结果。API支持流式响应模式，适用于实时展示生成内容的场景，也支持非流式模式获取完整响应。同时提供原生格式和OpenAI兼容格式两种接口。

## 数据结构

### 消息结构

```json
{
  "id": "消息ID，UUID格式",
  "created_at": "消息创建时间，ISO格式字符串",
  "role": "消息角色，如user或assistant",
  "type": "消息类型，默认为message",
  "content": "消息内容"
}
```

## 接口定义

### 1. 原生聊天接口

**请求**

```
POST /v1/chat
```

**请求体**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "消息内容"
    }
  ],
  "stream": false,
  "session_id": "会话ID（可选）",
  "model": "模型名称（可选）"
}
```

**请求参数说明**

| 参数名     | 类型   | 必填 | 默认值 | 描述                                      |
|-----------|-------|------|-------|-------------------------------------------|
| messages  | array | 是   | -     | 消息数组，包含用户提问和上下文历史           |
| stream    | bool  | 否   | false | 是否使用流式响应                            |
| session_id| string| 否   | null  | 会话ID，不提供时会创建新会话                |
| model     | string| 否   | null  | 使用的模型名称，不提供时使用系统默认配置     |

**响应（非流式）**

```json
{
  "message": {
    "id": "消息ID",
    "created_at": "创建时间",
    "role": "assistant",
    "content": "助手响应内容",
    "execution": {
      "logs": ["代码执行日志"],
      "outputs": ["代码执行输出"]
    }
  },
  "session_id": "会话ID"
}
```

**响应（流式）**

每个流式响应块的格式：

```
data: {"type":"message","content":"响应内容片段"}

data: {"type":"code","language":"python","content":"代码片段"}

data: {"type":"execution","logs":"代码执行日志"}

data: {"type":"output","output":"代码执行输出"}

data: {"type":"end"}
```

### 2. OpenAI兼容接口

**请求**

```
POST /v1/chat/completions
```

**请求体**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "消息内容"
    }
  ],
  "stream": false,
  "model": "模型名称（可选）",
  "session_id": "会话ID（可选）"
}
```

**请求参数说明**

| 参数名     | 类型   | 必填 | 默认值 | 描述                                      |
|-----------|-------|------|-------|-------------------------------------------|
| messages  | array | 是   | -     | OpenAI格式的消息数组                        |
| stream    | bool  | 否   | false | 是否使用流式响应                            |
| model     | string| 否   | null  | 使用的模型名称                             |
| session_id| string| 否   | null  | 会话ID，不提供时会创建新会话                |

**响应（非流式）**

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "interpreter-3.5",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 28,
    "total_tokens": 43
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "助手响应内容，包含代码执行结果"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ]
}
```

**响应（流式）**

每个流式响应块的格式：

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"interpreter-3.5","choices":[{"delta":{"role":"assistant"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"interpreter-3.5","choices":[{"delta":{"content":"响应内容片段"},"index":0,"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"interpreter-3.5","choices":[{"delta":{},"index":0,"finish_reason":"stop"}]}

data: [DONE]
```

## 使用示例

### 1. 使用原生接口发送非流式请求

**请求**

```bash
curl -X POST http://localhost:5002/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "计算1+1等于多少"
      }
    ],
    "stream": false
  }'
```

**响应**

```json
{
  "message": {
    "id": "msg_123abc",
    "created_at": "2024-03-01T10:15:23.456Z",
    "role": "assistant",
    "content": "1+1等于2。",
    "execution": {
      "logs": ["计算1+1"],
      "outputs": ["2"]
    }
  },
  "session_id": "sess_xyz789"
}
```

### 2. 使用原生接口发送流式请求

**请求**

```bash
curl -X POST http://localhost:5002/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "用Python计算斐波那契数列的前10个数"
      }
    ],
    "stream": true
  }'
```

**响应流**

```
data: {"type":"message","content":"我会用Python计算斐波那契数列的前10个数。"}

data: {"type":"code","language":"python","content":"def fibonacci(n):\n    fib = [0, 1]\n    for i in range(2, n):\n        fib.append(fib[i-1] + fib[i-2])\n    return fib\n\nprint(fibonacci(10))"}

data: {"type":"execution","logs":"执行Python代码..."}

data: {"type":"output","output":"[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]"}

data: {"type":"message","content":"以上是斐波那契数列的前10个数：0, 1, 1, 2, 3, 5, 8, 13, 21, 34"}

data: {"type":"end"}
```

### 3. 使用OpenAI兼容接口

**请求**

```bash
curl -X POST http://localhost:5002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "使用Python计算圆周率"
      }
    ],
    "model": "interpreter-3.5"
  }'
```

**响应**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677858242,
  "model": "interpreter-3.5",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 42,
    "total_tokens": 54
  },
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "我可以使用Python的math模块计算圆周率，或者使用近似计算方法。\n\n```python\nimport math\nprint(math.pi)\n\n# 或者使用莱布尼茨公式近似计算\ndef calculate_pi(n_terms):\n    pi = 0\n    for i in range(n_terms):\n        pi += (-1)**i / (2*i + 1)\n    return 4 * pi\n\nprint(calculate_pi(1000))\n```\n\n运行结果：\n3.141592653589793\n3.1425916543395442"
      },
      "finish_reason": "stop",
      "index": 0
    }
  ]
}
```

## 错误处理

| 状态码 | 错误类型              | 描述                             |
|-------|---------------------|----------------------------------|
| 400   | Invalid request     | 请求参数错误                       |
| 404   | Session not found   | 指定的会话不存在                   |
| 409   | Session busy        | 会话正在处理其他请求                |
| 500   | Server error        | 服务器内部错误                     |

## 实现细节

- 聊天接口支持代码执行，可以运行用户提供的代码并返回执行结果
- 流式响应模式适用于实时展示生成内容的场景，包括文本生成、代码生成和代码执行过程
- 支持会话管理，可以在多次请求之间保持上下文连续性
- OpenAI兼容接口使得现有基于OpenAI API的应用可以直接切换到Open Interpreter
- 处理请求时自动进行安全性检查，确保代码执行安全 