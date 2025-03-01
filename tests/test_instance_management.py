#!/usr/bin/env python3
"""
实例管理测试脚本
用于验证实例管理修复的效果
"""

import sys
import os
import time
import logging
import threading
import uuid
import json
import signal
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入需要测试的模块
from interpreter.server.instance_manager import InterpreterInstanceManager
from interpreter.server.session import SessionManager

# 定义超时装饰器
class TimeoutError(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """
    设置操作的时间限制
    """
    def signal_handler(signum, frame):
        raise TimeoutError(f"操作超时（{seconds}秒）")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

class MockInterpreter:
    """模拟解释器类"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.closed = False
        logger.info(f"创建模拟解释器 {session_id}")
        
    def close(self):
        """关闭解释器"""
        self.closed = True
        logger.info(f"关闭模拟解释器 {self.session_id}")
        
    def chat(self, message: str, stream: bool = True):
        """模拟聊天功能"""
        if stream:
            for i in range(3):
                yield f"模拟响应 {i} 来自 {self.session_id}"
                time.sleep(0.1)
        else:
            return f"模拟响应来自 {self.session_id}"

def test_instance_manager():
    """测试实例管理器功能"""
    logger.info("开始测试实例管理器")
    
    # 创建实例管理器，设置最大实例数为3
    instance_manager = InterpreterInstanceManager(max_active_instances=3)
    
    try:
        with time_limit(60):  # 设置60秒超时
            # 修改_create_new_interpreter方法，使用MockInterpreter
            original_create_interpreter = instance_manager._create_new_interpreter
            def mock_create_interpreter(session_id):
                return MockInterpreter(session_id)
            instance_manager._create_new_interpreter = mock_create_interpreter
            
            # 模拟创建5个实例
            session_ids = []
            for i in range(5):
                # 创建会话ID
                session_id = str(uuid.uuid4())
                session_ids.append(session_id)
                
                try:
                    # 创建实例
                    instance_manager.create_instance(session_id)
                    
                    # 标记为忙碌状态
                    instance_manager.mark_instance_status(session_id, 'busy')
                    
                    logger.info(f"创建实例 {i+1}: {session_id}")
                except Exception as e:
                    logger.error(f"创建实例 {i+1} 失败: {str(e)}")
            
            # 检查实例数量
            instance_count = len(instance_manager.interpreter_instances)
            logger.info(f"创建5个实例后，实际实例数量: {instance_count}")
            assert instance_count <= instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {instance_manager.max_active_instances}"
            
            # 检查实例状态
            active_instances = list(instance_manager.interpreter_instances.keys())
            logger.info(f"活跃实例列表: {active_instances}")
            
            for session_id in active_instances:
                if session_id in instance_manager.instance_status:
                    status = instance_manager.instance_status[session_id]
                    logger.info(f"实例 {session_id} 状态: {status}")
            
            # 模拟异常情况 - 将第一个实例标记为错误
            if active_instances:
                error_session_id = active_instances[0]
                instance_manager.mark_instance_status(error_session_id, 'error')
                logger.info(f"将实例 {error_session_id} 标记为错误状态")
                
                # 等待优化器执行完成
                time.sleep(1)
                
                # 检查错误状态的实例是否被清理
                if error_session_id in instance_manager.interpreter_instances:
                    logger.info("错误状态的实例未被自动清理，手动触发优化")
                    # 手动触发优化
                    instance_manager.optimize_instances()
                    # 再次等待优化器执行完成
                    time.sleep(1)
                
                # 创建新实例，确保触发优化器
                new_session_id = str(uuid.uuid4())
                instance_manager.create_instance(new_session_id)
                
                # 检查实例数量
                instance_count = len(instance_manager.interpreter_instances)
                logger.info(f"创建新实例后，实际实例数量: {instance_count}")
                assert instance_count <= instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {instance_manager.max_active_instances}"
                
                # 再次检查错误状态的实例是否被清理
                assert error_session_id not in instance_manager.interpreter_instances, f"错误状态的实例 {error_session_id} 未被清理"
                logger.info(f"确认错误状态的实例 {error_session_id} 已被清理")
            
            # 检查标记状态功能
            active_instances = list(instance_manager.interpreter_instances.keys())
            if active_instances:
                test_session_id = active_instances[0]
                # 标记为空闲
                instance_manager.mark_instance_status(test_session_id, 'idle')
                assert instance_manager.instance_status[test_session_id] == 'idle', "标记为空闲状态失败"
                # 标记为忙碌
                instance_manager.mark_instance_status(test_session_id, 'busy')
                assert instance_manager.instance_status[test_session_id] == 'busy', "标记为忙碌状态失败"
            
            # 模拟并发请求
            def concurrent_request(session_id: str):
                """模拟并发请求"""
                try:
                    # 创建实例
                    instance = instance_manager.get_instance(session_id)
                    if not instance:
                        logger.error(f"并发请求无法获取实例: {session_id}")
                        return
                    
                    # 标记为忙碌状态
                    instance_manager.mark_instance_status(session_id, 'busy')
                    
                    # 模拟处理
                    time.sleep(0.5)
                    
                    # 标记为空闲状态
                    instance_manager.mark_instance_status(session_id, 'idle')
                    
                    logger.info(f"并发请求 {session_id} 完成")
                except Exception as e:
                    logger.error(f"并发请求 {session_id} 出错: {str(e)}")
            
            # 创建5个并发请求（减少数量，避免请求过多）
            threads = []
            concurrent_session_ids = []
            for i in range(5):
                # 创建会话ID
                session_id = str(uuid.uuid4())
                concurrent_session_ids.append(session_id)
                
                # 创建线程
                thread = threading.Thread(target=concurrent_request, args=(session_id,))
                threads.append(thread)
            
            # 启动所有线程
            for thread in threads:
                thread.start()
                time.sleep(0.1)  # 稍微延迟，避免同时启动
            
            # 等待所有线程完成
            for thread in threads:
                thread.join(timeout=5)  # 设置超时，避免永久等待
            
            # 检查最终实例数量
            instance_count = len(instance_manager.interpreter_instances)
            logger.info(f"并发请求后，实际实例数量: {instance_count}")
            assert instance_count <= instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {instance_manager.max_active_instances}"
            
            # 检查活跃锁
            active_locks_count = len(instance_manager._active_locks)
            logger.info(f"活跃锁数量: {active_locks_count}")
            
            # 获取实例状态信息
            status_info = instance_manager.get_instances_status()
            logger.info(f"实例状态信息: {status_info}")

    except TimeoutError as e:
        logger.error(f"测试超时: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        raise
    finally:
        # 清理所有资源
        try:
            instance_manager.cleanup_all_resources()
            logger.info("清理测试资源完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    logger.info("实例管理器测试通过!")

def test_session_manager():
    """测试会话管理器的实例管理功能"""
    logger.info("开始测试会话管理器的实例管理功能")
    
    # 创建会话管理器，设置最大实例数为3
    session_manager = SessionManager(max_active_instances=3)
    
    try:
        with time_limit(60):  # 设置60秒超时
            # 修改实例管理器的_create_new_interpreter方法，使用MockInterpreter
            original_create_interpreter = session_manager.instance_manager._create_new_interpreter
            def mock_create_interpreter(session_id):
                return MockInterpreter(session_id)
            session_manager.instance_manager._create_new_interpreter = mock_create_interpreter
            
            # 模拟创建5个会话
            session_ids = []
            for i in range(5):
                try:
                    # 创建会话
                    session = session_manager.create_session({"test": True})
                    session_id = session["session_id"]
                    session_ids.append(session_id)
                    
                    # 标记为忙碌状态
                    session_manager.mark_instance_status(session_id, 'busy')
                    
                    logger.info(f"创建会话 {i+1}: {session_id}")
                except Exception as e:
                    logger.error(f"创建会话 {i+1} 失败: {str(e)}")
            
            # 检查实例数量
            instance_count = len(session_manager.instance_manager.interpreter_instances)
            logger.info(f"创建5个会话后，实际实例数量: {instance_count}")
            assert instance_count <= session_manager.instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {session_manager.instance_manager.max_active_instances}"
            
            # 检查实例状态
            active_instances = list(session_manager.instance_manager.interpreter_instances.keys())
            logger.info(f"活跃实例列表: {active_instances}")
            
            for session_id in active_instances:
                if session_id in session_manager.instance_manager.instance_status:
                    status = session_manager.instance_manager.instance_status[session_id]
                    logger.info(f"会话 {session_id} 状态: {status}")
            
            # 模拟异常情况
            if active_instances:
                error_session_id = active_instances[0]
                session_manager.mark_instance_status(error_session_id, 'error')
                logger.info(f"将会话 {error_session_id} 标记为错误状态")
                
                # 等待一小段时间，让优化线程有机会执行
                time.sleep(1)
                
                # 创建新会话，应该触发优化并清理错误状态的实例
                new_session = session_manager.create_session({"test": True})
                new_session_id = new_session["session_id"]
                
                # 检查实例数量
                instance_count = len(session_manager.instance_manager.interpreter_instances)
                logger.info(f"创建新会话后，实际实例数量: {instance_count}")
                assert instance_count <= session_manager.instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {session_manager.instance_manager.max_active_instances}"
                
                # 检查错误状态的实例是否被清理
                assert error_session_id not in session_manager.instance_manager.interpreter_instances, f"错误状态的实例 {error_session_id} 未被清理"
            
            # 获取实例状态信息
            status_info = session_manager.get_instances_status()
            logger.info(f"实例状态信息: {status_info}")
            
            # 测试锁获取和释放
            if active_instances:
                test_session_id = active_instances[0]
                # 尝试获取锁
                lock_acquired = session_manager.acquire_session_lock(test_session_id)
                assert lock_acquired, f"无法获取会话 {test_session_id} 的锁"
                
                # 释放锁
                session_manager.release_session_lock(test_session_id)
                
                # 再次获取锁
                lock_acquired = session_manager.acquire_session_lock(test_session_id)
                assert lock_acquired, f"释放锁后无法再次获取会话 {test_session_id} 的锁"
                
                # 释放锁
                session_manager.release_session_lock(test_session_id)
    
    except TimeoutError as e:
        logger.error(f"测试超时: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        raise
    finally:
        # 清理所有资源
        try:
            session_manager.instance_manager.cleanup_all_resources()
            logger.info("清理会话管理器测试资源完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    logger.info("会话管理器实例管理测试通过!")

def test_stress():
    """压力测试"""
    logger.info("开始压力测试")
    
    # 创建实例管理器，设置最大实例数为5（增加上限以便观察行为）
    instance_manager = InterpreterInstanceManager(max_active_instances=5)
    
    # 创建一个事件标志，用于通知所有线程停止工作
    stop_event = threading.Event()
    
    try:
        with time_limit(120):  # 设置120秒超时
            # 修改_create_new_interpreter方法，使用MockInterpreter
            original_create_interpreter = instance_manager._create_new_interpreter
            def mock_create_interpreter(session_id):
                # 模拟创建延迟
                time.sleep(0.1)
                return MockInterpreter(session_id)
            instance_manager._create_new_interpreter = mock_create_interpreter
            
            # 模拟高并发创建和释放
            def worker(worker_id: int):
                """工作线程，不断创建和释放实例"""
                try:
                    for i in range(10):  # 每个线程执行10次操作
                        # 检查是否被要求停止
                        if stop_event.is_set():
                            logger.info(f"工作线程 {worker_id} 收到停止信号，退出循环")
                            break
                            
                        # 创建唯一的会话ID
                        session_id = f"stress-{worker_id}-{i}-{uuid.uuid4()}"
                        
                        try:
                            # 检查线程池是否已关闭
                            with instance_manager.global_lock:
                                if instance_manager.executor_shutdown:
                                    logger.info(f"工作线程 {worker_id} 检测到线程池已关闭，退出")
                                    break
                            
                            # 尝试获取实例
                            instance = instance_manager.get_instance(session_id)
                            
                            # 如果获取实例失败，跳过后续操作
                            if not instance:
                                logger.warning(f"工作线程 {worker_id} 获取实例失败，跳过操作 {i}")
                                continue
                                
                            # 标记为忙碌
                            instance_manager.mark_instance_status(session_id, 'busy')
                            
                            # 模拟处理
                            time.sleep(0.2)
                            
                            # 检查是否被要求停止
                            if stop_event.is_set():
                                # 标记为错误，确保被清理
                                instance_manager.mark_instance_status(session_id, 'error')
                                break
                                
                            # 标记为空闲
                            instance_manager.mark_instance_status(session_id, 'idle')
                            
                            # 随机决定是否直接清理
                            if i % 3 == 0:
                                instance_manager._cleanup_instance(session_id)
                            
                            logger.debug(f"工作线程 {worker_id} 完成操作 {i}")
                        except RuntimeError as e:
                            # 如果收到线程池已关闭的异常，记录并退出
                            if "实例管理器已关闭" in str(e) or "cannot schedule new futures after shutdown" in str(e):
                                logger.info(f"工作线程 {worker_id} 检测到线程池已关闭: {str(e)}")
                                break
                            logger.error(f"工作线程 {worker_id} 操作 {i} 失败: {str(e)}")
                        except Exception as e:
                            logger.error(f"工作线程 {worker_id} 操作 {i} 失败: {str(e)}")
                            # 如果出现异常，尝试将实例标记为错误，以便被清理
                            try:
                                instance_manager.mark_instance_status(session_id, 'error')
                            except:
                                pass
                except Exception as e:
                    logger.error(f"工作线程 {worker_id} 出错: {str(e)}")
            
            # 创建20个工作线程
            worker_threads = []
            for i in range(10):  # 减少线程数，避免过度并发
                thread = threading.Thread(target=worker, args=(i,))
                worker_threads.append(thread)
            
            # 启动所有线程
            for thread in worker_threads:
                thread.start()
                time.sleep(0.05)  # 稍微错开启动时间
            
            # 定期检查状态
            check_times = 5
            for i in range(check_times):
                time.sleep(3)  # 每3秒检查一次
                
                # 获取当前状态
                instance_count = len(instance_manager.interpreter_instances)
                active_locks = len(instance_manager._active_locks)
                status_info = instance_manager.get_instances_status()
                
                logger.info(f"状态检查 {i+1}/{check_times}: 实例数={instance_count}, 活跃锁={active_locks}, 状态={status_info}")
                
                # 验证实例数量不超过最大限制
                assert instance_count <= instance_manager.max_active_instances, f"实例数量 {instance_count} 超过最大限制 {instance_manager.max_active_instances}"
            
            # 通知所有线程停止工作
            logger.info("发送停止信号给所有工作线程")
            stop_event.set()
            
            # 等待所有线程完成，但设置最长等待时间
            logger.info("等待所有工作线程结束...")
            for thread in worker_threads:
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning("部分工作线程未能在超时时间内结束")
            
            # 最终检查
            instance_count = len(instance_manager.interpreter_instances)
            active_locks = len(instance_manager._active_locks)
            logger.info(f"压力测试完成: 实例数={instance_count}, 活跃锁={active_locks}")
            
            # 验证最终状态
            assert instance_count <= instance_manager.max_active_instances, f"最终实例数量 {instance_count} 超过最大限制 {instance_manager.max_active_instances}"
    
    except TimeoutError as e:
        logger.error(f"压力测试超时: {str(e)}")
        # 通知所有线程停止
        stop_event.set()
        raise
    except Exception as e:
        logger.error(f"压力测试过程中出错: {str(e)}", exc_info=True)
        # 通知所有线程停止
        stop_event.set()
        raise
    finally:
        # 确保所有线程收到停止信号
        stop_event.set()
        
        # 清理所有资源
        try:
            # 在清理前再次等待所有线程结束
            for thread in worker_threads:
                if thread.is_alive():
                    thread.join(timeout=1)
                    
            # 清理所有资源
            instance_manager.cleanup_all_resources()
            logger.info("清理压力测试资源完成")
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    logger.info("压力测试通过!")

if __name__ == "__main__":
    try:
        logger.info("="*50)
        logger.info("开始实例管理测试套件")
        logger.info("="*50)
        
        logger.info("-"*50)
        test_instance_manager()
        logger.info("-"*50)
        
        logger.info("-"*50)
        test_session_manager()
        logger.info("-"*50)
        
        logger.info("-"*50)
        test_stress()
        logger.info("-"*50)
        
        logger.info("="*50)
        logger.info("所有测试通过!")
        logger.info("="*50)
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        sys.exit(1) 