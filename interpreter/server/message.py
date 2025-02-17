"""
NCU (New Computer Update) Message Structure Definitions
"""

from typing import Union, Literal, Dict, Optional
from datetime import datetime
import uuid

# Type definitions
MessageRole = Literal["user", "assistant", "computer"]
MessageType = Literal["message", "code", "image", "console", "file", "confirmation"]
MessageFormat = Literal["output", "path", "base64.png", "base64.jpeg", "python", "javascript", "shell", "html", "active_line", "execution"]
MessageRecipient = Literal["user", "assistant"]

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
        self.role = role
        self.type = type
        self.content = content
        self.format = format
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

    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create message from dictionary"""
        return cls(
            role=data["role"],
            type=data["type"],
            content=data.get("content", ""),
            format=data.get("format"),
            recipient=data.get("recipient"),
            id=data.get("id"),
            created_at=data.get("created_at")
        )

    def validate(self) -> bool:
        """Validate message format"""
        # Basic validation
        if not all(hasattr(self, attr) for attr in ['role', 'type', 'content']):
            return False
        
        # Role validation
        if self.role not in ["user", "assistant", "computer"]:
            return False
            
        # Type validation
        if self.type not in ["message", "code", "image", "console", "file", "confirmation"]:
            return False
            
        # Format validation if present
        if self.format and self.format not in [
            "output", "path", "base64.png", "base64.jpeg", "python", 
            "javascript", "shell", "html", "active_line", "execution"
        ]:
            return False
            
        # Recipient validation if present
        if self.recipient and self.recipient not in ["user", "assistant"]:
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