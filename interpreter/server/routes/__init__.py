"""
路由模块初始化文件
导出所有路由蓝图供主应用注册
"""

from .chat import bp as chat_bp
from .session import bp as session_bp
from .health import bp as health_bp

__all__ = ['chat_bp', 'session_bp', 'health_bp']
