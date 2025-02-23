"""
Flask application factory for Open Interpreter HTTP Server
"""

import os
import pkg_resources
import threading
from typing import Optional, Union

from flask import Flask, jsonify
from interpreter import OpenInterpreter

from .config import Config, config
from .errors import ConfigurationError, format_error_response
from .log_config import setup_logging, log_error
from .session import SessionManager
from .routes import chat_bp, session_bp, health_bp
from .routes.openai import openai_bp  # 添加这行

def configure_interpreter_instance(interpreter_instance: Union[OpenInterpreter, 'interpreter'], app: Flask) -> None:
    """
    统一配置解释器实例
    
    Args:
        interpreter_instance: 解释器实例
        app: Flask应用实例，用于获取配置和记录日志
    """
    # TODO: 后续将配置迁移到独立的配置文件中统一管理
    
    # 设置 LLM 相关配置
    app.logger.debug("Configuring interpreter settings...")
    app.logger.debug(f"  Model: {app.config['DEFAULT_MODEL']}")
    app.logger.debug(f"  Context Window: {app.config['CONTEXT_WINDOW']}")
    app.logger.debug(f"  Max Tokens: {app.config['MAX_TOKENS']}")
    
    interpreter_instance.auto_run = True
    interpreter_instance.loop = True


    interpreter_instance.llm.model = app.config['DEFAULT_MODEL']
    interpreter_instance.llm.context_window = app.config['CONTEXT_WINDOW']
    interpreter_instance.llm.max_tokens = app.config['MAX_TOKENS']
    interpreter_instance.computer.import_computer_api = True

    
    # 基础配置
    interpreter_instance.conversation_history = True    
    # 设置安全模式
    if hasattr(interpreter_instance, 'safe_mode'):
        interpreter_instance.safe_mode = 'off'
    elif hasattr(interpreter_instance, 'safeMode'):
        interpreter_instance.safeMode = 'off'
    else:
        app.logger.warning("Interpreter instance missing safe_mode property. Adding property and setting to 'off'.")
        setattr(interpreter_instance, 'safe_mode', 'off')

def setup_interpreter(app: Flask, interpreter_instance: Optional[Union[OpenInterpreter, 'interpreter']]) -> None:
    """
    配置解释器实例
    
    Args:
        app: Flask应用实例
        interpreter_instance: 可选的解释器实例
    """
    app.logger.info("Configuring interpreter instance...")
    
    if interpreter_instance is None:
        try:
            app.logger.debug("Creating new interpreter instance...")
            interpreter_instance = OpenInterpreter()
            configure_interpreter_instance(interpreter_instance, app)
            app.logger.info("Interpreter configured successfully")
        except Exception as e:
            app.logger.error("Failed to configure interpreter", exc_info=True)
            app.logger.error(f"Error details: {str(e)}")
            raise ConfigurationError(f"Failed to configure interpreter: {str(e)}")
    else:
        # 即使是现有实例也需要确保配置一致
        configure_interpreter_instance(interpreter_instance, app)
    
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
    app.register_blueprint(openai_bp)  # 添加这行

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
    
    try:
        # 加载配置
        app.logger.info("Loading configuration...")
        for key in dir(config):
            if key.isupper():
                app.config[key] = getattr(config, key)
                app.logger.debug(f"Config: {key} = {app.config[key]}")
        
        app.logger.info("Setting up application components...")
        setup_components(app)
        
        app.logger.info("Configuring interpreter...")
        setup_interpreter(app, interpreter_instance)
        
        app.logger.info("Registering blueprints...")
        register_blueprints(app)
        
        app.logger.info("Registering error handlers...")
        register_error_handlers(app)
        
        app.logger.info("Application initialization complete")
        return app
        
    except Exception as e:
        app.logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        if hasattr(app, 'logger'):
            app.logger.error("Initialization error details:", exc_info=True)
        raise