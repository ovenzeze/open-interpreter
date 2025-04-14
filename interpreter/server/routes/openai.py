"""OpenAI兼容接口路由处理"""
from flask import Blueprint, request, jsonify, Response, current_app, stream_with_context
from ..message import Message, StreamingChunk
from ..errors import ValidationError, MethodNotAllowedError, format_error_response
from ..message_processor import MessageProcessor
import uuid
import time
import functools
from typing import Dict, List, Any, Union, cast

openai_bp = Blueprint('openai', __name__)

def handle_method_not_allowed(allowed_methods):
    """
    装饰器：处理不支持的HTTP方法请求
    
    Args:
        allowed_methods: 允许的HTTP方法列表
        
    Returns:
        装饰后的函数
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # 对OPTIONS方法特殊处理，提供API验证支持
            if request.method == 'OPTIONS':
                response = jsonify({
                    "status": "success",
                    "message": "API endpoint available"
                })
                response.status_code = 200
                # 添加CORS和允许的方法头部
                response.headers['Allow'] = ', '.join(allowed_methods)
                response.headers['Access-Control-Allow-Methods'] = ', '.join(allowed_methods)
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                return response
            
            if request.method not in allowed_methods:
                current_app.logger.warning(f"Method {request.method} not allowed for endpoint {request.path}")
                error = MethodNotAllowedError(f"Method {request.method} not allowed for this endpoint")
                error_response, status_code = format_error_response(error)
                response = jsonify(error_response)
                response.status_code = status_code
                # 添加允许的方法到响应头
                response.headers['Allow'] = ', '.join(allowed_methods)
                return response
            return f(*args, **kwargs)
        return wrapped
    return decorator

@openai_bp.route('/v1/models', methods=['GET', 'OPTIONS'])
@handle_method_not_allowed(['GET', 'OPTIONS'])
def list_models():
    """
    获取可用的模型列表
    
    Returns:
        模型列表
    """
    try:
        # 从环境变量或配置中获取模型信息
        default_model = current_app.config.get('DEFAULT_MODEL', 'gpt-3.5-turbo')
        
        # OpenAI风格的模型列表响应
        models_response = {
            "object": "list",
            "data": [
                {
                    "id": default_model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "open-interpreter"
                }
            ]
        }
        
        # 如果有配置多个模型，可以在这里添加
        if hasattr(current_app, 'interpreter_instance') and hasattr(current_app.interpreter_instance, 'llm'):
            llm_model = getattr(current_app.interpreter_instance.llm, 'model', None)
            if llm_model and llm_model != default_model:
                models_response["data"].append({
                    "id": llm_model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "open-interpreter"
                })
        
        return jsonify(models_response)
    except Exception as e:
        current_app.logger.error(f"Error listing models: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@openai_bp.route('/v1/engines', methods=['GET', 'OPTIONS'])
@handle_method_not_allowed(['GET', 'OPTIONS'])
def list_engines():
    """
    获取可用的引擎列表（兼容OpenAI旧版API）
    
    Returns:
        引擎列表
    """
    try:
        # 从环境变量或配置中获取模型信息
        default_model = current_app.config.get('DEFAULT_MODEL', 'gpt-3.5-turbo')
        
        # 检查是否有环境变量中定义的模型
        env_model = None
        if 'LITELLM_MODEL' in current_app.config:
            env_model = current_app.config.get('LITELLM_MODEL')
        
        # OpenAI风格的引擎列表响应
        engines_response = {
            "object": "list",
            "data": [
                {
                    "id": default_model,
                    "object": "engine",
                    "created": int(time.time()),
                    "owner": "open-interpreter",
                    "ready": True
                }
            ]
        }
        
        # 添加环境变量中的模型
        if env_model and env_model != default_model:
            engines_response["data"].append({
                "id": env_model,
                "object": "engine",
                "created": int(time.time()),
                "owner": "open-interpreter",
                "ready": True
            })
        
        # 如果有配置多个模型，可以在这里添加
        if hasattr(current_app, 'interpreter_instance') and hasattr(current_app.interpreter_instance, 'llm'):
            llm_model = getattr(current_app.interpreter_instance.llm, 'model', None)
            if llm_model and llm_model != default_model and (not env_model or llm_model != env_model):
                engines_response["data"].append({
                    "id": llm_model,
                    "object": "engine",
                    "created": int(time.time()),
                    "owner": "open-interpreter",
                    "ready": True
                })
        
        return jsonify(engines_response)
    except Exception as e:
        current_app.logger.error(f"Error listing engines: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@openai_bp.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@handle_method_not_allowed(['POST', 'OPTIONS'])
def chat_completions():
    """
    OpenAI兼容的聊天完成接口
    
    Request Body:
        {
            "messages": [OpenAI格式的消息数组],
            "stream": bool,
            "model": str (可选),
            "session_id": str (可选)
        }
    
    Returns:
        OpenAI格式的响应
    """
    if not request.is_json:
        raise ValidationError("Content-Type must be application/json")
        
    try:
        data = request.get_json()
        if data is None:
            raise ValidationError("Invalid request data")
            
        # 获取原始消息
        raw_messages = data.get('messages', [])
        if not raw_messages:
            raise ValidationError("Messages array is required")
            
        stream = data.get('stream', False)
        session_id = data.get('session_id')
        model = data.get('model')
        
        # 获取聊天服务
        if not hasattr(current_app, 'chat_service'):
            from ..chat_service import ChatService
            current_app.chat_service = ChatService(current_app.session_manager)
        
        chat_service = current_app.chat_service
        
        current_app.logger.info(f"Processing OpenAI chat request with {len(raw_messages)} messages")
        
        # 转换消息为字典格式 - 直接使用原始消息的字典格式，避免类型转换问题
        # MessageProcessor.validate_messages会返回Message对象，但chat_service需要字典
        message_dicts = []
        for msg in raw_messages:
            if isinstance(msg, dict):
                message_dicts.append(msg)
            elif hasattr(msg, 'to_dict'):
                message_dicts.append(msg.to_dict())
            else:
                # 如果消息格式无法识别，尝试转换为字符串
                message_dicts.append({
                    "role": "user",
                    "content": str(msg),
                    "type": "message"
                })
        
        if stream:
            # 流式响应
            def generate_stream():
                for chunk in chat_service.process_streaming_chat(
                    messages=message_dicts,
                    session_id=session_id,
                    model=model
                ):
                    yield chunk
            
            return Response(
                stream_with_context(generate_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # 非流式响应
            result = chat_service.process_chat(
                messages=message_dicts,
                session_id=session_id,
                stream=stream,
                model=model
            )
            
            # 检查是否是错误响应
            if isinstance(result, dict) and 'error' in result:
                error_code = result.get('error', {}).get('code', '')
                return jsonify(result), 400 if error_code == 'session_busy' else 500
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 