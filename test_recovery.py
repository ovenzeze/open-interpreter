#!/usr/bin/env python
"""
测试异常退出恢复功能

这个脚本测试在聊天过程中发生异常情况下，会话状态和消息是否被正确保存和恢复。
它将模拟以下场景：
1. 创建一个会话并发送一条消息
2. 模拟处理过程中发生异常
3. 验证会话状态是否被标记为error
4. 验证会话锁是否被正确释放
5. 验证消息是否被正确保存
6. 尝试恢复会话并发送新消息
"""

import sys
import time
import logging
import threading
import json
import os
import uuid
from typing import Dict, List, Optional, Any, Generator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_recovery')

# 模拟必要的类和函数
class StreamingChunk:
    """模拟StreamingChunk类"""
    def __init__(self, role, type, content, recipient=None, format=None, id=None, start=False, end=False):
        self.role = role
        self.type = type
        self.content = content
        self.recipient = recipient
        self.format = format
        self.id = id
        self.start = start
        self.end = end
        
    def __str__(self):
        return f"StreamingChunk(role={self.role}, type={self.type}, content={self.content})"

def format_stream_chunk(chunk):
    """模拟format_stream_chunk函数"""
    return {
        "role": chunk.role,
        "type": chunk.type,
        "content": chunk.content,
        "format": chunk.format
    }

class Message:
    """模拟Message类"""
    def __init__(self, role, content, type="message"):
        self.role = role
        self.content = content
        self.type = type
        
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "type": self.type
        }

# 模拟Interpreter类
class MockInterpreter:
    """模拟解释器类，用于测试"""
    def __init__(self, should_fail=False, should_save_on_error=True):
        self.messages = []
        self.should_fail = should_fail
        self.should_save_on_error = should_save_on_error
        self.model = "mock-model"
        self.conversation_history = True
        self.conversation_filename = None
        self.conversation_history_path = "./test_conversations"
        
        # 确保测试目录存在
        if not os.path.exists(self.conversation_history_path):
            os.makedirs(self.conversation_history_path)
        
    def chat(self, content, stream=False, display=False):
        """模拟聊天方法"""
        # 添加用户消息
        self.messages.append({"role": "user", "content": content, "type": "message"})
        
        try:
            if self.should_fail:
                raise Exception("模拟执行失败")
                
            if stream:
                return self._stream_response(content)
            else:
                # 非流式响应
                response = {"role": "assistant", "content": f"回复: {content}", "type": "message"}
                self.messages.append(response)
                
                # 保存会话
                self._save_conversation()
                return response
        except Exception as e:
            logger.error(f"聊天过程中发生错误: {str(e)}")
            
            # 即使在错误情况下也保存会话
            if self.should_save_on_error:
                self._save_conversation()
            
            raise
            
    def _stream_response(self, content):
        """模拟流式响应"""
        try:
            # 生成助手消息片段
            yield {"role": "assistant", "type": "message", "content": "正在", "start": True}
            yield {"role": "assistant", "type": "message", "content": "思考"}
            
            if self.should_fail:
                raise Exception("模拟流式处理中断")
                
            yield {"role": "assistant", "type": "message", "content": "您的问题..."}
            
            # 生成代码消息
            yield {"role": "assistant", "type": "code", "content": "print('Hello World')", "format": "python", "start": True}
            yield {"role": "assistant", "type": "code", "content": "", "format": "python", "end": True}
            
            # 生成计算机输出
            yield {"role": "computer", "type": "console", "content": "Hello World\n", "start": True}
            yield {"role": "computer", "type": "console", "content": "", "end": True}
            
            # 生成最终回复
            yield {"role": "assistant", "type": "message", "content": f"回复: {content}", "end": True}
            
            # 更新消息历史
            self.messages.append({"role": "assistant", "content": f"回复: {content}", "type": "message"})
            
            # 保存会话
            self._save_conversation()
            
        except Exception as e:
            logger.error(f"流式响应中发生错误: {str(e)}")
            
            # 即使在错误情况下也保存会话
            if self.should_save_on_error:
                self._save_conversation()
                
            raise
    
    def _save_conversation(self):
        """保存会话到文件"""
        try:
            # 如果是第一条消息，设置会话文件名
            if not self.conversation_filename and len(self.messages) > 0:
                first_few_words = self.messages[0]["content"][:15].replace(" ", "_")
                self.conversation_filename = f"{first_few_words}_{int(time.time())}.json"
            
            # 检查目录是否存在
            if not os.path.exists(self.conversation_history_path):
                os.makedirs(self.conversation_history_path)
                
            # 写入文件
            if self.conversation_filename:
                file_path = os.path.join(self.conversation_history_path, self.conversation_filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.messages, f, ensure_ascii=False)
                    
                logger.info(f"会话已保存到: {file_path}")
                
        except Exception as e:
            logger.error(f"保存会话时发生错误: {str(e)}")

