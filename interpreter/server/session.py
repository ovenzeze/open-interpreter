"""
Session management for Open Interpreter HTTP Server
Following NCU (New Computer Update) message format
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal, Union, Tuple

import platformdirs
import os
import time
import threading

MessageRole = Literal["user", "assistant", "computer"]
MessageType = Literal["message", "code", "image", "console", "file", "confirmation"]
MessageFormat = Literal["output", "path", "base64.png", "base64.jpeg", "python", "javascript", "shell", "html", "active_line", "execution"]
MessageRecipient = Literal["user", "assistant"]

def get_storage_path(subdirectory=None):
    """Get the storage path for Open Interpreter"""
    config_dir = platformdirs.user_config_dir("open-interpreter")
    if subdirectory is None:
        return config_dir
    return os.path.join(config_dir, subdirectory)

class Message:
    """Represents a message following NCU format"""
    def __init__(
        self,
        role: str,
        type: str,
        content: str = None,
        format: str = None,
        recipient: str = None,
        created_at: str = None,
        id: str = None,
        start: bool = None,
        end: bool = None
    ):
        self.role = role
        self.type = type
        self.content = content
        self.format = format
        self.recipient = recipient
        self.created_at = created_at or datetime.now().isoformat()
        self.id = id or str(uuid.uuid4())
        self.start = start
        self.end = end

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = {
            "id": self.id,
            "role": self.role,
            "type": self.type,
            "created_at": self.created_at
        }
        if self.content is not None:
            data["content"] = self.content
        if self.format is not None:
            data["format"] = self.format
        if self.recipient is not None:
            data["recipient"] = self.recipient
        if self.start is not None:
            data["start"] = self.start
        if self.end is not None:
            data["end"] = self.end
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            role=data["role"],
            type=data["type"],
            content=data.get("content"),
            format=data.get("format"),
            recipient=data.get("recipient"),
            created_at=data.get("created_at"),
            id=data.get("id"),
            start=data.get("start"),
            end=data.get("end")
        )

class Session:
    """Represents a chat session with NCU message format"""
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[Message] = []
        self.created_at = datetime.now().isoformat()
        self.last_active = self.created_at
        self.metadata: Dict[str, Any] = {}

    def add_message(self, message: Union[Message, Dict[str, Any]]) -> None:
        """Add a message to the session"""
        if isinstance(message, dict):
            message = Message.from_dict(message)
        self.messages.append(message)
        self.last_active = datetime.now().isoformat()

    def get_context(self, max_messages: int = None) -> List[Message]:
        """Get conversation context, optionally limited to last N messages"""
        if max_messages:
            return self.messages[-max_messages:]
        return self.messages

    def get_last_code_execution(self) -> Optional[Dict[str, Any]]:
        """Get the last code execution context"""
        for msg in reversed(self.messages):
            if msg.type == "code":
                execution_context = {
                    "code": msg.content,
                    "language": msg.format,
                    "result": None
                }
                # 查找对应的执行结果
                for result in reversed(self.messages):
                    if result.role == "computer" and result.type == "console":
                        execution_context["result"] = result.content
                        break
                return execution_context
        return None

    def validate_message_sequence(self) -> bool:
        """验证消息序列是否符合规范"""
        if not self.messages:
            return True
            
        for i, msg in enumerate(self.messages):
            # 验证基本字段
            if not all(hasattr(msg, field) for field in ["role", "type"]):
                return False
                
            # 验证角色和类型的组合
            valid_types = {
                "user": ["message", "file", "image"],
                "assistant": ["message", "code"],
                "computer": ["console", "confirmation", "image"]
            }
            
            if msg.role not in valid_types or msg.type not in valid_types[msg.role]:
                return False
                
            # 验证格式字段
            if msg.format:
                valid_formats = {
                    "message": ["text"],
                    "code": ["python", "javascript", "shell"],
                    "image": ["path", "base64.png", "base64.jpeg"],
                    "console": ["output", "active_line"],
                    "confirmation": ["execution"],
                    "file": ["path"]
                }
                
                if msg.type not in valid_formats or msg.format not in valid_formats[msg.type]:
                    return False
                    
            # 验证代码执行序列
            if msg.type == "code":
                # 代码后应该跟着computer的响应
                if i + 1 < len(self.messages):
                    next_msg = self.messages[i + 1]
                    if next_msg.role != "computer" or next_msg.type not in ["confirmation", "console"]:
                        return False
                        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "last_active": self.last_active,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary"""
        session = cls(session_id=data["session_id"])
        session.messages = [Message.from_dict(msg) for msg in data["messages"]]
        session.created_at = data["created_at"]
        session.last_active = data.get("last_active", session.created_at)
        session.metadata = data.get("metadata", {})
        return session

