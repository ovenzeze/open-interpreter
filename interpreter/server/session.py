"""
Session management for Open Interpreter HTTP Server
Following NCU (New Computer Update) message format
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal, Union, Tuple

import platformdirs
import os
import time
import threading

# 创建 logger
logger = logging.getLogger('interpreter_server')

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
        # 使用 platformdirs 获取系统配置目录
        if storage_path is None:
            storage_path = platformdirs.user_config_dir("open-interpreter")
            storage_path = os.path.join(storage_path, "conversations")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.session_locks: Dict[str, threading.Lock] = {}
        self.interpreter_instances: Dict[str, Any] = {}
        self.lock = threading.Lock()  # 添加全局锁对象
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self.cleanup_thread.start()
        
        # 加载持久化的会话
        self._load_persisted_sessions()

    def _get_session_file_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.storage_path / f"{session_id}.json"

    def _save_session_messages(self, session_id: str, messages: List[Dict]) -> None:
        """保存会话消息到文件"""
        try:
            file_path = self._get_session_file_path(session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {str(e)}")

    def _load_session_messages(self, session_id: str) -> List[Dict]:
        """从文件加载会话消息"""
        try:
            file_path = self._get_session_file_path(session_id)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}")
        return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """添加消息到会话并持久化存储
        
        Args:
            session_id: 会话ID
            message: 消息字典，必须包含 role、type、content 字段
            
        Returns:
            bool: 是否成功添加消息
        """
        try:
            # 验证消息格式
            required_fields = ['role', 'type', 'content']
            if not all(field in message for field in required_fields):
                logger.error(f"Message missing required fields: {required_fields}")
                return False
                
            # 获取当前会话消息
            messages = self._load_session_messages(session_id)
            
            # 添加新消息
            messages.append({
                "role": message["role"],
                "type": message["type"],
                "content": message["content"]
            })
            
            # 保存到文件
            self._save_session_messages(session_id, messages)
            
            # 更新内存中的会话
            session = self.sessions.get(session_id)
            if session:
                if 'messages' not in session:
                    session['messages'] = []
                session['messages'] = messages
                session['last_active'] = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            return False

    def get_messages(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话的消息列表"""
        try:
            # 首先检查会话是否存在且有效
            session = self.get_session(session_id)
            if not session:
                return None
                
            # 从文件加载最新消息
            messages = self._load_session_messages(session_id)
            
            # 更新会话的最后活动时间
            session['last_active'] = time.time()
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return None

    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        while True:
            try:
                current_time = time.time()
                expired_sessions = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if current_time - session['last_active'] > self.session_timeout
                ]
                
                for session_id in expired_sessions:
                    # 清理锁
                    if session_id in self.session_locks:
                        del self.session_locks[session_id]
                    # 清理会话
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    # 清理interpreter实例
                    if session_id in self.interpreter_instances:
                        del self.interpreter_instances[session_id]
                    # 清理文件
                    file_path = self._get_session_file_path(session_id)
                    if file_path.exists():
                        file_path.unlink()
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup thread: {str(e)}")
                time.sleep(self.cleanup_interval)

    def _load_persisted_sessions(self):
        """加载持久化的会话数据"""
        try:
            for session_file in self.storage_path.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        
                    # 处理旧格式的会话文件（直接是消息列表）
                    if isinstance(session_data, list):
                        session_id = session_file.stem
                        session = {
                            'session_id': session_id,
                            'created_at': datetime.now().isoformat(),
                            'messages': session_data,
                            'last_active': time.time(),
                            'metadata': {}
                        }
                        self.sessions[session_id] = session
                    else:
                        # 新格式的会话文件
                        session_id = session_data.get('session_id') or session_file.stem
                        if self._is_session_valid(session_data.get('last_active', time.time())):
                            self.sessions[session_id] = session_data
                            
                except Exception as e:
                    logger.error(f"Error loading session file {session_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading persisted sessions: {str(e)}")

    def _is_session_valid(self, last_active) -> bool:
        """检查会话是否有效"""
        try:
            if isinstance(last_active, str):
                last_active = datetime.fromisoformat(last_active).timestamp()
            return (time.time() - float(last_active)) < self.session_timeout
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating session timestamp: {str(e)}")
            return False

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

    def acquire_session_lock(self, session_id: str, timeout: float = 5.0) -> bool:
        """获取会话锁"""
        if session_id not in self.session_locks:
            return False
        return self.session_locks[session_id].acquire(timeout=timeout)

    def release_session_lock(self, session_id: str) -> None:
        """释放会话锁"""
        if session_id in self.session_locks and self.session_locks[session_id].locked():
            self.session_locks[session_id].release()

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

    def get_interpreter(self, session_id: str) -> Optional[Any]:
        """获取会话对应的interpreter实例"""
        return self.interpreter_instances.get(session_id) 