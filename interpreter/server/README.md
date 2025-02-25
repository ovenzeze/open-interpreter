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
SERVER_PORT_PROD=5001
SERVER_PORT_DEV=5002
INTERPRETER_BASE=~/.interpreter
INTERPRETER_HOME=~/.interpreter/.prod
PYTHON_PATH=/path/to/your/python
```

### 启动服务

服务使用 PM2 进行管理，提供了生产环境和开发环境两种配置：

#### 使用脚本启动

```bash
# 启动服务
./server.sh start

# 停止服务
./server.sh stop

# 重启服务
./server.sh restart

# 查看服务状态
./server.sh status
```

#### PM2 直接管理

```bash
# 启动所有服务
pm2 start ecosystem.config.js

# 只启动生产环境
pm2 start ecosystem.config.js --only interpreter-prod

# 只启动开发环境
pm2 start ecosystem.config.js --only interpreter-dev

# 查看服务状态
pm2 status

# 查看日志
pm2 logs interpreter-prod
pm2 logs interpreter-dev
```

### 环境说明

#### 生产环境 (interpreter-prod)
- 端口：5001（可通过 SERVER_PORT_PROD 环境变量配置）
- 日志级别：INFO（可通过 LOG_LEVEL 环境变量配置）
- 日志位置：~/.interpreter/logs/prod/
- 自动重启：启用
- 内存限制：1GB
- 文件监控：禁用

#### 开发环境 (interpreter-dev)
- 端口：5002（可通过 SERVER_PORT_DEV 环境变量配置）
- 日志级别：DEBUG
- 日志位置：~/.interpreter/logs/dev/
- 自动重启：启用
- 内存限制：1GB
- 文件监控：启用（监控 interpreter 目录）
- 忽略监控：logs, tests, *.pyc, __pycache__, .git, node_modules

## API 文档

完整的 API 文档已移至 Postman 配置文件，您可以在 `interpreter/server/api/postman_collection.json` 中找到。要使用这些 API：

1. 下载并安装 [Postman](https://www.postman.com/downloads/)
2. 导入位于 `interpreter/server/api/postman_collection.json` 的配置文件
3. 设置环境变量：
   - `base_url`: 您的服务器地址（默认为 `http://localhost:5001`）
   - `api_key`: 您的 API 密钥

所有请求都需要包含以下 Header：
```http
Authorization: Bearer your-api-key
Content-Type: application/json
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

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License