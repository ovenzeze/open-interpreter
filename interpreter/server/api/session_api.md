# 会话管理 API

## 数据结构

### 会话数据结构

```json
{
  "session_id": "唯一会话ID，UUID格式",
  "created_at": "会话创建时间，ISO格式字符串",
  "last_active": "最后活动时间，ISO格式字符串",
  "messages": [
    {
      "id": "消息ID，UUID格式",
      "created_at": "消息创建时间，ISO格式字符串",
      "role": "消息角色，如user或assistant",
      "type": "消息类型，默认为message",
      "content": "消息内容"
    }
  ],
  "metadata": {
    "title": "会话标题",
    "description": "会话描述",
    "tags": ["标签1", "标签2"],
    "model": "使用的模型",
    "safe_mode": true,
    "preview": "预览内容",
    "language": "主要编程语言",
    "is_starred": false,
    "status": "会话状态(active/archived/deleted)",
    "turn_count": 0,
    "category": "会话分类",
    "last_modified": "最后修改时间，ISO格式字符串",
    "context_window": 0,
    "max_tokens": 0
  }
}
```

## 接口列表

### 1. 获取会话列表

**请求**

```
GET /v1/sessions
```

**查询参数**

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|------|------|-------|------|
| page  | int  | 否   | 1     | 页码，从1开始  |
| limit | int  | 否   | 20    | 每页数量，最大100 |

**响应**

```json
{
  "sessions": [
    {
      // 会话数据结构
    }
  ],
  "total": 100,  // 总会话数
  "page": 1,     // 当前页码
  "limit": 20    // 每页数量
}
```

**说明**

- 只返回有效的会话（未过期的会话）
- 会话按最后活动时间倒序排列
- 分页参数会自动调整：page最小为1，limit范围为1-100

### 2. 创建会话

**请求**

```
POST /v1/sessions
```

**请求体**

```json
{
  "title": "会话标题（可选）",
  "safe_mode": true,
  "model": "使用的模型（可选）",
  "metadata": {
    // 其他元数据（可选）
  }
}
```

**响应**

```json
{
  // 会话数据结构
}
```

### 3. 获取单个会话

**请求**

```
GET /v1/sessions/{session_id}
```

**响应**

```json
{
  // 会话数据结构
}
```

### 4. 更新会话

**请求**

```
PATCH /v1/sessions/{session_id}
```

**请求体**

```json
{
  "metadata": {
    // 需要更新的元数据字段
  }
}
```

**响应**

```json
{
  // 更新后的会话数据结构
}
```

### 5. 删除会话

**请求**

```
DELETE /v1/sessions/{session_id}
```

**响应**

```json
{
  "success": true
}
```

### 6. 添加消息到会话

**请求**

```
POST /v1/sessions/{session_id}/messages
```

**请求体**

```json
{
  "role": "user或assistant",
  "content": "消息内容"
}
```

**响应**

```json
{
  "success": true,
  "session": {
    // 更新后的会话数据结构
  }
}
```

### 7. 加载历史会话

**请求**

```
POST /v1/sessions/{session_id}/load
```

**请求体**

```json
{
  "messages": [
    {
      "role": "user或assistant",
      "content": "消息内容"
    }
  ]
}
```

**响应**

```json
{
  "success": true
}
```

### 8. 导出会话数据

**请求**

```
GET /v1/sessions/{session_id}/export
```

**响应**

```json
{
  // 完整的会话数据结构，包含所有原始字段
}
``` 