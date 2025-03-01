# 标题生成 API

## 接口说明

标题生成API提供基于会话内容自动生成标题和其他元数据的功能。该接口使用Google Gemini API进行生成，可以根据会话中的消息内容生成相关的标题、描述、标签等元数据。

## 接口定义

### 生成会话元数据

**请求**

```
POST /v1/sessions/{session_id}/generate-title
```

**路径参数**

| 参数名     | 类型   | 必填 | 描述       |
|-----------|-------|------|-----------|
| session_id | string | 是   | 会话ID     |

**请求体**

```json
{
  "prompt": "自定义提示词，用于指导元数据生成（可选）",
  "fields": ["title", "description", "tags", "category", "language", "preview"]
}
```

**请求参数说明**

| 参数名  | 类型   | 必填 | 默认值 | 描述                                                |
|--------|-------|------|-------|---------------------------------------------------|
| prompt | string | 否   | ""    | 自定义提示词，用于指导元数据生成                        |
| fields | array  | 否   | ["title"] | 需要生成的元数据字段列表                           |

**fields 可选值**

- `title`: 会话标题
- `description`: 会话描述
- `tags`: 相关标签（返回数组）
- `category`: 会话分类
- `language`: 会话使用的主要语言
- `preview`: 会话内容预览

**响应**

```json
{
  "metadata": {
    "title": "生成的标题",
    "description": "生成的描述（如果请求中包含）",
    "tags": ["标签1", "标签2", "标签3"]（如果请求中包含）,
    "category": "生成的分类（如果请求中包含）",
    "language": "检测到的语言（如果请求中包含）",
    "preview": "生成的预览（如果请求中包含）"
  },
  "session": {
    // 完整的会话数据，包含更新后的元数据
    "session_id": "会话ID",
    "created_at": "创建时间",
    "last_active": "最后活动时间",
    "messages": [],
    "metadata": {
      // 包含更新后的元数据
    }
  }
}
```

**错误响应**

| 状态码 | 错误类型              | 描述                           |
|-------|---------------------|--------------------------------|
| 404   | Session not found   | 指定的会话不存在                  |
| 400   | No messages in session | 会话中没有消息，无法生成元数据    |
| 500   | Failed to generate metadata | 元数据生成失败             |

## 使用示例

### 1. 只生成标题

**请求**

```bash
curl -X POST http://localhost:5002/v1/sessions/{session_id}/generate-title \
  -H "Content-Type: application/json" \
  -d '{}'
```

**响应**

```json
{
  "metadata": {
    "title": "技术讨论：Python异步编程"
  },
  "session": {
    // 完整的会话数据
  }
}
```

### 2. 生成多个元数据字段

**请求**

```bash
curl -X POST http://localhost:5002/v1/sessions/{session_id}/generate-title \
  -H "Content-Type: application/json" \
  -d '{"fields": ["title", "description", "tags", "category", "language"]}'
```

**响应**

```json
{
  "metadata": {
    "title": "Python异步编程探讨",
    "description": "关于Python中asyncio库和异步编程模式的技术讨论",
    "tags": ["Python", "asyncio", "异步编程", "协程"],
    "category": "技术讨论",
    "language": "中文"
  },
  "session": {
    // 完整的会话数据
  }
}
```

### 3. 使用自定义提示生成元数据

**请求**

```bash
curl -X POST http://localhost:5002/v1/sessions/{session_id}/generate-title \
  -H "Content-Type: application/json" \
  -d '{"fields": ["title", "description"], "prompt": "请生成英文标题和描述，标题需要包含emoji"}'
```

**响应**

```json
{
  "metadata": {
    "title": "Python Async Programming 🚀",
    "description": "A technical discussion about asyncio library and asynchronous programming patterns in Python"
  },
  "session": {
    // 完整的会话数据
  }
}
```

## 实现细节

- 接口会从会话中获取最多10条消息用于生成元数据
- 使用Google Gemini 2.0 Flash模型进行生成
- 支持自定义提示词，可以指定生成的语言、风格等
- 生成的元数据会自动更新到会话的metadata字段中
- 返回的session字段包含完整的会话数据，包括更新后的元数据 