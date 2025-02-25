"""
Flask application factory for Open Interpreter HTTP Server
"""

import os
import pkg_resources
import threading
from typing import Optional, Union

from flask import Flask, jsonify
import interpreter
from interpreter import OpenInterpreter

from .config import Config
from .errors import ConfigurationError, format_error_response
from .log_config import setup_logging, log_error
from .session import SessionManager  # 直接从 session.py 导入
from .routes import chat_bp, session_bp, health_bp, openai_bp  # 移除 openai_bp

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
    # 使用 app.config.get() 避免 KeyError
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    
    # 设置日志
    app.logger = setup_logging(
        app_name="interpreter_server",
        log_level=log_level
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
    app.register_blueprint(openai_bp)  # 启用 OpenAI 兼容接口

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

def create_app(config=None):
    app = Flask(__name__)
    
    # Update version setting using the imported interpreter module
    try:
        app.version = interpreter.__version__
    except AttributeError:
        app.version = 'unknown'
    
    # 1. 首先加载默认配置
    app.config.update(vars(Config()))
    
    # 2. 然后用传入的配置覆盖默认值
    if config:
        app.config.update(config)
    
    try:
        # 3. 设置基础日志（在其他初始化之前）
        log_level = app.config.get('LOG_LEVEL', 'INFO')
        app.logger = setup_logging(
            app_name="interpreter_server",
            log_level=log_level
        )
        
        app.logger.info("Initializing application...")
        
        # 4. 初始化会话管理器
        app.session_manager = SessionManager(
            max_active_instances=app.config.get('MAX_ACTIVE_INSTANCES', 3),
            session_timeout=app.config.get('INSTANCE_TIMEOUT', 3600),
            cleanup_interval=app.config.get('CLEANUP_INTERVAL', 300)
        )
        
        # 5. 设置解释器
        setup_interpreter(app, None)
        
        # 6. 注册蓝图和错误处理
        register_blueprints(app)
        register_error_handlers(app)
        
        app.logger.info("Application initialization complete")
        return app
        
    except Exception as e:
        print(f"Failed to initialize application: {str(e)}")
        if hasattr(app, 'logger'):
            app.logger.error("Initialization error details:", exc_info=True)
        raise