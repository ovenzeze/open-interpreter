"""
NCU (New Computer Update) Message Structure Definitions
"""

from typing import Union, Literal, Dict, Optional, Any, cast
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Type definitions - 扩展支持的角色和类型，使得处理更灵活
MessageRole = Union[Literal["user", "assistant", "computer"], str]
MessageType = Union[Literal["message", "code", "image", "console", "file", "confirmation"], str]
MessageFormat = Union[Literal["output", "path", "base64.png", "base64.jpeg", "python", "javascript", "shell", "html", "active_line", "execution"], str]
MessageRecipient = Union[Literal["user", "assistant"], str]

# 有效角色列表
VALID_ROLES = ["user", "assistant", "computer"]
# 有效类型列表
VALID_TYPES = ["message", "code", "image", "console", "file", "confirmation"]
# 有效格式列表
VALID_FORMATS = ["output", "path", "base64.png", "base64.jpeg", "python", "javascript", "shell", "html", "active_line", "execution"]
# 有效接收者列表
VALID_RECIPIENTS = ["user", "assistant"]

class Message:
    """NCU Message Structure"""
    def __init__(
        self,
        role: MessageRole,
        type: MessageType,
        content: Union[str, Dict[str, str]],
        format: Optional[MessageFormat] = None,
        recipient: Optional[MessageRecipient] = None,
        id: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        # 验证并修正角色
        if role not in VALID_ROLES:
            logger.warning(f"Invalid role: {role}, defaulting to 'user'")
            self.role = "user"
        else:
            self.role = role
            
        # 验证并修正类型    
        if type not in VALID_TYPES:
            logger.warning(f"Invalid type: {type}, defaulting to 'message'")
            self.type = "message"
        else:
            self.type = type
            
        self.content = content
        
        # 验证并修正格式
        if format is not None and format not in VALID_FORMATS:
            logger.warning(f"Invalid format: {format}, setting to None")
            self.format = None
        else:
            self.format = format
            
        # 验证并修正接收者
        if recipient is not None and recipient not in VALID_RECIPIENTS:
            logger.warning(f"Invalid recipient: {recipient}, setting to None")
            self.recipient = None
        else:
            self.recipient = recipient
            
        self.id = id or str(uuid.uuid4())
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert message to dictionary format"""
        message = {
            "role": self.role,
            "type": self.type,
            "content": self.content,
            "id": self.id,
            "created_at": self.created_at
        }
        if self.format:
            message["format"] = self.format
        if self.recipient:
            message["recipient"] = self.recipient
        return message

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute value with default"""
        return getattr(self, key, default)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        # 确保角色值有效
        role = data.get("role", "user")
        if role not in VALID_ROLES:
            # 针对OpenAI兼容格式的特殊处理
            if role == "system":
                logger.warning(f"Converting 'system' role to 'assistant'")
                role = "assistant"
            elif role in ["function", "tool", "developer"]:
                logger.warning(f"Converting '{role}' role to 'computer'")
                role = "computer"
            else:
                logger.warning(f"Invalid role '{role}', defaulting to 'user'")
                role = "user"
        
        # 确保消息类型有效
        msg_type = data.get("type", "message")
        if msg_type not in VALID_TYPES:
            logger.warning(f"Invalid message type '{msg_type}', defaulting to 'message'")
            msg_type = "message"
            
        return cls(
            role=role,
            type=msg_type,
            content=data.get("content", ""),
            format=data.get("format"),
            recipient=data.get("recipient"),
            created_at=data.get("created_at"),
            id=data.get("id")
        )

    def validate(self) -> bool:
        """Validate message format"""
        # Basic validation
        if not all(hasattr(self, attr) for attr in ['role', 'type', 'content']):
            return False
        
        # Role validation
        if self.role not in VALID_ROLES:
            return False
            
        # Type validation
        if self.type not in VALID_TYPES:
            return False
            
        # Format validation if present
        if self.format and self.format not in VALID_FORMATS:
            return False
            
        # Recipient validation if present
        if self.recipient and self.recipient not in VALID_RECIPIENTS:
            return False
            
        return True

class StreamingChunk(Message):
    """NCU Streaming Chunk Structure"""
    def __init__(
        self,
        role: MessageRole,
        type: MessageType,
        content: Union[str, Dict[str, str]] = "",
        format: Optional[MessageFormat] = None,
        recipient: Optional[MessageRecipient] = None,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
        start: bool = False,
        end: bool = False
    ):
        super().__init__(
            role=role,
            type=type,
            content=content,
            format=format,
            recipient=recipient,
            id=id,
            created_at=created_at
        )
        self.start = start
        self.end = end

    def to_dict(self) -> Dict:
        """Convert streaming chunk to dictionary format"""
        chunk = super().to_dict()
        if self.start:
            chunk["start"] = True
        if self.end:
            chunk["end"] = True
        return chunk

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamingChunk':
        """Create streaming chunk from dictionary"""
        return cls(
            role=data.get("role", "user"),
            type=data.get("type", "message"),
            content=data.get("content", ""),
            format=data.get("format"),
            recipient=data.get("recipient"),
            created_at=data.get("created_at"),
            id=data.get("id"),
            start=data.get("start", False),
            end=data.get("end", False)
        ) 