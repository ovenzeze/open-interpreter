"""
Flask application factory for Open Interpreter HTTP Server
"""

import os
import pkg_resources
import threading
from typing import Optional, Union

from flask import Flask, jsonify
from interpreter import OpenInterpreter, interpreter

from .config import Config, config
from .errors import ConfigurationError, format_error_response
from .log_config import setup_logging, log_error
from .session import SessionManager
from .routes import chat_bp, session_bp, health_bp

def setup_interpreter(app: Flask, interpreter_instance: Optional[Union[OpenInterpreter, 'interpreter']]) -> None:
    """
    配置解释器实例
    
    Args:
        app: Flask应用实例
        interpreter_instance: 可选的解释器实例
    """
    if interpreter_instance is None:
        try:
            interpreter_instance = interpreter
            interpreter_instance.llm.model = app.config['DEFAULT_MODEL']
            interpreter_instance.llm.context_window = app.config['CONTEXT_WINDOW']
            interpreter_instance.llm.max_tokens = app.config['MAX_TOKENS']
            interpreter_instance.conversation_history = True
        except Exception as e:
            app.logger.error("Failed to configure interpreter", exc_info=True)
            raise ConfigurationError(f"Failed to configure interpreter: {str(e)}")
    
    interpreter_instance.auto_run = True
    app.interpreter_instance = interpreter_instance

def setup_components(app: Flask) -> None:
    """
    设置应用组件
    
    Args:
        app: Flask应用实例
    """
    # 设置日志
    app.logger = setup_logging(
        app_name="interpreter_server",
        log_level=app.config['LOG_LEVEL']
    )
    
    # 设置会话管理器
    app.session_manager = SessionManager()
    
    # 设置聊天锁
    app.chat_lock = threading.Lock()
    
    # 获取并存储版本信息
    try:
        app.version = pkg_resources.get_distribution('open-interpreter').version
    except pkg_resources.DistributionNotFound:
        app.version = 'unknown'
        app.logger.warning("Could not determine package version")

def register_blueprints(app: Flask) -> None:
    """
    注册所有蓝图
    
    Args:
        app: Flask应用实例
    """
    app.register_blueprint(chat_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(health_bp)

def register_error_handlers(app: Flask) -> None:
    """
    注册错误处理器
    
    Args:
        app: Flask应用实例
    """
    @app.errorhandler(Exception)
    def handle_error(error):
        """全局错误处理器"""
        log_error(error)
        error_response, status_code = format_error_response(error)
        return jsonify(error_response), status_code

def create_app(interpreter_instance: Optional[Union[OpenInterpreter, 'interpreter']] = None) -> Flask:
    """
    创建并配置Flask应用实例
    
    Args:
        interpreter_instance: 可选的解释器实例。如果未提供，将创建新实例。
    
    Returns:
        Flask应用实例
    """
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    for key in dir(config):
        if key.isupper():
            app.config[key] = getattr(config, key)
    
    try:
        # 设置应用组件
        setup_components(app)
        
        # 配置解释器
        setup_interpreter(app, interpreter_instance)
        
        # 注册蓝图
        register_blueprints(app)
        
        # 注册错误处理器
        register_error_handlers(app)
        
        app.logger.info("Application initialized successfully")
        return app
        
    except Exception as e:
        app.logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise 