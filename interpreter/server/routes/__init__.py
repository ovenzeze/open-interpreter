"""
Routes package for Open Interpreter HTTP Server
"""

from .chat import bp as chat_bp
from .session import bp as session_bp
from .health import bp as health_bp
# from .openai import bp as openai_bp  # 暂时注释掉，直到 openai 路由实现

__all__ = ['chat_bp', 'session_bp', 'health_bp']  # 移除 'openai_bp'
