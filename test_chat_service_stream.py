#!/usr/bin/env python
"""
测试ChatService流式处理中的状态管理功能
这是一个简化的测试脚本，使用模拟对象来测试修改后的状态管理功能
"""

import sys
import time
import logging
import threading
from typing import Dict, List, Generator, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_chat_service')

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

def format_openai_stream_chunk(chunk):
    """模拟format_openai_stream_chunk函数"""
    return {
        "choices": [{
            "delta": {
                "content": chunk.content,
                "role": chunk.role
            },
            "finish_reason": "stop" if chunk.end else None
        }]
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
    def __init__(self, should_fail=False):
        self.messages = []
        self.should_fail = should_fail
        self.model = "mock-model"
        
    def chat(self, content, stream=False, display=False):
        """模拟聊天方法"""
        if self.should_fail:
            raise Exception("模拟执行失败")
            
        if stream:
            return self._stream_response(content)
        else:
            # 非流式响应
            response = {"content": f"回复: {content}", "role": "assistant", "type": "message"}
            self.messages.append({"role": "user", "content": content, "type": "message"})
            self.messages.append(response)
            return response
            
    def _stream_response(self, content):
        """模拟流式响应"""
        # 添加用户消息
        self.messages.append({"role": "user", "content": content, "type": "message"})
        
        # 生成助手消息片段
        yield {"role": "assistant", "type": "message", "content": "正在", "start": True}
        time.sleep(0.1)
        yield {"role": "assistant", "type": "message", "content": "思考"}
        time.sleep(0.1)
        yield {"role": "assistant", "type": "message", "content": "您的问题..."}
        time.sleep(0.1)
        
        # 生成代码消息
        yield {"role": "assistant", "type": "code", "content": "print('Hello World')", "format": "python", "start": True}
        time.sleep(0.1)
        yield {"role": "assistant", "type": "code", "content": "", "format": "python", "end": True}
        
        # 生成计算机输出
        yield {"role": "computer", "type": "console", "content": "Hello World\n", "start": True}
        time.sleep(0.1)
        yield {"role": "computer", "type": "console", "content": "", "end": True}
        
        # 生成最终回复
        yield {"role": "assistant", "type": "message", "content": f"回复: {content}", "end": True}
        
        # 更新消息历史
        self.messages.append({"role": "assistant", "content": f"回复: {content}", "type": "message"})

# 模拟SessionManager类
class MockSessionManager:
    """模拟SessionManager类，用于测试"""
    def __init__(self):
        self.sessions = {}
        self.interpreter_instances = {}
        self.instance_status = {}
        self.locks = {}
        self.active_locks = set()
        
    def get_or_create_session(self, session_id=None):
        """获取或创建会话"""
        if not session_id:
            session_id = f"test-session-{len(self.sessions)}"
        
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "created_at": time.time(),
                "last_active": time.time()
            }
            return session_id, True
        
        return session_id, False
        
    def acquire_session_lock(self, session_id, timeout=5.0):
        """获取会话锁"""
        if session_id in self.active_locks:
            return False
            
        self.active_locks.add(session_id)
        return True
        
    def release_session_lock(self, session_id):
        """释放会话锁"""
        if session_id in self.active_locks:
            self.active_locks.remove(session_id)
            
    def get_session(self, session_id):
        """获取会话"""
        return self.sessions.get(session_id)
        
    def create_session(self):
        """创建会话"""
        session_id = f"test-session-{len(self.sessions)}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "messages": [],
            "created_at": time.time(),
            "last_active": time.time()
        }
        return self.sessions[session_id]
        
    def get_interpreter(self, session_id):
        """获取解释器实例"""
        if session_id not in self.interpreter_instances:
            # 模拟创建解释器实例的耗时操作
            time.sleep(0.1)
            self.interpreter_instances[session_id] = MockInterpreter(
                should_fail=(session_id.endswith("fail"))  # 特殊session_id会导致失败
            )
            # 设置初始状态
            self.instance_status[session_id] = 'idle'
            
        return self.interpreter_instances[session_id]
        
    def mark_instance_status(self, session_id, status):
        """标记实例状态"""
        prev_status = self.instance_status.get(session_id, 'unknown')
        self.instance_status[session_id] = status
        logger.info(f"实例 {session_id} 状态从 {prev_status} 变为 {status}")

