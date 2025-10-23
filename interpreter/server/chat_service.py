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
                    is_openai_format: bool = False) -> Union[Dict, List[Dict]]:
        """
        处理聊天请求（非流式）
        
        Args:
            messages: 消息列表
            session_id: 会话ID，如果为None则创建新会话
            stream: 是否使用流式响应
            model: 使用的模型名称
            is_openai_format: 是否使用OpenAI格式响应
            
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
            self.logger.info(f"Getting interpreter instance for session {session_id} with model {model}")
            interpreter = self._get_interpreter(session_id, model)
            if not interpreter:
                self.logger.error(f"Failed to get interpreter instance for session {session_id}")
                return self._create_session_not_found_response(session_id)
            
            # 4. 标记实例为忙碌状态
            self.logger.info(f"Marking instance {session_id} as busy")
            self.session_manager.mark_instance_status(session_id, 'busy')
            
            # 5. 处理消息
            try:
                self.logger.info(f"Starting chat processing for session {session_id}")
                self.logger.info(f"Interpreter config: model={getattr(interpreter.llm, 'model', 'unknown')}, api_base={getattr(interpreter.llm, 'api_base', 'unknown')}")
                # 保存用户消息到会话
                if session_id and messages and len(messages) > 0:
                    # 获取最后一条用户消息
                    last_message = messages[-1]
                    self.logger.info(f"Last message type: {type(last_message)}")
                    
                    # 确保消息是字典格式
                    if isinstance(last_message, dict):
                        self.logger.info(f"Last message content: {last_message}")
                        if last_message.get('role') == 'user':
                            # 检查会话中是否已有相同内容的用户消息，避免重复添加
                            existing_messages = self.session_manager.get_messages(session_id) or []
                            existing_user_contents = [msg.get('content', '') for msg in existing_messages 
                                                    if msg.get('role') == 'user']
                            
                            if last_message.get('content') not in existing_user_contents:
                                self.logger.info(f"Attempting to save user message to session {session_id}")
                                # 将用户消息保存到会话
                                success = self.session_manager.add_message(session_id, last_message)
                                self.logger.info(f"Save result: {success}")
                            else:
                                self.logger.info(f"User message already exists in session, skipping save")
                        else:
                            self.logger.info(f"Last message is not a user message: {last_message.get('role')}")
                    else:
                        self.logger.info(f"Converting message to dict format")
                        # 尝试转换为字典格式
                        if hasattr(last_message, 'to_dict'):
                            msg_dict = last_message.to_dict()
                            self.logger.info(f"Converted message: {msg_dict}")
                            if msg_dict.get('role') == 'user':
                                # 检查会话中是否已有相同内容的用户消息
                                existing_messages = self.session_manager.get_messages(session_id) or []
                                existing_user_contents = [msg.get('content', '') for msg in existing_messages 
                                                        if msg.get('role') == 'user']
                                
                                if msg_dict.get('content') not in existing_user_contents:
                                    success = self.session_manager.add_message(session_id, msg_dict)
                                    self.logger.info(f"Save result: {success}")
                                else:
                                    self.logger.info(f"User message already exists in session, skipping save")
                        else:
                            self.logger.info(f"Cannot convert message to dict format")
                else:
                    self.logger.info(f"No messages to save or session_id is None. session_id: {session_id}, messages length: {len(messages) if messages else 0}")
                
                # 转换OpenAI格式的消息
                interpreter_messages = convert_openai_to_interpreter(messages)
                # 加载历史消息
                interpreter.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]
                # 处理最后一条消息
                self.logger.info(f"Calling interpreter.chat() with message: {interpreter_messages[-1].content[:50]}...")
                try:
                    response = interpreter.chat(interpreter_messages[-1].content, stream=False, display=False)
                    self.logger.info(f"interpreter.chat() completed successfully")
                except Exception as chat_error:
                    self.logger.error(f"interpreter.chat() failed with error: {str(chat_error)}", exc_info=True)
                    raise chat_error
                
                # 转换响应格式为OpenAI消息列表
                openai_messages = convert_interpreter_to_openai(response)
                
                # 包装成OpenAI标准响应格式
                import uuid
                import time
                chat_response = {
                    "id": f"chatcmpl-{str(uuid.uuid4())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model or getattr(interpreter, "model", "gpt-4"),
                    "choices": [{
                        "index": 0,
                        "message": openai_messages[-1] if openai_messages else {"role": "assistant", "content": ""},
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
            return self._format_error(e)
        finally:
            # 7. 重置实例状态为空闲（无论成功还是失败）
            if session_id:
                current_status = self.session_manager.instance_manager.instance_status.get(session_id)
                if current_status in ['busy', 'error']:
                    self.session_manager.mark_instance_status(session_id, 'idle')
                    self.logger.info(f"Reset instance {session_id} status from {current_status} to idle")
            
            # 8. 释放会话锁
            if lock_acquired and session_id:
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
            is_openai_format: 是否使用OpenAI格式响应
            
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
                yield format_openai_stream_chunk(error_chunk)
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
                yield format_openai_stream_chunk(error_chunk)
                return
                
            # 4. 标记实例为忙碌状态
            self.session_manager.mark_instance_status(session_id, 'busy')
            
            try:
                # 5. 处理消息并生成流式响应
                # 保存用户消息到会话
                if session_id and messages and len(messages) > 0:
                    # 获取最后一条用户消息
                    last_message = messages[-1]
                    if isinstance(last_message, dict) and last_message.get('role') == 'user':
                        # 检查会话中是否已有相同内容的用户消息，避免重复添加
                        existing_messages = self.session_manager.get_messages(session_id) or []
                        if existing_messages:
                            existing_user_contents = [msg.get('content', '') for msg in existing_messages 
                                                if msg.get('role') == 'user']
                            
                            if last_message.get('content') not in existing_user_contents:
                                # 将用户消息保存到会话
                                self.session_manager.add_message(session_id, last_message)
                
                # 转换OpenAI格式的消息
                interpreter_messages = convert_openai_to_interpreter(messages)
                # 加载历史消息
                interpreter.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]
                # 处理最后一条消息
                response = interpreter.chat(interpreter_messages[-1].content, stream=True, display=False)
                
                # 处理流式响应
                for chunk in response:
                    # 处理角色映射，确保OpenAI格式兼容
                    chunk_role = chunk.get('role', 'assistant')
                    if chunk_role == 'computer':
                        # 根据类型映射不同的角色
                        if chunk.get('type') == 'console' and chunk.get('format') == 'output':
                            chunk_role = 'function'
                        else:
                            chunk_role = 'assistant'
                    
                    # 创建包装后的chunk对象
                    chunk_obj = StreamingChunk(
                        role=chunk_role,  # 使用转换后的角色
                        type=chunk.get('type', 'message'),
                        content=chunk.get('content', ''),
                        format=chunk.get('format'),
                        recipient='user',
                        id=chunk.get('id'),
                        start=chunk.get('start', False),
                        end=chunk.get('end', False)
                    )
                    yield format_openai_stream_chunk(chunk_obj)
                
                # 在OpenAI格式下发送[DONE]信号
                if is_openai_format:
                    yield "data: [DONE]\n\n"
                
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
                yield format_openai_stream_chunk(error_chunk)
                
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
            yield format_openai_stream_chunk(error_chunk)
        finally:
            # 6. 重置实例状态为空闲（无论成功还是失败）
            if session_id:
                current_status = self.session_manager.instance_manager.instance_status.get(session_id)
                if current_status in ['busy', 'error']:
                    self.session_manager.mark_instance_status(session_id, 'idle')
                    self.logger.info(f"Reset streaming instance {session_id} status from {current_status} to idle")
            
            # 7. 释放会话锁
            if lock_acquired and session_id:
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
        获取解释器实例，如果提供了新的模型参数，更新 session metadata
        
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
            
            # 更新 session metadata 中的模型配置
            try:
                session = self.session_manager.get_session(session_id)
                if session:
                    if 'metadata' not in session:
                        session['metadata'] = {}
                    session['metadata']['model'] = model
                    # 保存更新后的 session
                    self.session_manager._persist_session(session_id, session)
                    self.logger.info(f"Updated session {session_id} metadata with model: {model}")
            except Exception as e:
                self.logger.warning(f"Failed to update session metadata: {str(e)}")
                
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
    
    def _format_error(self, error: Exception) -> Dict:
        """
        格式化错误响应
        
        Args:
            error: 异常
            
        Returns:
            错误响应
        """
        # 使用现有的错误格式化函数
        error_response, _ = format_error_response(error)
        return error_response 