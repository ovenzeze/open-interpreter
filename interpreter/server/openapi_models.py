"""
OpenAPI 响应模型定义，基于现有的 models.py
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ OpenAI Compatible Models ============

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(
        ..., 
        description="消息角色: user, assistant, system",
        json_schema_extra={"example": "user"}
    )
    content: str = Field(
        ..., 
        description="消息内容",
        json_schema_extra={"example": "Hello, how are you?"}
    )
    type: Optional[str] = Field(
        "message", 
        description="消息类型",
        json_schema_extra={"example": "message"}
    )


class ChatCompletionRequest(BaseModel):
    """聊天完成请求"""
    messages: List[ChatMessage] = Field(
        ..., 
        description="消息列表",
        json_schema_extra={"example": [{"role": "user", "content": "Hello, can you help me?"}]}
    )
    model: Optional[str] = Field(
        None, 
        description="模型名称 (可选，默认使用服务器配置)",
        json_schema_extra={"example": "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0"}
    )
    stream: Optional[bool] = Field(
        False, 
        description="是否流式响应",
        json_schema_extra={"example": False}
    )
    session_id: Optional[str] = Field(
        None, 
        description="会话ID (可选，用于保持对话上下文)",
        json_schema_extra={"example": "session-123"}
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Hello, can you help me write a Python function?"}
                ],
                "model": "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
                "stream": False,
                "session_id": None
            }
        }


class ChatCompletionChoice(BaseModel):
    """聊天完成选项"""
    index: int = Field(0, description="选项索引")
    message: ChatMessage = Field(..., description="响应消息")
    finish_reason: str = Field("stop", description="结束原因")


class Usage(BaseModel):
    """Token使用情况"""
    prompt_tokens: int = Field(0, description="提示词token数")
    completion_tokens: int = Field(0, description="完成token数") 
    total_tokens: int = Field(0, description="总token数")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应"""
    id: str = Field(..., description="响应ID")
    object: str = Field("chat.completion", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    model: str = Field(..., description="使用的模型")
    choices: List[ChatCompletionChoice] = Field(..., description="响应选项列表")
    usage: Usage = Field(..., description="Token使用情况")


class ModelObject(BaseModel):
    """模型对象"""
    id: str = Field(..., description="模型ID")
    object: str = Field("model", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    owned_by: str = Field(..., description="所有者")


class ModelListResponse(BaseModel):
    """模型列表响应"""
    object: str = Field("list", description="对象类型")
    data: List[ModelObject] = Field(..., description="模型列表")

class EngineObject(BaseModel):
    """引擎对象"""
    id: str = Field(..., description="引擎ID")
    object: str = Field("engine", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    owner: str = Field(..., description="所有者")
    ready: bool = Field(True, description="是否就绪")

class EngineListResponse(BaseModel):
    """引擎列表响应"""
    object: str = Field("list", description="对象类型")
    data: List[EngineObject] = Field(..., description="引擎列表")

# ============ Health Check Models ============

class LLMHealthInfo(BaseModel):
    """LLM 健康信息"""
    model: str = Field(..., description="LLM 模型名称", json_schema_extra={"example": "gpt-3.5-turbo"})
    status: str = Field(..., description="LLM 状态", json_schema_extra={"example": "ready"})
    error: Optional[str] = Field(None, description="错误信息 (如果存在)")

class InstanceHealthCounts(BaseModel):
    """实例状态计数"""
    busy: int = Field(0, description="忙碌实例数量")
    ready: int = Field(0, description="就绪实例数量")
    optimization: int = Field(0, description="优化中实例数量")

class InstanceHealthInfo(BaseModel):
    """实例健康信息"""
    max: int = Field(..., description="最大实例数")
    active: int = Field(..., description="活跃实例数")
    status: str = Field(..., description="实例管理器状态", json_schema_extra={"example": "available"})
    status_counts: Optional[InstanceHealthCounts] = Field(None, description="实例详细状态计数")
    is_optimizing: Optional[bool] = Field(None, description="是否正在优化")
    error: Optional[str] = Field(None, description="错误信息 (如果存在)")

class SystemMemoryInfo(BaseModel):
    """系统内存信息"""
    total: str = Field(..., description="总内存大小")
    available: str = Field(..., description="可用内存大小")
    percent: float = Field(..., description="内存使用百分比")

class SystemDiskInfo(BaseModel):
    """系统磁盘信息"""
    total: str = Field(..., description="总磁盘大小")
    used: str = Field(..., description="已使用磁盘大小")
    free: str = Field(..., description="空闲磁盘大小")
    percent: float = Field(..., description="磁盘使用百分比")

class SystemInfo(BaseModel):
    """系统详细信息"""
    os: str = Field(..., description="操作系统")
    cpu_cores: int = Field(..., description="CPU 核心数")
    memory: SystemMemoryInfo = Field(..., description="内存信息")
    disk: SystemDiskInfo = Field(..., description="磁盘信息")

class HealthCheckResponse(BaseModel):
    """基础健康检查响应"""
    status: str = Field(..., description="服务状态", json_schema_extra={"example": "healthy"})
    version: str = Field(..., description="服务版本", json_schema_extra={"example": "1.0.0"})
    uptime: str = Field(..., description="服务运行时间", json_schema_extra={"example": "1d 2h 30m"})
    llm: LLMHealthInfo = Field(..., description="LLM 健康信息")
    instances: InstanceHealthInfo = Field(..., description="实例健康信息")

class FullHealthCheckResponse(HealthCheckResponse):
    """完整健康检查响应 (包含系统信息)"""
    system: Optional[SystemInfo] = Field(None, description="系统详细信息 (当 detail='full' 时)")

# ============ Session Management Models ============
class AddMessageRequest(BaseModel):
    """添加消息请求"""
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    type: str = Field("message", description="消息类型")
    format: Optional[str] = Field(None, description="消息格式")

class MessageMeta(BaseModel):
    """会话中的消息元数据"""
    id: str
    role: str
    type: str
    content: Optional[str] = None
    format: Optional[str] = None
    recipient: Optional[str] = None
    created_at: str
    start: Optional[bool] = None
    end: Optional[bool] = None

class SessionMeta(BaseModel):
    """会话的元数据部分"""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    model: Optional[str] = None
    safe_mode: Optional[bool] = None
    preview: Optional[str] = None
    language: Optional[str] = None
    is_starred: Optional[bool] = None
    status: Optional[str] = None
    turn_count: Optional[int] = None
    category: Optional[str] = None
    last_modified: Optional[str] = None
    modified_by: Optional[str] = None
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None

class SessionFull(BaseModel):
    """一个完整的会话对象"""
    session_id: str
    created_at: str
    last_active: str
    messages: List[MessageMeta]
    metadata: SessionMeta

class AddMessageResponse(BaseModel):
    """添加消息响应"""
    success: bool = Field(True, description="操作是否成功")
    session: SessionFull = Field(..., description="更新后的会话对象")

class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool = Field(True, description="操作是否成功")

class LoadSessionRequest(BaseModel):
    """加载会话历史请求"""
    messages: List[Dict[str, Any]] = Field(..., description="要加载的消息列表")

class MessagesListResponse(BaseModel):
    """消息列表响应"""
    messages: List[MessageMeta] = Field(..., description="消息列表")
    total: int = Field(..., description="消息总数")