class SessionManager:
    """Manages chat sessions with NCU message format support"""
    def __init__(self, storage_path: str = None, 
                 session_timeout: int = 3600,  # 1小时超时
                 cleanup_interval: int = 300):  # 5分钟清理一次
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict = {}
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.session_locks: Dict[str, threading.Lock] = {}
        self.interpreter_instances: Dict[str, Any] = {}  # 存储每个会话的interpreter实例
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self.cleanup_thread.start()
        
        # 加载持久化的会话
        self._load_persisted_sessions()
        
    def _load_persisted_sessions(self):
        """加载持久化的会话数据"""
        try:
            for session_file in self.storage_path.glob("*.json"):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    # 只加载未过期的会话
                    if self._is_session_valid(session_data.get('last_active', 0)):
                        self.sessions[session_data['session_id']] = session_data
        except Exception as e:
            logger.error(f"Error loading persisted sessions: {str(e)}")

    def _is_session_valid(self, last_active: float) -> bool:
        """检查会话是否有效"""
        return (time.time() - last_active) < self.session_timeout

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        with self.lock:
            current_time = time.time()
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if not self._is_session_valid(session.get('last_active', 0))
            ]
            
            for session_id in expired_sessions:
                self._remove_session(session_id)
                
            return len(expired_sessions)

    def _remove_session(self, session_id: str):
        """删除会话及其持久化文件"""
        try:
            self.sessions.pop(session_id, None)
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logger.error(f"Error removing session {session_id}: {str(e)}")

    def save_all_sessions(self):
        """保存所有活动会话"""
        with self.lock:
            for session_id, session_data in self.sessions.items():
                self._persist_session(session_id, session_data)

    def _persist_session(self, session_id: str, session_data: Dict):
        """持久化单个会话"""
        try:
            session_file = self.storage_path / f"{session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
        except Exception as e:
            logger.error(f"Error persisting session {session_id}: {str(e)}")

    def create_session(self, metadata: Optional[Dict] = None) -> Dict:
        """创建新会话"""
        from interpreter import OpenInterpreter  # 延迟导入避免循环依赖
        
        session_id = str(uuid.uuid4())
        # 为新会话创建独立的interpreter实例
        interpreter_instance = OpenInterpreter()
        interpreter_instance.conversation_history = True
        self.interpreter_instances[session_id] = interpreter_instance
        
        session = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'last_active': time.time(),
            'metadata': metadata or {}
        }
        self.sessions[session_id] = session
        self.session_locks[session_id] = threading.Lock()
        self._persist_session(session_id, session)
        return session

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        session = self.sessions.get(session_id)
        if session and self._is_session_valid(session.get('last_active', 0)):
            session['last_active'] = time.time()
            self._persist_session(session_id, session)
            return session
        return None

    def update_session(self, session_id: str, updates: Dict) -> Optional[Dict]:
        """更新会话信息"""
        session = self.get_session(session_id)
        if session:
            session.update(updates)
            session['last_active'] = time.time()
            self._persist_session(session_id, session)
            return session
        return None

    def list_sessions(self) -> List[Dict]:
        """列出所有有效会话"""
        with self.lock:
            return [
                session for session in self.sessions.values()
                if self._is_session_valid(session.get('last_active', 0))
            ]

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话消息历史"""
        session = self.get_session(session_id)
        if session:
            return session.get('messages', [])
        return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """添加消息到会话（增强验证）"""
        with self.lock:
            session = self.get_session(session_id)
            if session:
                # 增强消息验证
                required_fields = ['role', 'type', 'content']
                if not all(field in message for field in required_fields):
                    raise ValueError(f"Message missing required fields: {required_fields}")
                
                # 自动生成时间戳和ID
                message.setdefault('created_at', datetime.now().isoformat())
                message.setdefault('id', str(uuid.uuid4()))
                
                # 保存到会话
                session['messages'].append(message)
                session['last_active'] = time.time()
                self._persist_session(session_id, session)
                return True
            return False

    def acquire_session_lock(self, session_id: str, timeout: float = 5.0) -> bool:
        """获取会话锁"""
        if session_id not in self.session_locks:
            return False
        return self.session_locks[session_id].acquire(timeout=timeout)

    def release_session_lock(self, session_id: str) -> None:
        """释放会话锁"""
        if session_id in self.session_locks and self.session_locks[session_id].locked():
            self.session_locks[session_id].release()

    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        while True:
            current_time = time.time()
            expired_sessions = [
                session_id
                for session_id, session in self.sessions.items()
                if current_time - session['last_active'] > 86400  # 24小时过期
            ]
            
            for session_id in expired_sessions:
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
                if session_id in self.sessions:
                    del self.sessions[session_id]
                if session_id in self.interpreter_instances:
                    del self.interpreter_instances[session_id]
            
            time.sleep(3600)  # 每小时检查一次

    def get_messages(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话的消息列表"""
        session = self.get_session(session_id)
        if session:
            return session.get('messages', [])
        return None

    def get_or_create_session(self, session_id: Optional[str] = None) -> Tuple[Dict, bool]:
        """Get existing session or create new one
        
        Returns:
            Tuple of (session, created) where created is True if new session was created
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session, False
        return self.create_session(), True

    def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> None:
        """Update session metadata"""
        session = self.get_session(session_id)
        if session:
            session['metadata'].update(metadata)
            self._persist_session(session_id, session)

    def merge_messages(self, session_id: str, new_messages: List[Dict[str, Any]]) -> None:
        """Merge new messages into existing session while maintaining context"""
        session = self.get_session(session_id)
        if session:
            for message in new_messages:
                session['messages'].append(message)
            session['last_active'] = time.time()
            self._persist_session(session_id, session)
        else:
            raise ValueError("Session not found")

    def _generate_session_id(self):
        """Generate a new session ID"""
        return str(uuid.uuid4())

    def _load_existing_sessions(self) -> None:
        """Load existing sessions from storage"""
        for session_file in self.storage_path.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                
                # 如果是旧格式的会话文件（直接是消息列表），则转换为新格式
                if isinstance(data, list):
                    session_id = session_file.stem  # 使用文件名作为会话ID
                    session_data = {
                        "session_id": session_id,
                        "messages": [],
                        "created_at": datetime.now().isoformat(),
                        "last_active": datetime.now().isoformat(),
                        "metadata": {}
                    }
                    
                    # 转换旧格式消息到新格式
                    for msg in data:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            # 设置默认类型
                            msg_type = "message"
                            if msg["role"] == "assistant" and "```" in msg["content"]:
                                msg_type = "code"
                            elif msg["role"] == "computer":
                                msg_type = "console"
                            
                            new_msg = {
                                "role": msg["role"],
                                "type": msg_type,
                                "content": msg["content"],
                                "created_at": datetime.now().isoformat(),
                                "id": str(uuid.uuid4())
                            }
                            session_data["messages"].append(new_msg)
                    
                    session = Session.from_dict(session_data)
                else:
                    session = Session.from_dict(data)
                
                self.sessions[session.session_id] = session.to_dict()
            except Exception as e:
                print(f"Error loading session {session_file}: {e}")

    def get_or_create_session(self, session_id: Optional[str] = None) -> Tuple[Dict, bool]:
        """Get existing session or create new one
        
        Returns:
            Tuple of (session, created) where created is True if new session was created
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session, False
        return self.create_session(), True

    def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> None:
        """Update session metadata"""
        session = self.get_session(session_id)
        if session:
            session['metadata'].update(metadata)
            self._persist_session(session_id, session)

    def merge_messages(self, session_id: str, new_messages: List[Dict[str, Any]]) -> None:
        """Merge new messages into existing session while maintaining context"""
        session = self.get_session(session_id)
        if session:
            for message in new_messages:
                session['messages'].append(message)
            session['last_active'] = time.time()
            self._persist_session(session_id, session)
        else:
            raise ValueError("Session not found")

    def get_messages(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话的消息列表"""
        session = self.get_session(session_id)
        if session:
            return session.get('messages', [])
        return None

    def get_interpreter(self, session_id: str) -> Optional[Any]:
        """获取会话对应的interpreter实例"""
        return self.interpreter_instances.get(session_id) 