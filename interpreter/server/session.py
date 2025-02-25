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

# 只导入需要的类，避免循环依赖
from .log_config import setup_logging
from .models import MessageBase, Session

# 获取logger实例
logger = setup_logging('interpreter_server')

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
            type=data.get("type", "message"),
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
    def __init__(self, 
                 storage_path: str = None, 
                 session_timeout: int = 3600,
                 cleanup_interval: int = 300,
                 max_active_instances: int = 3):
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
        self._chat_locks: Dict[str, threading.Lock] = {}  # 专用于聊天操作的锁
        self.max_active_instances = max_active_instances
        self.instance_last_used = {}  # 记录实例最后使用时间
        
        self._active_locks = set()
        self._lock_timeout = 30  # 30秒锁超时
        
        # 添加缺失的锁
        self._instances_lock = threading.Lock()
        self._sessions_lock = threading.Lock()
        self.lock = threading.Lock()
        
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
                    messages = json.load(f)
                    return messages if isinstance(messages, list) else []
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}")
        return []

    def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """添加消息到会话并持久化存储"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False

            # 构造消息对象
            msg_data = {
                "role": message["role"],
                "type": message.get("type", "message"),
                "content": message["content"],
                "format": message.get("format"),
                "created_at": datetime.now().isoformat()
            }

            # 更新会话消息
            if 'messages' not in session:
                session['messages'] = []
            session['messages'].append(msg_data)
            session['last_active'] = time.time()

            # 持久化保存
            self._persist_session(session_id, session)
            return True
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            return False

    def get_messages(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话的消息列表"""
        try:
            session = self.get_session(session_id)
            if session:
                messages = session.get('messages', [])
                return messages
            logger.debug(f"Cannot get messages: session {session_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}", exc_info=True)
            return None

    def _cleanup_expired_sessions(self):
        """优化清理过期会话的逻辑"""
        while True:
            try:
                # 获取需要清理的会话列表
                to_cleanup = []
                with self._instances_lock:
                    current_time = time.time()
                    expired_sessions = [
                        session_id
                        for session_id, last_used in self.instance_last_used.items()
                        if current_time - last_used > self.session_timeout
                    ]
                    to_cleanup.extend(expired_sessions)
                
                # 在锁外执行清理
                for session_id in to_cleanup:
                    self._cleanup_instance(session_id)
                    
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
        """Create a new session with metadata"""
        session_id = str(uuid.uuid4())
        
        if metadata and isinstance(metadata, dict):
            if 'metadata' in metadata:
                metadata = metadata['metadata']
                
        session = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'last_active': time.time(),
            'metadata': metadata or {}
        }
        
        try:
            # 创建解释器实例
            from interpreter import OpenInterpreter
            interpreter_instance = OpenInterpreter()
            interpreter_instance.conversation_history = True
            self.interpreter_instances[session_id] = interpreter_instance
            
            # 保存会话数据
            self.sessions[session_id] = session
            self.session_locks[session_id] = threading.Lock()
            self._persist_session(session_id, session)
            
            logger.info(f"Created new session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息（无锁快速路径）"""
        try:
            session = self.sessions.get(session_id)
            if session and self._is_session_valid(session.get('last_active', 0)):
                # 异步更新最后活动时间
                def update_last_active():
                    session['last_active'] = time.time()
                    self._persist_session(session_id, session)
                threading.Thread(target=update_last_active, daemon=True).start()
                return session
            
            # 如果会话不存在或已过期，记录日志并返回 None
            if not session:
                logger.debug(f"Session not found: {session_id}")
            elif not self._is_session_valid(session.get('last_active', 0)):
                logger.debug(f"Session expired: {session_id}")
            
            return None
        except Exception as e:
            # 记录详细错误信息，但仍然返回 None 而不是抛出异常
            logger.error(f"Error getting session {session_id}: {str(e)}", exc_info=True)
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
        """列出所有有效会话（快速路径）"""
        try:
            # 快速拷贝会话列表，避免长时间持有锁
            with self._sessions_lock:
                sessions = list(self.sessions.values())
            
            # 在锁外部处理过滤
            return [
                session for session in sessions
                if self._is_session_valid(session.get('last_active', 0))
            ]
        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}")
            return []

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话消息历史"""
        session = self.get_session(session_id)
        if session:
            return session.get('messages', [])
        return []

    def acquire_session_lock(self, session_id: str, timeout: float = 5.0) -> bool:
        """获取会话锁（只用于聊天操作）"""
        try:
            if session_id in self._active_locks:
                # 检查是否超时
                lock_time = self.instance_last_used.get(session_id, 0)
                if time.time() - lock_time > self._lock_timeout:
                    self.release_session_lock(session_id)
                else:
                    return False

            # 创建或获取聊天锁
            if session_id not in self._chat_locks:
                self._chat_locks[session_id] = threading.Lock()
            
            # 尝试获取锁
            if self._chat_locks[session_id].acquire(timeout=timeout):
                self._active_locks.add(session_id)
                self.instance_last_used[session_id] = time.time()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Lock acquisition failed: {str(e)}")
            return False

    def release_session_lock(self, session_id: str) -> None:
        """释放会话锁，仅用于聊天操作"""
        try:
            if session_id in self._active_locks:
                self._active_locks.remove(session_id)
                
            if session_id in self._chat_locks:
                try:
                    self._chat_locks[session_id].release()
                except RuntimeError:
                    pass  # 忽略重复释放的错误
        except Exception as e:
            logger.error(f"Lock release failed: {str(e)}")

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
        """获取会话对应的interpreter实例（优化锁的使用）"""
        try:
            # 快速路径：检查实例是否存在
            interpreter = self.interpreter_instances.get(session_id)
            if interpreter is not None:
                with self._instances_lock:
                    self.instance_last_used[session_id] = time.time()
                return interpreter
            
            # 慢路径：需要创建新实例
            with self._instances_lock:
                # 双重检查，避免竞态条件
                interpreter = self.interpreter_instances.get(session_id)
                if interpreter is not None:
                    self.instance_last_used[session_id] = time.time()
                    return interpreter
                    
                logger.info(f"Creating new interpreter instance for session {session_id}")
                self.optimize_interpreter_instances(session_id)
                interpreter = self._create_new_interpreter(session_id)
                self.interpreter_instances[session_id] = interpreter
                self.instance_last_used[session_id] = time.time()
                
            logger.debug(f"Active interpreter instances: {len(self.interpreter_instances)}/{self.max_active_instances}")
            return interpreter
            
        except Exception as e:
            logger.error(f"Error getting interpreter: {str(e)}")
            return None

    def _create_new_interpreter(self, session_id: str) -> Any:
        """创建新的interpreter实例"""
        from interpreter import OpenInterpreter
        interpreter = OpenInterpreter()
        interpreter.auto_run = True
        interpreter.conversation_history = True
        # 加载历史消息
        messages = self._load_session_messages(session_id)
        if messages:
            interpreter.messages = messages
        return interpreter            

    def optimize_interpreter_instances(self, session_id: str) -> None:
        """优化 interpreter 实例管理"""
        with self.lock:
            if len(self.interpreter_instances) >= self.max_active_instances:
                # 找出最不活跃的实例进行清理
                oldest_session = min(
                    self.instance_last_used.items(), 
                    key=lambda x: x[1]
                )[0]
                if oldest_session != session_id:
                    logger.info(
                        f"Cleaning up inactive interpreter instance for session {oldest_session} "
                        f"(active instances: {len(self.interpreter_instances)})"
                    )
                    self._cleanup_instance(oldest_session)

    def _cleanup_instance(self, session_id: str) -> None:
        """清理指定会话的interpreter实例（优化锁的使用）"""
        try:
            with self._instances_lock:
                if session_id in self.interpreter_instances:
                    del self.interpreter_instances[session_id]
                if session_id in self.instance_last_used:
                    del self.instance_last_used[session_id]
            
            # 分开使用会话锁
            with self._sessions_lock:
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    
            # 异步删除文件
            def delete_file():
                try:
                    session_file = self.storage_path / f"{session_id}.json"
                    if session_file.exists():
                        session_file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting session file: {str(e)}")
                    
            threading.Thread(target=delete_file, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error cleaning up instance {session_id}: {str(e)}")

    def get_instances_status(self) -> Dict[str, Any]:
        """获取实例状态信息（无锁实现）"""
        try:
            # 直接读取实例数量，不使用锁
            # 由于这只是用于监控，即使数据有少许不准确也可接受
            return {
                "max_instances": self.max_active_instances,
                "active_instances": len(self.interpreter_instances)
            }
        except Exception as e:
            logger.error(f"Error getting instances status: {str(e)}")
            return {
                "max_instances": self.max_active_instances,
                "active_instances": 0,
                "error": str(e)
            }

from typing import Dict, Optional
from .models import Session, MessageBase
from .log_config import logger

class SessionService:
    """Session management service layer"""
    def __init__(self):
        self._manager = SessionManager()
    
    def create_session(self, metadata: Optional[Dict] = None) -> Session:
        """Create new session"""
        try:
            session = self._manager.create_session(metadata)
            logger.info(f"Created new session: {session.session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise

    def add_message(self, session_id: str, message: MessageBase) -> None:
        """Add message to session"""
        try:
            session = self._manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            session.messages.append(message)
            session.last_active = datetime.now().isoformat()
            logger.debug(f"Added message to session {session_id}")
        except Exception as e:
            logger.error(f"Failed to add message: {str(e)}")
            raise

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            return self._manager.get_session(session_id)
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            raise

    def update_session_metadata(self, session_id: str, metadata: Dict) -> None:
        """Update session metadata"""
        try:
            self._manager.update_session_metadata(session_id, metadata)
            logger.info(f"Updated metadata for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to update metadata: {str(e)}")
            raise

    def export_session(self, session_id: str) -> Dict:
        """Export session data"""
        try:
            session = self._manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            return session.to_dict()
        except Exception as e:
            logger.error(f"Failed to export session: {str(e)}")
            raise