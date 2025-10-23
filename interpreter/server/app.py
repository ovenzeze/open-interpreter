"""
Flask application factory for Open Interpreter HTTP Server
"""

import os
import pkg_resources
import threading
from typing import Optional, Union

from flask import jsonify, request, g, current_app, redirect
from flask_openapi3 import OpenAPI, Info
# 移除 flask_cors 导入
import interpreter
from interpreter import OpenInterpreter

from .config import Config
from .errors import ConfigurationError, format_error_response
from .log_config import setup_logging, log_error
from .session import SessionManager  # 直接从 session.py 导入
from .routes import chat_bp, session_bp, health_bp, openai_bp, title_generator_bp  # 添加 title_generator_bp

def configure_interpreter_instance(interpreter_instance: Union[OpenInterpreter, 'interpreter'], app: OpenAPI) -> None:
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

def setup_interpreter(app: OpenAPI, interpreter_instance: Optional[Union[OpenInterpreter, 'interpreter']]) -> None:
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

def setup_components(app: OpenAPI) -> None:
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

def register_blueprints(app: OpenAPI) -> None:
    """
    注册所有蓝图
    
    Args:
        app: Flask应用实例
    """
    # 使用 register_api 注册 APIBlueprint 使其出现在 OpenAPI 文档中
    app.register_api(chat_bp)
    app.register_api(session_bp)
    app.register_api(health_bp)
    app.register_api(openai_bp)  # 启用 OpenAI 兼容接口
    
    # title_generator_bp 如果不是 APIBlueprint，使用 register_blueprint
    try:
        app.register_api(title_generator_bp)
    except:
        app.register_blueprint(title_generator_bp)

def register_error_handlers(app: OpenAPI) -> None:
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
    
    # 添加特定的METHOD_NOT_ALLOWED处理器
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """方法不允许错误处理器"""
        app.logger.warning(f"Method not allowed: {request.method} {request.path}")
        error_response = {
            "error": {
                "message": f"Method {request.method} not allowed for this endpoint",
                "type": "MethodNotAllowedError"
            }
        }
        response = jsonify(error_response)
        response.status_code = 405
        # 添加允许的方法到响应头
        if hasattr(error, 'valid_methods') and error.valid_methods:
            response.headers['Allow'] = ', '.join(error.valid_methods)
        return response

def create_app(config=None):
    # 创建 OpenAPI 应用
    info = Info(
        title="Open Interpreter Server API",
        version="0.4.3",
        description="OpenAI-compatible API server for Open Interpreter with automatic OpenAPI documentation"
    )
    app = OpenAPI(__name__, info=info)
    
    # 移除 CORS 初始化
    
    if config:
        app.config.update(config)
    
    # 设置默认配置
    app.config.setdefault("MAX_INSTANCES", 3)
    app.config.setdefault("MODEL", "gpt-3.5-turbo")
    app.config.setdefault("SAFE_MODE", "true")
    
    # 添加CORS支持
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get('Origin')
        if origin:
            # 使用请求的实际源而不是通配符
            response.headers.add('Access-Control-Allow-Origin', origin)
            # 允许凭据
            response.headers.add('Access-Control-Allow-Credentials', 'true')
        else:
            response.headers.add('Access-Control-Allow-Origin', '*')
            
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        # 处理预检请求
        if request.method == 'OPTIONS':
            # 预检请求缓存时间（秒）
            response.headers.add('Access-Control-Max-Age', '3600')
            # 确保预检请求返回200状态码
            if response.status_code == 200:
                return response
            # 如果状态码不是200（可能是405），则创建一个新的成功响应
            success_response = jsonify({"status": "success", "message": "API endpoint available"})
            success_response.status_code = 200
            # 复制原始响应的所有头部
            for header, value in response.headers.items():
                success_response.headers[header] = value
            return success_response
            
        return response
    
    # 设置版本信息
    try:
        app.version = pkg_resources.get_distribution('open-interpreter').version
    except pkg_resources.DistributionNotFound:
        app.version = 'unknown'
        if hasattr(app, 'logger'):
            app.logger.warning("Could not determine package version")
    
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
        
        # 4.5 初始化聊天服务
        from .chat_service import ChatService
        app.chat_service = ChatService(app.session_manager)
        
        # 5. 设置解释器
        setup_interpreter(app, None)
        
        # 6. 注册蓝图和错误处理
        register_blueprints(app)
        register_error_handlers(app)
        
        # 7. 添加根路径重定向到 Swagger UI
        @app.get("/")
        def redirect_to_swagger():
            """重定向根路径到 Swagger UI"""
            return redirect("/openapi/swagger")
        
        app.logger.info("Application initialization complete")
        return app
        
    except Exception as e:
        print(f"Failed to initialize application: {str(e)}")
        if hasattr(app, 'logger'):
            app.logger.error("Initialization error details:", exc_info=True)
        raise