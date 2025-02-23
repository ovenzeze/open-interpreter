"""
服务器配置模块
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """服务器配置类"""
    
    def __init__(self):
        # 服务器设置
        self.HOST = os.getenv('SERVER_HOST', '0.0.0.0')
        self.PORT = int(os.getenv('SERVER_PORT', 5000))
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # 日志设置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_DIR = 'logs'
        
        # 会话设置
        self.SESSION_DIR = 'sessions'
        self.SESSION_CLEANUP_INTERVAL = 3600  # 1小时清理一次过期会话
        self.SESSION_LIFETIME = 86400  # 会话有效期24小时
        
        # 锁设置
        self.LOCK_TIMEOUT = 5  # 锁等待超时时间（秒）
        
        # LLM设置
        self.DEFAULT_MODEL = os.getenv('LITELLM_MODEL', 'gpt-3.5-turbo')
        self.CONTEXT_WINDOW = 10000
        self.MAX_TOKENS = int(os.getenv('MAX_TOKENS', 4096))
        self.TEMPERATURE = float(os.getenv('TEMPERATURE', 0.7))
        
        # 速率限制
        self.RATE_LIMIT = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
        self.SESSION_RATE_LIMIT = int(os.getenv('SESSION_RATE_LIMIT_PER_MINUTE', 10))
        
        # 实例管理配置
        self.MAX_ACTIVE_INSTANCES = int(os.getenv("MAX_ACTIVE_INSTANCES", "3"))
        self.INSTANCE_TIMEOUT = int(os.getenv("INSTANCE_TIMEOUT", "3600"))  # 1小时
        self.CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "300"))   # 5分钟
    
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        return cls()

# 创建默认配置实例
config = Config()