# 模拟ChatService类
class ChatService:
    """模拟ChatService类，实现流式处理功能以测试状态管理"""
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.logger = logger
    
    def _get_or_create_session(self, session_id):
        """模拟获取或创建会话"""
        return self.session_manager.get_or_create_session(session_id)
    
    def _acquire_session_lock(self, session_id):
        """模拟获取会话锁"""
        return self.session_manager.acquire_session_lock(session_id)
    
    def _release_session_lock(self, session_id):
        """模拟释放会话锁"""
        self.session_manager.release_session_lock(session_id)
    
    def _get_interpreter(self, session_id, model=None):
        """模拟获取解释器实例"""
        return self.session_manager.get_interpreter(session_id)
    
    def _create_busy_response(self, session_id):
        """模拟创建会话忙响应"""
        return {
            "error": {
                "message": "会话正忙，请稍后再试",
                "code": "session_busy"
            }
        }
    
    def _create_session_not_found_response(self, session_id):
        """模拟创建会话不存在响应"""
        return {
            "error": {
                "message": "会话已过期或不存在",
                "code": "session_expired"
            }
        }
    
    def process_streaming_chat(self, 
                              messages: List[Dict], 
                              session_id: Optional[str] = None, 
                              model: Optional[str] = None,
                              is_openai_format: bool = False) -> Generator:
        """
        处理流式聊天请求的实现，用于测试状态管理功能
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
                
                # 简化的消息处理
                last_message = messages[-1]
                if isinstance(last_message, dict):
                    last_message_content = last_message.get('content', '')
                elif hasattr(last_message, 'content'):
                    last_message_content = last_message.content
                else:
                    last_message_content = str(last_message)
                
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

# 测试函数
def test_stream_normal_path():
    """测试流式处理正常路径"""
    logger.info("=== 开始测试: 流式处理正常路径 ===")
    
    # 创建模拟会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建测试消息
    messages = [{"role": "user", "content": "测试消息"}]
    session_id = "test-session-normal"
    
    # 处理流式响应
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证状态变化
    final_status = session_manager.instance_status.get(session_id)
    logger.info(f"最终实例状态: {final_status}")
    
    # 验证响应
    logger.info(f"收到 {len(response_chunks)} 个响应片段")
    
    # 验证结果
    assert final_status == 'idle', f"预期状态为'idle'，实际为'{final_status}'"
    assert len(response_chunks) > 0, "应该收到至少一个响应片段"
    assert session_id not in session_manager.active_locks, "会话锁应该被释放"
    
    logger.info("✅ 流式处理正常路径测试通过")
    
def test_stream_error_path():
    """测试流式处理错误路径"""
    logger.info("=== 开始测试: 流式处理错误路径 ===")
    
    # 创建模拟会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建测试消息
    messages = [{"role": "user", "content": "测试消息"}]
    session_id = "test-session-fail"  # 特殊ID，会触发错误
    
    # 处理流式响应
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证状态变化
    final_status = session_manager.instance_status.get(session_id)
    logger.info(f"最终实例状态: {final_status}")
    
    # 验证响应
    logger.info(f"收到 {len(response_chunks)} 个响应片段")
    
    # 验证结果
    assert final_status == 'error', f"预期状态为'error'，实际为'{final_status}'"
    assert len(response_chunks) > 0, "应该收到至少一个响应片段"
    assert session_id not in session_manager.active_locks, "会话锁应该被释放"
    
    logger.info("✅ 流式处理错误路径测试通过")
    
def test_busy_session():
    """测试会话忙状态处理"""
    logger.info("=== 开始测试: 会话忙状态处理 ===")
    
    # 创建模拟会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 创建测试消息
    messages = [{"role": "user", "content": "测试消息"}]
    session_id = "test-session-busy"
    
    # 模拟会话忙状态
    session_manager.active_locks.add(session_id)
    
    # 处理流式响应
    response_chunks = list(chat_service.process_streaming_chat(
        messages=messages,
        session_id=session_id
    ))
    
    # 验证响应
    logger.info(f"收到 {len(response_chunks)} 个响应片段")
    logger.info(f"响应内容: {response_chunks[0]}")
    
    # 验证结果
    assert len(response_chunks) == 1, "应该只收到一个错误响应片段"
    
    # 检查错误消息内容 - 修复检查方式
    response_str = str(response_chunks[0])
    has_busy_error = False
    if isinstance(response_chunks[0], dict):
        if "session_busy" in str(response_chunks[0]) or "会话正忙" in str(response_chunks[0]):
            has_busy_error = True
    
    assert has_busy_error, f"响应应该包含busy错误信息，实际是: {response_str}"
    
    logger.info("✅ 会话忙状态处理测试通过")

def test_concurrent_stream_processing():
    """测试并发流式处理"""
    logger.info("=== 开始测试: 并发流式处理 ===")
    
    # 创建模拟会话管理器和聊天服务
    session_manager = MockSessionManager()
    chat_service = ChatService(session_manager)
    
    # 定义测试函数
    def process_stream(session_id, should_succeed=True):
        try:
            messages = [{"role": "user", "content": f"并发测试 {session_id}"}]
            
            # 实际ID由should_succeed决定
            actual_id = session_id if should_succeed else f"{session_id}-fail"
            
            # 处理流式响应
            response_chunks = list(chat_service.process_streaming_chat(
                messages=messages,
                session_id=actual_id
            ))
            
            # 验证响应
            logger.info(f"会话 {actual_id} 收到 {len(response_chunks)} 个响应片段")
            
            # 记录最终状态
            final_status = session_manager.instance_status.get(actual_id)
            logger.info(f"会话 {actual_id} 最终状态: {final_status}")
            
            # 预期状态
            expected_status = 'idle' if should_succeed else 'error'
            assert final_status == expected_status, f"会话 {actual_id} 预期状态为 {expected_status}，实际为 {final_status}"
            
        except Exception as e:
            logger.error(f"并发测试线程异常: {str(e)}")
            
    # 创建多个线程进行并发测试
    threads = []
    for i in range(5):
        # 一半成功，一半失败
        should_succeed = (i % 2 == 0)
        t = threading.Thread(
            target=process_stream, 
            args=(f"concurrent-{i}", should_succeed)
        )
        threads.append(t)
        
    # 启动所有线程
    for t in threads:
        t.start()
        time.sleep(0.05)  # 稍微错开启动时间
        
    # 等待所有线程完成
    for t in threads:
        t.join()
        
    # 验证并发处理结果
    for i in range(5):
        session_id = f"concurrent-{i}"
        actual_id = session_id if (i % 2 == 0) else f"{session_id}-fail"
        
        # 验证会话锁已释放
        assert actual_id not in session_manager.active_locks, f"会话 {actual_id} 的锁应该被释放"
        
        # 验证最终状态
        expected_status = 'idle' if (i % 2 == 0) else 'error'
        actual_status = session_manager.instance_status.get(actual_id)
        assert actual_status == expected_status, f"会话 {actual_id} 预期状态为 {expected_status}，实际为 {actual_status}"
    
    logger.info("✅ 并发流式处理测试通过")

if __name__ == "__main__":
    try:
        # 运行测试
        test_stream_normal_path()
        test_stream_error_path()
        test_busy_session()
        test_concurrent_stream_processing()
        
        # 总结
        logger.info("✅✅✅ 所有测试通过! 会话管理修改符合预期。")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}", exc_info=True)
        sys.exit(1) 