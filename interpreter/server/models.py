import threading
from typing import Dict, List, Optional, Literal, Union, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, validator
from datetime import datetime

# Message related schemas
MessageRole = Literal["user", "assistant", "computer"]
MessageType = Literal["message", "code", "image", "console", "file", "confirmation"]
MessageFormat = Literal["output", "path", "base64.png", "base64.jpeg", "python", "javascript", "shell", "html", "active_line", "execution"]

class MessageBase(BaseModel):
    """Base message structure following NCU format"""
    id: str
    role: MessageRole
    type: MessageType
    content: Optional[str] = None
    format: Optional[MessageFormat] = None
    recipient: Optional[Literal["user", "assistant"]] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    start: Optional[bool] = None
    end: Optional[bool] = None

class MessageCreate(BaseModel):
    """Message creation request validation"""
    role: str
    content: str
    type: str = "message"
    format: Optional[str] = None

    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant', 'computer']:
            raise ValueError('Invalid role')
        return v

    @validator('type')
    def validate_type(cls, v):
        valid_types = ['message', 'code', 'image', 'console', 'file', 'confirmation']
        if v not in valid_types:
            raise ValueError('Invalid message type')
        return v

class SessionMetadata(TypedDict, total=False):
    """Session metadata structure"""
    title: str                    
    description: Optional[str]    
    tags: List[str]              
    model: Optional[str]         
    safe_mode: bool              # 移除默认值，TypedDict 不支持
    preview: Optional[str]       
    language: Optional[str]      

class SessionState(TypedDict):
    """Session state tracking"""
    active: bool
    last_active: datetime
    interpreter: Optional[Any]
    lock: threading.Lock

class Session(BaseModel):
    """Session structure"""
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: List[MessageBase] = []
    metadata: SessionMetadata = {}

    class Config:
        from_attributes = True

class SessionUpdate(BaseModel):
    """Session update request validation"""
    metadata: Optional[Dict] = None
    messages: Optional[List[Dict]] = None

    @validator('messages')
    def validate_messages(cls, v):
        if v is not None and not isinstance(v, list):
            raise ValueError('Messages must be a list')
        return v

# API Request/Response models
class SessionCreate(BaseModel):
    """Session creation request"""
    title: Optional[str] = None
    safe_mode: bool = True
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        """将请求数据转换为会话元数据结构，避免嵌套"""
        metadata = self.metadata.copy() if self.metadata else {}
        
        # 添加其他字段到最外层元数据
        if self.title:
            metadata["title"] = self.title
        if self.model:
            metadata["model"] = self.model
        metadata["safe_mode"] = self.safe_mode

        return {"metadata": metadata}

class SessionListResponse(BaseModel):
    """Session list response"""
    sessions: List[Session]
    total: int
    page: int = 1
    limit: int = 20

class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None

# Keep existing Message and Session classes in session.py for now
# We can gradually migrate to these models as needed