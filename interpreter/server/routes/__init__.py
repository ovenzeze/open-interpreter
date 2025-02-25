"""
Routes package for Open Interpreter HTTP Server
"""

from .chat import bp as chat_bp
from .session import bp as session_bp
from .health import bp as health_bp
from .openai import openai_bp  # 启用 openai 路由

__all__ = ['chat_bp', 'session_bp', 'health_bp', 'openai_bp']  # 添加 'openai_bp'
