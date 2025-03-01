"""
统一的聊天处理服务
处理原生聊天和OpenAI兼容接口的核心逻辑
"""

import time
import threading
from typing import Dict, List, Optional, Any, Generator, Tuple, Union, Callable

from .message import Message, StreamingChunk
from .errors import ValidationError, format_error_response
from .log_config import setup_logging
from .utils import (
    convert_openai_to_interpreter,
    convert_interpreter_to_openai,
    format_stream_chunk,
    format_openai_stream_chunk
)

class ChatService:
    """统一的聊天处理服务"""
    
    def __init__(self, session_manager):
        """
        初始化聊天服务
        
        Args:
            session_manager: 会话管理器实例
        """
        self.session_manager = session_manager
        self.logger = setup_logging('chat_service')
    
    def process_chat(self, 
                    messages: List[Dict], 
                    session_id: Optional[str] = None, 
                    stream: bool = False, 
                    model: Optional[str] = None,
                    is_openai_format: bool = False) -> Dict:
        """
        处理聊天请求（非流式）
        
        Args:
            messages: 消息列表
            session_id: 会话ID，如果为None则创建新会话
            stream: 是否使用流式响应
            model: 使用的模型名称
            is_openai_format: 是否使用OpenAI格式
            
        Returns:
            处理结果
        """
        lock_acquired = False
        try:
            # 1. 会话管理
            session_id, is_new_session = self._get_or_create_session(session_id)
            
            # 2. 获取会话锁
            if not self._acquire_session_lock(session_id):
                return self._create_busy_response(session_id)
            lock_acquired = True
            self.logger.info(f"Session lock acquired for session {session_id}")
            
            # 3. 获取解释器实例
            interpreter = self._get_interpreter(session_id, model)
            if not interpreter:
                return self._create_session_not_found_response(session_id)
            
            # 4. 标记实例为忙碌状态
            self.session_manager.mark_instance_status(session_id, 'busy')
            
            # 5. 处理消息
            try:
                if is_openai_format:
                    # 保存用户消息到会话
                    if session_id and messages and len(messages) > 0:
                        # 获取最后一条用户消息
                        last_message = messages[-1]
                        self.logger.info(f"Last message type: {type(last_message)}")
                        
                        # 确保消息是字典格式
                        if isinstance(last_message, dict):
                            self.logger.info(f"Last message content: {last_message}")
                            if last_message.get('role') == 'user':
                                self.logger.info(f"Attempting to save user message to session {session_id}")
                                # 将用户消息保存到会话
                                success = self.session_manager.add_message(session_id, last_message)
                                self.logger.info(f"Save result: {success}")
                            else:
                                self.logger.info(f"Last message is not a user message: {last_message.get('role')}")
                        else:
                            self.logger.info(f"Converting message to dict format")
                            # 尝试转换为字典格式
                            if hasattr(last_message, 'to_dict'):
                                msg_dict = last_message.to_dict()
                                self.logger.info(f"Converted message: {msg_dict}")
                                if msg_dict.get('role') == 'user':
                                    success = self.session_manager.add_message(session_id, msg_dict)
                                    self.logger.info(f"Save result: {success}")
                            else:
                                self.logger.info(f"Cannot convert message to dict format")
                    else:
                        self.logger.info(f"No messages to save or session_id is None. session_id: {session_id}, messages length: {len(messages) if messages else 0}")
                    
                    # 转换OpenAI格式的消息
                    interpreter_messages = convert_openai_to_interpreter(messages)
                    # 加载历史消息
                    interpreter.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]
                    # 处理最后一条消息
                    response = interpreter.chat(interpreter_messages[-1].content, stream=False, display=False)
                    # 处理响应
                    from .message_processor import MessageProcessor
                    result = MessageProcessor.process_response(response, self.session_manager, session_id)
                    # 处理完成后标记为空闲
                    self.session_manager.mark_instance_status(session_id, 'idle')
                    return result
                else:
                    # 原生格式处理
                    # 记录当前消息数量，用于过滤历史消息
                    current_message_count = len(interpreter.messages)
                    
                    # 准备消息
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        last_message_content = last_message.get('content', '')
                    elif isinstance(last_message, Message):
                        last_message_content = last_message.content
                    else:
                        last_message_content = str(last_message)
                    
                    # 设置历史消息
                    if len(messages) > 1:  # 如果有历史消息
                        interpreter.messages = []  # 先清空
                        for msg in messages[:-1]:
                            if isinstance(msg, str):
                                msg_dict = {
                                    'role': 'user',
                                    'type': 'message',
                                    'content': msg
                                }
                            elif isinstance(msg, dict):
                                msg_dict = msg
                            elif isinstance(msg, Message):
                                msg_dict = msg.to_dict()
                            else:
                                msg_dict = {
                                    'role': 'user',
                                    'type': 'message',
                                    'content': str(msg)
                                }
                            interpreter.messages.append(msg_dict)
                    
                    # 执行聊天
                    response = interpreter.chat(
                        last_message_content,
                        stream=False,
                        display=False
                    )
                    
                    # 处理响应
                    response_messages = []
                    code_messages = []
                    
                    # 只处理新生成的消息，跳过历史消息
                    new_messages = interpreter.messages[current_message_count:]
                    
                    # 遍历生成的所有消息
                    for msg in new_messages:
                        if msg["role"] in ["assistant", "computer"]:
                            if msg["type"] == "message":
                                response_messages.append({
                                    "role": "assistant",
                                    "content": msg["content"]
                                })
                            elif msg["type"] == "code":
                                code_messages.append({
                                    "role": "assistant",
                                    "type": "code",
                                    "content": msg["content"],
                                    "format": msg.get("format", "python")
                                })
                            elif msg["type"] == "console" and msg["role"] == "computer":
                                code_messages.append({
                                    "role": "computer",
                                    "type": "console",
                                    "content": msg["content"]
                                })
                    
                    # 构造最终响应
                    chat_response = {
                        "id": f"chatcmpl-{session_id}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": getattr(interpreter, "model", "gpt-4"),
                        "choices": [{
                            "index": 0,
                            "messages": code_messages + response_messages,
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        }
                    }
                    
                    # 处理完成后标记为空闲
                    self.session_manager.mark_instance_status(session_id, 'idle')
                    return chat_response
            except Exception as e:
                # 处理过程中出错，标记状态为错误
                self.session_manager.mark_instance_status(session_id, 'error')
                raise e
                
        except Exception as e:
            self.logger.error(f"Error processing chat: {str(e)}", exc_info=True)
            # 确保出错时也标记状态
            if session_id:
                self.session_manager.mark_instance_status(session_id, 'error')
            return self._format_error(e, is_openai_format)
        finally:
            # 7. 释放会话锁
            if lock_acquired:
                self.logger.info(f"Releasing session lock for session {session_id}")
                self._release_session_lock(session_id)
    
    def process_streaming_chat(self, 
                              messages: List[Dict], 
                              session_id: Optional[str] = None, 
                              model: Optional[str] = None,
                              is_openai_format: bool = False) -> Generator:
        """
        处理流式聊天请求
        
        Args:
            messages: 消息列表
            session_id: 会话ID，如果为None则创建新会话
            model: 使用的模型名称
            is_openai_format: 是否使用OpenAI格式
            
        Returns:
            生成器，产生流式响应
        """
        lock_acquired = False
        try:
            # 1. 会话管理
            session_id, is_new_session = self._get_or_create_session(session_id)
            
            # 2. 获取会话锁
            if not self._acquire_session_lock(session_id):
                error_response = self._create_busy_response(session_id)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=error_response['error']['message'],
                    recipient='user'
                )
                format_func = format_openai_stream_chunk if is_openai_format else format_stream_chunk
                yield format_func(error_chunk)
                return
                
            lock_acquired = True
            self.logger.info(f"Session lock acquired for session {session_id} (streaming)")
            
            # 3. 获取解释器实例
            interpreter = self._get_interpreter(session_id, model)
            if not interpreter:
                error_response = self._create_session_not_found_response(session_id)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=error_response['error']['message'],
                    recipient='user'
                )
                format_func = format_openai_stream_chunk if is_openai_format else format_stream_chunk
                yield format_func(error_chunk)
                return
                
            # 4. 标记实例为忙碌状态
            self.session_manager.mark_instance_status(session_id, 'busy')
            
            try:
                # 5. 处理消息并生成流式响应
                format_func = format_openai_stream_chunk if is_openai_format else format_stream_chunk
                
                if is_openai_format:
                    # 保存用户消息到会话
                    if session_id and messages and len(messages) > 0:
                        # 获取最后一条用户消息
                        last_message = messages[-1]
                        if isinstance(last_message, dict) and last_message.get('role') == 'user':
                            # 将用户消息保存到会话
                            self.session_manager.add_message(session_id, last_message)
                    
                    # 转换OpenAI格式的消息
                    interpreter_messages = convert_openai_to_interpreter(messages)
                    # 加载历史消息
                    interpreter.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]
                    # 处理最后一条消息
                    response = interpreter.chat(interpreter_messages[-1].content, stream=True, display=False)
                else:
                    # 原生格式处理
                    # 准备消息
                    last_message = messages[-1]
                    if isinstance(last_message, dict):
                        last_message_content = last_message.get('content', '')
                    elif isinstance(last_message, Message):
                        last_message_content = last_message.content
                    else:
                        last_message_content = str(last_message)
                    
                    # 设置历史消息
                    if len(messages) > 1:  # 如果有历史消息
                        interpreter.messages = []  # 先清空
                        for msg in messages[:-1]:
                            if isinstance(msg, str):
                                msg_dict = {
                                    'role': 'user',
                                    'type': 'message',
                                    'content': msg
                                }
                            elif isinstance(msg, dict):
                                msg_dict = msg
                            elif isinstance(msg, Message):
                                msg_dict = msg.to_dict()
                            else:
                                msg_dict = {
                                    'role': 'user',
                                    'type': 'message',
                                    'content': str(msg)
                                }
                            interpreter.messages.append(msg_dict)
                    
                    # 执行聊天
                    response = interpreter.chat(
                        last_message_content,
                        stream=True,
                        display=False
                    )
                
                # 处理流式响应
                for chunk in response:
                    # 创建包装后的chunk对象
                    chunk_obj = StreamingChunk(
                        role='assistant' if chunk.get('role') == 'assistant' else 'computer',
                        type=chunk.get('type', 'message'),
                        content=chunk.get('content', ''),
                        format=chunk.get('format'),
                        recipient='user',
                        id=chunk.get('id'),
                        start=chunk.get('start', False),
                        end=chunk.get('end', False)
                    )
                    yield format_func(chunk_obj)
                
                # 流处理结束后，标记实例为空闲
                self.session_manager.mark_instance_status(session_id, 'idle')
                
            except Exception as e:
                # 处理过程中出错，标记实例为错误状态
                self.session_manager.mark_instance_status(session_id, 'error')
                self.logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=str(e),
                    recipient='user'
                )
                format_func = format_openai_stream_chunk if is_openai_format else format_stream_chunk
                yield format_func(error_chunk)
                
        except Exception as e:
            # 确保出错时也标记状态
            if session_id:
                self.session_manager.mark_instance_status(session_id, 'error')
            self.logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
            error_chunk = StreamingChunk(
                role='assistant',
                type='error',
                content=str(e),
                recipient='user'
            )
            format_func = format_openai_stream_chunk if is_openai_format else format_stream_chunk
            yield format_func(error_chunk)
        finally:
            # 6. 释放会话锁
            if lock_acquired:
                self.logger.info(f"Releasing session lock for session {session_id} (streaming)")
                self._release_session_lock(session_id)
    
    # 辅助方法
    def _get_or_create_session(self, session_id: Optional[str]) -> Tuple[str, bool]:
        """
        获取或创建会话
        
        Args:
            session_id: 会话ID，如果为None则创建新会话
            
        Returns:
            (session_id, is_new_session) 元组
        """
        if session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                return session_id, False
        
        # 创建新会话
        session = self.session_manager.create_session()
        return session['session_id'], True
    
    def _acquire_session_lock(self, session_id: str) -> bool:
        """
        获取会话锁
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功获取锁
        """
        return self.session_manager.acquire_session_lock(session_id, timeout=5.0)
    
    def _release_session_lock(self, session_id: str) -> None:
        """
        释放会话锁
        
        Args:
            session_id: 会话ID
        """
        self.session_manager.release_session_lock(session_id)
    
    def _get_interpreter(self, session_id: str, model: Optional[str]) -> Any:
        """
        获取解释器实例
        
        Args:
            session_id: 会话ID
            model: 使用的模型名称
            
        Returns:
            解释器实例
        """
        interpreter = self.session_manager.get_interpreter(session_id)
        if interpreter and model:
            # 更新模型
            if hasattr(interpreter, 'llm') and hasattr(interpreter.llm, 'model'):
                interpreter.llm.model = model
            elif hasattr(interpreter, 'model'):
                interpreter.model = model
        return interpreter
    
    def _create_busy_response(self, session_id: str) -> Dict:
        """
        创建会话忙响应
        
        Args:
            session_id: 会话ID
            
        Returns:
            错误响应
        """
        return {
            "error": {
                "message": "会话正忙，请稍后再试",
                "code": "session_busy",
                "details": {
                    "retry_after": 5,
                    "status": "locked",
                    "session_id": session_id
                }
            }
        }
    
    def _create_session_not_found_response(self, session_id: str) -> Dict:
        """
        创建会话不存在响应
        
        Args:
            session_id: 会话ID
            
        Returns:
            错误响应
        """
        return {
            "error": {
                "message": "会话已过期或不存在",
                "code": "session_expired",
                "details": {
                    "session_id": session_id
                }
            }
        }
    
    def _format_error(self, error: Exception, is_openai_format: bool = False) -> Dict:
        """
        格式化错误响应
        
        Args:
            error: 异常
            is_openai_format: 是否使用OpenAI格式
            
        Returns:
            错误响应
        """
        if is_openai_format:
            # OpenAI格式的错误
            return {
                "error": {
                    "message": str(error),
                    "type": error.__class__.__name__,
                    "param": None,
                    "code": "internal_error"
                }
            }
        
        # 使用现有的错误格式化函数
        error_response, _ = format_error_response(error)
        return error_response 