# 模拟SessionManager类
class MockSessionManager:
    """模拟SessionManager类，用于测试"""
    def __init__(self):
        self.sessions = {}
        self.interpreter_instances = {}
        self.instance_status = {}
        self._chat_locks = {}
        self._active_locks = set()
        self.instance_last_used = {}
        self._lock_timeout = 30.0  # 30秒超时
        self._instances_lock = threading.RLock()
        self.storage_path = "./test_sessions"
        
        # 确保测试目录存在
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        
    def get_or_create_session(self, session_id=None):
        """获取或创建会话"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "created_at": time.time(),
                "last_active": time.time(),
                "metadata": {}
            }
            # 保存会话文件
            self._persist_session(session_id, self.sessions[session_id])
            return session_id, True
        
        return session_id, False
    
    def _persist_session(self, session_id, session_data):
        """保存会话到文件"""
        try:
            file_path = os.path.join(self.storage_path, f"{session_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存会话 {session_id} 时发生错误: {str(e)}")
    
    def _load_session(self, session_id):
        """从文件加载会话"""
        try:
            file_path = os.path.join(self.storage_path, f"{session_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载会话 {session_id} 时发生错误: {str(e)}")
        return None
        
    def acquire_session_lock(self, session_id, timeout=5.0):
        """获取会话锁"""
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
            logger.error(f"获取锁失败: {str(e)}")
            return False
        
    def release_session_lock(self, session_id):
        """释放会话锁"""
        try:
            if session_id in self._active_locks:
                self._active_locks.remove(session_id)
                
            if session_id in self._chat_locks:
                try:
                    self._chat_locks[session_id].release()
                except RuntimeError:
                    pass  # 忽略重复释放的错误
        except Exception as e:
            logger.error(f"释放锁失败: {str(e)}")
            
    def get_session(self, session_id):
        """获取会话"""
        if session_id in self.sessions:
            return self.sessions[session_id]
            
        # 尝试从文件加载
        session_data = self._load_session(session_id)
        if session_data:
            self.sessions[session_id] = session_data
            return session_data
            
        return None
        
    def create_session(self, metadata=None):
        """创建会话"""
        session_id = str(uuid.uuid4())
        if metadata is None:
            metadata = {}
        
        self.sessions[session_id] = {
            "session_id": session_id,
            "messages": [],
            "created_at": time.time(),
            "last_active": time.time(),
            "metadata": metadata
        }
        
        # 保存会话文件
        self._persist_session(session_id, self.sessions[session_id])
        return self.sessions[session_id]
        
    def get_interpreter(self, session_id):
        """获取解释器实例"""
        if session_id not in self.interpreter_instances:
            # 检查会话是否存在
            session = self.get_session(session_id)
            if not session:
                return None
                
            # 模拟创建解释器实例
            should_fail = session_id.endswith("fail")
            self.interpreter_instances[session_id] = MockInterpreter(
                should_fail=should_fail,
                should_save_on_error=True
            )
            # 设置初始状态
            self.instance_status[session_id] = 'idle'
            
        return self.interpreter_instances[session_id]
        
    def mark_instance_status(self, session_id, status):
        """标记实例状态"""
        with self._instances_lock:
            prev_status = self.instance_status.get(session_id, 'unknown')
            self.instance_status[session_id] = status
            logger.info(f"实例 {session_id} 状态从 {prev_status} 变为 {status}")
            
            # 更新会话使用时间
            self.instance_last_used[session_id] = time.time()
            
            # 如果是错误状态，更新会话元数据
            if status == 'error' and session_id in self.sessions:
                self.sessions[session_id]['metadata']['last_error'] = time.time()
                self.sessions[session_id]['metadata']['error_count'] = self.sessions[session_id]['metadata'].get('error_count', 0) + 1
                
                # 保存更新后的会话
                self._persist_session(session_id, self.sessions[session_id])

    def add_message(self, session_id, message):
        """添加消息到会话"""
        session = self.get_session(session_id)
        if not session:
            return False
            
        # 添加消息
        if 'messages' not in session:
            session['messages'] = []
        
        # 构造消息数据
        msg_data = {
            "role": message.get("role", "user"),
            "type": message.get("type", "message"),
            "content": message.get("content", ""),
            "created_at": time.time()
        }
        
        session['messages'].append(msg_data)
        session['last_active'] = time.time()
        
        # 保存会话
        self._persist_session(session_id, session)
        return True

# 模拟ChatService类
class ChatService:
    """模拟ChatService类，实现异常恢复功能"""
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.logger = logger
    
    def _get_or_create_session(self, session_id):
        """获取或创建会话"""
        return self.session_manager.get_or_create_session(session_id)
    
    def _acquire_session_lock(self, session_id):
        """获取会话锁"""
        return self.session_manager.acquire_session_lock(session_id)
    
    def _release_session_lock(self, session_id):
        """释放会话锁"""
        self.session_manager.release_session_lock(session_id)
    
    def _get_interpreter(self, session_id, model=None):
        """获取解释器实例"""
        return self.session_manager.get_interpreter(session_id)
    
    def _create_busy_response(self, session_id):
        """创建会话忙响应"""
        return {
            "error": {
                "message": "会话正忙，请稍后再试",
                "code": "session_busy"
            }
        }
    
    def process_streaming_chat(self, 
                              messages, 
                              session_id=None, 
                              model=None,
                              is_openai_format=False) -> Generator:
        """
        处理流式聊天请求的实现，添加异常恢复功能
        """
        lock_acquired = False
        try:
            # 1. 会话管理
            session_id, is_new_session = self._get_or_create_session(session_id)
            
            # 2. 获取会话锁
            if not self._acquire_session_lock(session_id):
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content="会话正忙，请稍后再试",
                    recipient='user'
                )
                yield format_stream_chunk(error_chunk)
                return
                
            lock_acquired = True
            self.logger.info(f"Session lock acquired for session {session_id}")
            
            # 3. 获取解释器实例
            interpreter = self._get_interpreter(session_id, model)
            if not interpreter:
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content="会话不存在或已过期",
                    recipient='user'
                )
                yield format_stream_chunk(error_chunk)
                return
                
            # 4. 标记实例为忙碌状态
            self.session_manager.mark_instance_status(session_id, 'busy')
            
            try:
                # 5. 处理消息并生成流式响应
                # 简化的消息处理
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    last_message_content = last_message.get('content', '')
                elif hasattr(last_message, 'content'):
                    last_message_content = last_message.content
                else:
                    last_message_content = str(last_message)
                
                # 添加消息到会话
                self.session_manager.add_message(session_id, {
                    "role": "user",
                    "content": last_message_content
                })
                
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
                        role=chunk.get('role', 'assistant'),
                        type=chunk.get('type', 'message'),
                        content=chunk.get('content', ''),
                        format=chunk.get('format'),
                        recipient='user',
                        id=chunk.get('id'),
                        start=chunk.get('start', False),
                        end=chunk.get('end', False)
                    )
                    yield format_stream_chunk(chunk_obj)
                
                # 流处理结束后，标记实例为空闲
                self.session_manager.mark_instance_status(session_id, 'idle')
                
            except Exception as e:
                # 处理过程中出错，标记实例为错误状态
                self.session_manager.mark_instance_status(session_id, 'error')
                self.logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
                
                # 修改：在异常情况下也添加错误消息到会话
                self.session_manager.add_message(session_id, {
                    "role": "assistant",
                    "type": "error",
                    "content": f"处理过程中发生错误: {str(e)}"
                })
                
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=str(e),
                    recipient='user'
                )
                yield format_stream_chunk(error_chunk)
                
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
            yield format_stream_chunk(error_chunk)
        finally:
            # 6. 释放会话锁
            if lock_acquired:
                self.logger.info(f"Releasing session lock for session {session_id}")
                self._release_session_lock(session_id)

# 测试函数
def test_normal_recovery():
    """测试正常情况下的会话保存和恢复"""
    logger.info("=== 开始测试: 正常情况下的会话保存和恢复 ===")
    
    # 创建会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建测试消息
    messages = [{"role": "user", "content": "这是一条测试消息"}]
    session_id = str(uuid.uuid4())
    
    logger.info(f"创建会话ID: {session_id}")
    
    # 处理第一条消息
    logger.info("发送第一条消息...")
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证状态和响应
    final_status = session_manager.instance_status.get(session_id)
    logger.info(f"处理后状态: {final_status}")
    logger.info(f"响应片段数量: {len(response_chunks)}")
    
    # 检查会话文件
    session_file = os.path.join(session_manager.storage_path, f"{session_id}.json")
    assert os.path.exists(session_file), f"会话文件应该存在: {session_file}"
    
    with open(session_file, 'r', encoding='utf-8') as f:
        saved_session = json.load(f)
        logger.info(f"会话文件内容: {json.dumps(saved_session, indent=2, ensure_ascii=False)}")
        
    # 验证会话锁已释放
    assert session_id not in session_manager._active_locks, "会话锁应该已释放"
    
    # 发送第二条消息
    logger.info("发送第二条消息...")
    messages = [{"role": "user", "content": "这是第二条消息"}]
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证状态和响应
    final_status = session_manager.instance_status.get(session_id)
    logger.info(f"处理后状态: {final_status}")
    logger.info(f"响应片段数量: {len(response_chunks)}")
    
    # 再次检查会话文件
    with open(session_file, 'r', encoding='utf-8') as f:
        saved_session = json.load(f)
        logger.info(f"更新后的会话消息数量: {len(saved_session.get('messages', []))}")
        
    # 验证结果
    assert final_status == 'idle', f"预期状态为'idle'，实际为'{final_status}'"
    assert len(response_chunks) > 0, "应该收到至少一个响应片段"
    assert session_id not in session_manager._active_locks, "会话锁应该被释放"
    assert len(saved_session.get('messages', [])) >= 2, "会话应该包含至少两条消息"
    
    logger.info("✅ 正常情况下的会话保存和恢复测试通过")

def test_error_recovery():
    """测试错误情况下的会话保存和恢复"""
    logger.info("=== 开始测试: 错误情况下的会话保存和恢复 ===")
    
    # 创建会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建测试消息和会话ID (故意使用会导致失败的ID)
    messages = [{"role": "user", "content": "这是一条会导致失败的消息"}]
    session_id = f"test-fail-{str(uuid.uuid4())}"
    
    logger.info(f"创建会话ID: {session_id}")
    
    # 处理消息（预期会失败）
    logger.info("发送消息（预期会失败）...")
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证状态和响应
    final_status = session_manager.instance_status.get(session_id)
    logger.info(f"处理后状态: {final_status}")
    logger.info(f"响应片段数量: {len(response_chunks)}")
    
    # 检查会话文件
    session_file = os.path.join(session_manager.storage_path, f"{session_id}.json")
    assert os.path.exists(session_file), f"会话文件应该存在: {session_file}"
    
    with open(session_file, 'r', encoding='utf-8') as f:
        saved_session = json.load(f)
        logger.info(f"会话文件内容: {json.dumps(saved_session, indent=2, ensure_ascii=False)}")
        
    # 验证元数据中包含错误信息
    assert 'last_error' in saved_session.get('metadata', {}), "会话元数据应该包含错误信息"
    assert 'error_count' in saved_session.get('metadata', {}), "会话元数据应该包含错误计数"
    
    # 验证会话锁已释放
    assert session_id not in session_manager._active_locks, "会话锁应该已释放"
    
    # 验证状态被标记为错误
    assert final_status == 'error', f"预期状态为'error'，实际为'{final_status}'"
    
    # 尝试恢复并发送新消息（使用非失败ID）
    new_session_id = session_id.replace("fail", "recover")
    old_messages = saved_session.get('messages', [])
    
    # 创建一个新会话，并导入之前的消息
    logger.info(f"创建新会话: {new_session_id}，并导入之前的消息")
    session_manager.get_or_create_session(new_session_id)
    
    # 添加旧消息
    for msg in old_messages:
        session_manager.add_message(new_session_id, msg)
    
    # 发送新消息
    logger.info("发送新消息到恢复的会话...")
    messages = [{"role": "user", "content": "这是恢复后的新消息"}]
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=new_session_id
    ))
    
    # 验证状态和响应
    final_status = session_manager.instance_status.get(new_session_id)
    logger.info(f"处理后状态: {final_status}")
    logger.info(f"响应片段数量: {len(response_chunks)}")
    
    # 检查新会话文件
    new_session_file = os.path.join(session_manager.storage_path, f"{new_session_id}.json")
    with open(new_session_file, 'r', encoding='utf-8') as f:
        new_saved_session = json.load(f)
        logger.info(f"恢复后的会话消息数量: {len(new_saved_session.get('messages', []))}")
    
    # 验证结果
    assert final_status == 'idle', f"预期状态为'idle'，实际为'{final_status}'"
    assert len(response_chunks) > 0, "应该收到至少一个响应片段"
    assert new_session_id not in session_manager._active_locks, "会话锁应该被释放"
    assert len(new_saved_session.get('messages', [])) > len(old_messages), "恢复的会话应该包含更多消息"
    
    logger.info("✅ 错误情况下的会话保存和恢复测试通过")

def test_concurrent_recovery():
    """测试并发情况下的错误恢复"""
    logger.info("=== 开始测试: 并发情况下的错误恢复 ===")
    
    # 创建会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建基本会话ID
    base_session_id = str(uuid.uuid4())
    logger.info(f"基本会话ID: {base_session_id}")
    
    # 定义测试函数
    def process_message(index, should_fail=False):
        try:
            # 构造会话ID
            if should_fail:
                session_id = f"{base_session_id}-fail-{index}"
            else:
                session_id = f"{base_session_id}-{index}"
                
            logger.info(f"线程 {index} 使用会话ID: {session_id}")
            
            # 构造消息
            messages = [{"role": "user", "content": f"线程 {index} 的测试消息"}]
            
            # 处理消息
            response_chunks = list(chat_service.process_streaming_chat(
                messages=messages,
                session_id=session_id
            ))
            
            # 验证状态
            final_status = session_manager.instance_status.get(session_id)
            expected_status = 'error' if should_fail else 'idle'
            
            logger.info(f"线程 {index} 最终状态: {final_status}")
            assert final_status == expected_status, f"线程 {index} 预期状态为 {expected_status}，实际为 {final_status}"
            assert session_id not in session_manager._active_locks, f"线程 {index} 的会话锁应该已释放"
            
            # 检查会话文件
            session_file = os.path.join(session_manager.storage_path, f"{session_id}.json")
            assert os.path.exists(session_file), f"线程 {index} 的会话文件应该存在"
            
        except Exception as e:
            logger.error(f"线程 {index} 发生错误: {str(e)}")
            assert False, f"线程 {index} 不应该发生错误"
    
    # 创建多个线程同时处理
    threads = []
    for i in range(5):
        should_fail = (i % 2 == 0)  # 偶数索引的线程会失败
        t = threading.Thread(target=process_message, args=(i, should_fail))
        threads.append(t)
    
    # 启动线程
    for t in threads:
        t.start()
        time.sleep(0.1)  # 稍微错开启动时间
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    # 验证所有会话锁都已释放
    for i in range(5):
        if i % 2 == 0:
            session_id = f"{base_session_id}-fail-{i}"
        else:
            session_id = f"{base_session_id}-{i}"
            
        assert session_id not in session_manager._active_locks, f"会话 {session_id} 的锁应该已释放"
    
    logger.info("✅ 并发情况下的错误恢复测试通过")

if __name__ == "__main__":
    try:
        # 运行测试
        test_normal_recovery()
        test_error_recovery()
        test_concurrent_recovery()
        
        # 总结
        logger.info("✅✅✅ 所有异常恢复测试通过!")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        sys.exit(1) 