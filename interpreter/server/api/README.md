# Open Interpreter API 文档

本目录包含Open Interpreter服务端API的定义文档和示例。这些文档描述了服务端提供的各种接口，包括数据结构、请求参数、响应格式等详细信息。

## 文档列表

- [会话管理 API](./session_api.md) - 会话创建、获取、更新、删除等操作的接口定义
- [标题生成 API](./title_generator_api.md) - 基于会话内容自动生成标题和元数据的接口定义
- [OpenAPI规范](./open_interpreter.json) - 符合OpenAPI规范的API定义文件
- [Postman集合](./collection.json) - 可导入Postman的API集合

## 使用说明

### 服务端API基本信息

- 基础URL: `http://localhost:5002`
- API版本: v1
- 内容类型: `application/json`

### 认证

目前API不需要认证即可访问。在生产环境中，建议配置适当的认证机制。

### 错误处理

所有API在发生错误时会返回标准的错误响应格式：

```json
{
  "error": "错误描述信息",
  "code": "错误代码（可选）",
  "details": "详细错误信息（可选）"
}
```

常见HTTP状态码：

- 200: 请求成功
- 201: 资源创建成功
- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误

## 开发指南

如需添加新的API文档，请遵循以下格式：

1. 创建一个新的Markdown文件，命名为`{功能名称}_api.md`
2. 文档应包含以下部分：
   - 接口说明
   - 请求/响应格式
   - 参数说明
   - 示例
   - 错误处理

## 更新日志

- 2024-03-01: 添加标题生成API文档
- 2024-02-25: 更新OpenAPI规范文件
- 2024-02-17: 初始版本