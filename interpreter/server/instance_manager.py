import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Set
from concurrent.futures import ThreadPoolExecutor

# 获取logger实例
logger = logging.getLogger('interpreter_server')

class InterpreterInstanceManager:
    """
    解释器实例管理工具类
    
    负责管理解释器实例的创建、获取和清理，确保实例数量不超过最大限制
    使用ThreadPoolExecutor来管理实例资源，避免创建过多实例
    """
    
    def __init__(self, max_active_instances: int = 3, instance_timeout: int = 3600, session_manager=None):
        """
        初始化实例管理器
        
        Args:
            max_active_instances: 最大活跃实例数量
            instance_timeout: 实例超时时间（秒）
            session_manager: 会话管理器实例，用于获取 session 配置
        """
        self.max_active_instances = max_active_instances
        self.instance_timeout = instance_timeout
        self.session_manager = session_manager
        
        # 实例存储
        self.interpreter_instances: Dict[str, Any] = {}
        self.instance_last_used: Dict[str, float] = {}
        self.instance_status: Dict[str, str] = {}  # 'idle', 'busy', 'error'
        
        # 锁管理
        self._active_locks: Set[str] = set()
        self._instance_locks: Dict[str, threading.Lock] = {}
        self.global_lock = threading.RLock()  # 使用可重入锁避免同一线程死锁
        
        # 线程池执行器 - 用于限制并发实例数量
        self.executor = ThreadPoolExecutor(max_workers=max_active_instances)
        self.executor_shutdown = False  # 标记线程池是否已关闭
        
        # 优化器锁 - 避免多个优化器同时运行
        self.optimizer_lock = threading.Lock()
        self.is_optimizing = False
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_instances, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"实例管理器初始化完成，最大实例数: {max_active_instances}")
    
    def set_session_manager(self, session_manager):
        """设置会话管理器，避免循环依赖"""
        self.session_manager = session_manager
    
    def create_instance(self, session_id: str) -> Any:
        """
        创建新的解释器实例
        
        Args:
            session_id: 会话ID
            
        Returns:
            解释器实例
        """
        # 检查并优化现有实例
        current_count = 0
        instance_to_force_cleanup = None
        
        with self.global_lock:
            # 检查线程池是否已关闭
            if self.executor_shutdown:
                logger.warning("线程池已关闭，无法创建新实例")
                raise RuntimeError("实例管理器已关闭，无法创建新实例")
                
            # 检查当前实例数量
            current_count = len(self.interpreter_instances)
            logger.info(f"创建实例前数量: {current_count}, 最大限制: {self.max_active_instances}")
            
            # 如果当前实例数量已达到或超过最大限制，准备清理
            if current_count >= self.max_active_instances:
                # 找出可清理的实例ID
                if self.instance_last_used:
                    oldest_session = min(self.instance_last_used.items(), key=lambda x: x[1])[0]
                    instance_to_force_cleanup = oldest_session
        
        # 如果需要清理实例，在锁外执行
        if instance_to_force_cleanup and current_count >= self.max_active_instances:
            # 先尝试优化实例
            logger.info(f"触发实例优化，当前实例数: {current_count}")
            self.optimize_instances()
            
            # 获取优化后的实例数
            with self.global_lock:
                current_count = len(self.interpreter_instances)
            
            # 如果数量还是超过限制，强制清理最早的实例
            if current_count >= self.max_active_instances and instance_to_force_cleanup:
                logger.info(f"强制清理最早使用的实例: {instance_to_force_cleanup}")
                self._cleanup_instance(instance_to_force_cleanup, force=True)
        
        try:
            # 确保线程池未关闭
            with self.global_lock:
                if self.executor_shutdown:
                    logger.warning("线程池已关闭，无法创建新实例")
                    raise RuntimeError("实例管理器已关闭，无法创建新实例")
            
            # 直接创建解释器，而非在线程池中创建
            # 这样可以避免线程池关闭时的异常
            try:
                interpreter_instance = self._create_new_interpreter(session_id)
                
                # 获取锁并保存实例信息
                with self.global_lock:
                    if not self.executor_shutdown:  # 再次检查，避免在创建过程中executor被关闭
                        self.interpreter_instances[session_id] = interpreter_instance
                        self.instance_last_used[session_id] = time.time()
                        self.instance_status[session_id] = 'idle'
                        current_count = len(self.interpreter_instances)
                        logger.info(f"为会话 {session_id} 创建了新实例，当前实例数: {current_count}")
                        return interpreter_instance
                    else:
                        # 如果创建过程中线程池被关闭，则关闭实例并抛出异常
                        logger.warning("实例创建过程中线程池被关闭")
                        if hasattr(interpreter_instance, 'close') and callable(getattr(interpreter_instance, 'close')):
                            interpreter_instance.close()
                        raise RuntimeError("实例管理器已关闭，无法保存新实例")
                
            except Exception as e:
                logger.error(f"创建解释器实例失败: {str(e)}", exc_info=True)
                raise
            
        except Exception as e:
            logger.error(f"创建实例失败: {str(e)}", exc_info=True)
            # 记录错误状态
            with self.global_lock:
                if not self.executor_shutdown:
                    self.instance_status[session_id] = 'error'
            raise
    
    def get_instance(self, session_id: str) -> Optional[Any]:
        """
        获取会话对应的解释器实例
        
        Args:
            session_id: 会话ID
            
        Returns:
            解释器实例，如果不存在则返回None
        """
        # 快速路径：检查实例是否存在
        interpreter = None
        
        with self.global_lock:
            # 检查线程池是否已关闭
            if self.executor_shutdown:
                logger.warning("线程池已关闭，无法获取实例")
                return None
                
            interpreter = self.interpreter_instances.get(session_id)
            if interpreter is not None:
                self.instance_last_used[session_id] = time.time()
                # 更新状态（但不覆盖busy状态）
                if self.instance_status.get(session_id) != 'busy':
                    self.instance_status[session_id] = 'idle'
        
        if interpreter is not None:
            return interpreter
        
        # 慢路径：需要创建新实例
        logger.info(f"为会话 {session_id} 创建新的解释器实例")
        return self.create_instance(session_id)
    
    def mark_instance_status(self, session_id: str, status: str) -> None:
        """
        标记实例状态
        
        Args:
            session_id: 会话ID
            status: 状态，可选值: 'idle', 'busy', 'error'
        """
        if not session_id:
            logger.warning("尝试标记空会话ID的实例状态")
            return
            
        if status not in ['idle', 'busy', 'error']:
            logger.warning(f"尝试将实例状态标记为未知状态: {status}")
            status = 'error'  # 默认为错误状态
        
        needs_optimize = False
        
        with self.global_lock:
            # 检查实例是否存在
            if session_id not in self.interpreter_instances:
                logger.warning(f"尝试标记不存在的实例状态: {session_id}")
                return
                
            # 更新状态
            self.instance_status[session_id] = status
            logger.info(f"将实例 {session_id} 状态标记为 {status}")
            
            # 更新最后使用时间
            self.instance_last_used[session_id] = time.time()
            
            # 如果状态为error，立即清理
            if status == 'error':
                # 在锁外清理，保存引用
                cleanup_session_id = session_id
                needs_optimize = False  # 不需要优化，直接清理
            # 如果状态为idle，需要优化实例数量
            elif status == 'idle':
                needs_optimize = True
        
        # 如果是错误状态，立即清理
        if status == 'error' and 'cleanup_session_id' in locals():
            logger.info(f"立即清理错误状态实例: {cleanup_session_id}")
            try:
                # 直接清理，不使用线程池
                self._cleanup_instance(cleanup_session_id, True)
            except Exception as e:
                logger.error(f"清理错误状态实例失败: {str(e)}", exc_info=True)
        # 在锁外启动优化，避免死锁
        elif needs_optimize:
            try:
                # 直接执行优化，不使用线程池
                if not self.executor_shutdown:
                    threading.Thread(target=self.optimize_instances, daemon=True).start()
            except Exception as e:
                logger.error(f"启动优化线程失败: {str(e)}", exc_info=True)
    
    def acquire_instance_lock(self, session_id: str, timeout: float = 5.0) -> bool:
        """
        获取实例锁
        
        Args:
            session_id: 会话ID
            timeout: 超时时间（秒）
            
        Returns:
            是否成功获取锁
        """
        try:
            lock_is_active = False
            
            with self.global_lock:
                # 检查线程池是否已关闭
                if self.executor_shutdown:
                    logger.warning("线程池已关闭，无法获取实例锁")
                    return False
                    
                lock_is_active = session_id in self._active_locks
                # 检查是否超时
                if lock_is_active:
                    lock_time = self.instance_last_used.get(session_id, 0)
                    if time.time() - lock_time > 30:  # 30秒锁超时
                        logger.warning(f"锁超时自动释放: {session_id}")
                        self._active_locks.remove(session_id)
                        lock_is_active = False
                    else:
                        return False

                # 创建锁对象（如果不存在）
                if session_id not in self._instance_locks:
                    self._instance_locks[session_id] = threading.Lock()
            
            # 如果锁已激活，直接返回失败
            if lock_is_active:
                return False
                
            # 记录锁获取开始时间
            lock_acquire_start = time.time()
            
            # 获取实例锁对象（不需要在全局锁内）
            instance_lock = None
            with self.global_lock:
                instance_lock = self._instance_locks.get(session_id)
                
            if not instance_lock:
                logger.error(f"无法获取实例锁对象: {session_id}")
                return False
            
            # 尝试获取锁（在全局锁外）
            if instance_lock.acquire(timeout=timeout):
                lock_acquire_time = time.time() - lock_acquire_start
                logger.debug(f"获取锁耗时: {lock_acquire_time:.4f}秒")
                
                # 标记锁已激活
                with self.global_lock:
                    if not self.executor_shutdown:  # 再次检查，避免在获取锁过程中executor被关闭
                        self._active_locks.add(session_id)
                        self.instance_last_used[session_id] = time.time()
                        return True
                    else:
                        # 如果获取锁过程中线程池被关闭，则释放锁并返回失败
                        try:
                            instance_lock.release()
                        except RuntimeError:
                            pass  # 忽略重复释放的错误
                        logger.warning("获取锁过程中线程池被关闭")
                        return False
            else:
                logger.warning(f"无法在{timeout}秒内获取锁: {session_id}")
            return False
            
        except Exception as e:
            logger.error(f"锁获取失败: {str(e)}")
            return False
    
    def release_instance_lock(self, session_id: str) -> None:
        """
        释放实例锁
        
        Args:
            session_id: 会话ID
        """
        try:
            instance_lock = None
            should_release = False
            
            with self.global_lock:
                if session_id in self._active_locks:
                    self._active_locks.remove(session_id)
                    should_release = True
                    
                if session_id in self._instance_locks:
                    instance_lock = self._instance_locks[session_id]
            
            # 在全局锁外释放实例锁
            if should_release and instance_lock:
                try:
                    instance_lock.release()
                except RuntimeError:
                    pass  # 忽略重复释放的错误
                
        except Exception as e:
            logger.error(f"锁释放失败: {str(e)}")
    
    def optimize_instances(self, current_session_id: Optional[str] = None) -> bool:
        """
        优化解释器实例，确保不超过最大限制
        
        Args:
            current_session_id: 当前会话ID，避免清理当前会话的实例
            
        Returns:
            是否成功优化实例数量
        """
        # 使用优化器锁，确保同一时间只有一个优化过程
        if not self.optimizer_lock.acquire(blocking=False):
            logger.debug("已有优化进程在运行，跳过此次优化")
            return False
            
        try:
            # 检查线程池是否已关闭
            with self.global_lock:
                if self.executor_shutdown:
                    logger.warning("线程池已关闭，跳过优化")
                    return False
                    
            self.is_optimizing = True
            
            # 最大尝试次数和计数器
            max_attempts = 5
            attempt = 0
            success = False
            
            # 初始检查
            with self.global_lock:
                current_count = len(self.interpreter_instances)
                logger.info(f"当前实例数量: {current_count}, 最大限制: {self.max_active_instances}")
                
                # 如果实例数量已经在限制内，直接返回成功
                if current_count <= self.max_active_instances:
                    return True
                
                # 检查是否有错误状态的实例需要优先清理
                error_instances = [
                    session_id for session_id, status in self.instance_status.items()
                    if status == 'error' and session_id != current_session_id
                ]
                
                # 如果有错误状态的实例，优先清理它们
                if error_instances:
                    for error_session_id in error_instances:
                        logger.info(f"优先清理错误状态实例: {error_session_id}")
                        # 在锁外执行清理需要保存引用
                        error_session_to_clean = error_session_id
            
            # 如果有错误状态的实例，优先清理
            if 'error_session_to_clean' in locals():
                cleanup_success = self._cleanup_instance(error_session_to_clean, force=True)
                if cleanup_success:
                    # 检查清理后的实例数量
                    with self.global_lock:
                        current_count = len(self.interpreter_instances)
                        if current_count <= self.max_active_instances:
                            return True
            
            # 优化循环
            while attempt < max_attempts:
                # 检查线程池是否已关闭
                with self.global_lock:
                    if self.executor_shutdown:
                        logger.warning("线程池已关闭，中断优化")
                        return False
                        
                attempt += 1
                logger.info(f"尝试清理实例 (尝试 {attempt}/{max_attempts})")
                
                # 获取需要清理的实例ID
                session_id_to_clean = None
                
                with self.global_lock:
                    current_count = len(self.interpreter_instances)
                    if current_count <= self.max_active_instances:
                        success = True
                        break
                        
                    # 首先尝试清理错误状态的实例
                    error_instances = [
                        session_id for session_id, status in self.instance_status.items()
                        if status == 'error' and session_id != current_session_id
                    ]
                    
                    if error_instances:
                        session_id_to_clean = error_instances[0]
                        logger.info(f"准备清理错误状态实例: {session_id_to_clean}")
                    else:
                        # 其次清理空闲实例
                        idle_instances = [
                            session_id for session_id, status in self.instance_status.items()
                            if status == 'idle' and session_id != current_session_id
                        ]
                        
                        if idle_instances:
                            # 按最后使用时间排序
                            idle_instances.sort(
                                key=lambda x: self.instance_last_used.get(x, 0)
                            )
                            session_id_to_clean = idle_instances[0]
                            logger.info(f"准备清理空闲实例: {session_id_to_clean}")
                        elif len(self.interpreter_instances) > 1:
                            # 最后清理最早使用的实例（如果不是当前会话）
                            instances_to_clean = [
                                session_id for session_id in self.interpreter_instances.keys()
                                if session_id != current_session_id
                            ]
                            
                            if instances_to_clean:
                                instances_to_clean.sort(
                                    key=lambda x: self.instance_last_used.get(x, 0)
                                )
                                session_id_to_clean = instances_to_clean[0]
                                logger.info(f"准备强制清理最早使用的实例: {session_id_to_clean}")
                            else:
                                logger.warning("无法清理更多实例，所有实例都是当前会话")
                                break
                        else:
                            logger.warning("无法清理更多实例，实例数量已是最小")
                            break
                
                # 在锁外执行清理
                if session_id_to_clean:
                    # 根据实例状态决定是否强制清理
                    force_cleanup = False
                    with self.global_lock:
                        status = self.instance_status.get(session_id_to_clean)
                        force_cleanup = status == 'error' or status == 'busy'
                    
                    # 执行清理
                    cleanup_success = self._cleanup_instance(session_id_to_clean, force=force_cleanup)
                    if not cleanup_success:
                        logger.warning(f"清理实例 {session_id_to_clean} 失败")
                
                # 检查清理后的实例数量
                with self.global_lock:
                    new_count = len(self.interpreter_instances)
                    if new_count >= current_count:
                        logger.warning(f"无法减少实例数量 ({new_count} >= {current_count})，尝试其他方式")
                    else:
                        logger.info(f"清理后实例数量: {new_count}")
                        # 如果实例数量已经在限制内，结束循环
                        if new_count <= self.max_active_instances:
                            success = True
                            break
                        current_count = new_count
            
            # 最终检查
            with self.global_lock:
                success = len(self.interpreter_instances) <= self.max_active_instances
                
            return success
            
        except Exception as e:
            logger.error(f"优化解释器实例时出错: {str(e)}", exc_info=True)
            return False
        finally:
            self.is_optimizing = False
            self.optimizer_lock.release()
    
    def _cleanup_instance(self, session_id: str, force: bool = False) -> bool:
        """
        清理指定会话的解释器实例
        
        Args:
            session_id: 会话ID
            force: 是否强制清理，即使实例状态为busy
            
        Returns:
            是否成功清理实例
        """
        try:
            # 检查实例状态
            can_cleanup = force
            interpreter = None
            
            with self.global_lock:
                # 如果不是强制清理，检查状态
                if not force and session_id in self.instance_status:
                    can_cleanup = self.instance_status[session_id] != 'busy'
                    
                if not can_cleanup:
                    logger.warning(f"实例 {session_id} 正忙，跳过清理")
                    return False
                
                # 获取实例对象
                if session_id in self.interpreter_instances:
                    interpreter = self.interpreter_instances[session_id]
                    # 从字典中删除（即使关闭失败，也需要从字典中删除）
                    del self.interpreter_instances[session_id]
                    logger.info(f"从interpreter_instances中删除实例 {session_id}")
                
                if session_id in self.instance_last_used:
                    del self.instance_last_used[session_id]
                    logger.info(f"从instance_last_used中删除实例 {session_id}")
                    
                if session_id in self.instance_status:
                    del self.instance_status[session_id]
                    logger.info(f"从instance_status中删除实例 {session_id}")
                    
                # 检查是否还在活跃锁中
                if session_id in self._active_locks:
                    self._active_locks.remove(session_id)
                    logger.info(f"从_active_locks中删除实例 {session_id}")
            
            # 在锁外关闭解释器实例
            if interpreter:
                try:
                    # 如果解释器有close方法，调用它
                    if hasattr(interpreter, 'close') and callable(getattr(interpreter, 'close')):
                        interpreter.close()
                        logger.info(f"成功关闭解释器实例 {session_id}")
                    else:
                        logger.info(f"解释器实例 {session_id} 没有close方法")
                except Exception as e:
                    logger.warning(f"关闭解释器实例时出错: {str(e)}")
            
            # 最后清理实例锁
            with self.global_lock:
                if session_id in self._instance_locks:
                    try:
                        # 只有当锁被当前线程持有时才释放
                        lock = self._instance_locks[session_id]
                        lock_acquired = lock.acquire(blocking=False)
                        if lock_acquired:
                            lock.release()  # 释放刚刚获取的锁
                        lock.release()  # 尝试释放原始锁
                    except RuntimeError:
                        pass  # 忽略重复释放的错误
                    
                    # 从字典中删除锁对象
                    del self._instance_locks[session_id]
                    logger.info(f"删除了实例 {session_id} 的锁")
            
            logger.info(f"已清理实例 {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"清理实例 {session_id} 时出错: {str(e)}", exc_info=True)
            return False
    
    def _cleanup_expired_instances(self) -> None:
        """
        清理过期的实例
        """
        while True:
            try:
                # 检查是否已关闭
                with self.global_lock:
                    if self.executor_shutdown:
                        logger.info("实例管理器已关闭，停止清理线程")
                        return
                        
                # 获取需要清理的实例列表
                to_cleanup = []
                
                with self.global_lock:
                    current_time = time.time()
                    expired_sessions = [
                        session_id
                        for session_id, last_used in self.instance_last_used.items()
                        if current_time - last_used > self.instance_timeout
                    ]
                    to_cleanup.extend(expired_sessions)
                
                # 在锁外执行清理
                for session_id in to_cleanup:
                    self._cleanup_instance(session_id)
                    
                time.sleep(300)  # 每5分钟检查一次
            except Exception as e:
                logger.error(f"清理线程出错: {str(e)}")
                time.sleep(300)
    
    def _create_new_interpreter(self, session_id: str) -> Any:
        """
        创建新的解释器实例，从 session metadata 中读取配置
        
        Args:
            session_id: 会话ID
            
        Returns:
            解释器实例
        """
        from interpreter import OpenInterpreter
        import os
        
        # 创建解释器实例
        interpreter = OpenInterpreter()
        
        # 基础配置
        interpreter.auto_run = True
        interpreter.conversation_history = True
        
        # 从 session metadata 中获取配置，如果没有则使用默认值
        session_config = self._get_session_config(session_id)
        
        # 配置 LLM
        if hasattr(interpreter, 'llm'):
            # 设置模型 - 优先使用正确的环境变量
            model = session_config.get('model', os.getenv('OPENAI_MODEL_NAME', os.getenv('LITELLM_MODEL', 'gpt-3.5-turbo')))
            if hasattr(interpreter.llm, 'model'):
                interpreter.llm.model = model
            
            # 设置 API 基础 URL
            api_base = session_config.get('api_base', 'https://llm.deth.dev')
            if hasattr(interpreter.llm, 'api_base'):
                interpreter.llm.api_base = api_base
            elif hasattr(interpreter.llm, 'base_url'):
                interpreter.llm.base_url = api_base
            
            # 设置 API 密钥
            api_key = session_config.get('api_key', 'sk-isakeem')
            if hasattr(interpreter.llm, 'api_key'):
                interpreter.llm.api_key = api_key
            elif hasattr(interpreter.llm, 'key'):
                interpreter.llm.key = api_key
            
            # 设置其他参数
            if hasattr(interpreter.llm, 'context_window'):
                interpreter.llm.context_window = session_config.get('context_window', 10000)
            if hasattr(interpreter.llm, 'max_tokens'):
                interpreter.llm.max_tokens = session_config.get('max_tokens', 4096)
            if hasattr(interpreter.llm, 'temperature'):
                interpreter.llm.temperature = session_config.get('temperature', 0.7)
        
        # 注意：不再设置全局环境变量 os.environ['OPENAI_API_KEY'] 和 os.environ['OPENAI_API_BASE']
        # 因为在多线程环境下，这会影响其他并发的实例。
        # 应该完全依赖于 interpreter 实例本身的配置。

        # 确保 interpreter.llm 具有正确的配置
        if not interpreter.llm.api_key:
             interpreter.llm.api_key = session_config.get('api_key', 'sk-isakeem')
        if not interpreter.llm.api_base:
             interpreter.llm.api_base = session_config.get('api_base', 'https://llm.deth.dev')
        
        logger.info(f"Created interpreter instance for session {session_id} with config: model={session_config.get('model', 'default')}, api_base={session_config.get('api_base', 'default')}")
        return interpreter
    
    def _get_session_config(self, session_id: str) -> Dict[str, Any]:
        """
        从 session metadata 中获取配置
        
        Args:
            session_id: 会话ID
            
        Returns:
            配置字典
        """
        import os
        
        # 默认配置 - 优先使用环境变量中的正确配置
        default_config = {
            'model': os.getenv('OPENAI_MODEL_NAME', os.getenv('LITELLM_MODEL', 'gpt-3.5-turbo')),
            'api_base': os.getenv('OPENAI_API_BASE', os.getenv('ANTHROPIC_BASE_URL', 'https://llm.deth.dev')),
            'api_key': os.getenv('OPENAI_API_KEY', os.getenv('ANTHROPIC_AUTH_TOKEN', 'sk-isakeem')),
            'context_window': 10000,
            'max_tokens': 4096,
            'temperature': 0.7
        }
        
        # 如果有 session_manager，尝试从 session metadata 中获取配置
        if self.session_manager:
            try:
                session = self.session_manager.get_session(session_id)
                if session and 'metadata' in session:
                    metadata = session['metadata']
                    # 从 metadata 中提取配置，如果没有则使用默认值
                    config = default_config.copy()
                    config.update({
                        'model': metadata.get('model', default_config['model']),
                        'api_base': metadata.get('api_base', default_config['api_base']),
                        'api_key': metadata.get('api_key', default_config['api_key']),
                        'context_window': metadata.get('context_window', default_config['context_window']),
                        'max_tokens': metadata.get('max_tokens', default_config['max_tokens']),
                        'temperature': metadata.get('temperature', default_config['temperature'])
                    })
                    logger.info(f"Loaded session config for {session_id}: {config}")
                    return config
            except Exception as e:
                logger.warning(f"Failed to load session config for {session_id}: {str(e)}")
        
        return default_config
    
    def get_instances_status(self) -> Dict[str, Any]:
        """
        获取实例状态信息
        
        Returns:
            实例状态信息
        """
        try:
            with self.global_lock:
                status_counts = {'idle': 0, 'busy': 0, 'error': 0}
                for status in self.instance_status.values():
                    if status in status_counts:
                        status_counts[status] += 1
                
                return {
                    "max_instances": self.max_active_instances,
                    "active_instances": len(self.interpreter_instances),
                    "status_counts": status_counts,
                    "active_locks": len(self._active_locks),
                    "is_optimizing": self.is_optimizing,
                    "executor_shutdown": self.executor_shutdown
                }
        except Exception as e:
            logger.error(f"获取实例状态信息时出错: {str(e)}")
            return {
                "max_instances": self.max_active_instances, 
                "active_instances": 0,
                "error": str(e)
            }
    
    def cleanup_all_resources(self) -> None:
        """
        清理所有资源，用于系统关闭时调用
        """
        try:
            logger.info("开始清理所有实例资源")
            
            # 标记线程池已关闭，防止新任务提交
            with self.global_lock:
                self.executor_shutdown = True
            
            # 关闭线程池
            self.executor.shutdown(wait=False)
            
            # 获取所有实例ID
            all_session_ids = []
            with self.global_lock:
                all_session_ids = list(self.interpreter_instances.keys())
            
            # 强制清理所有实例
            for session_id in all_session_ids:
                self._cleanup_instance(session_id, force=True)
                
            logger.info("所有实例资源已清理完毕")
        except Exception as e:
            logger.error(f"清理所有资源时出错: {str(e)}", exc_info=True) 