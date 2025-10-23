"""OpenAI兼容接口路由处理"""
from flask import request, jsonify, Response, current_app, stream_with_context
from flask_openapi3 import APIBlueprint
from ..message import Message, StreamingChunk
from ..errors import ValidationError, MethodNotAllowedError, format_error_response
from ..message_processor import MessageProcessor
from ..openapi_models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
    EngineListResponse
)
import uuid
import time
import functools
from typing import Dict, List, Any, Union, cast

openai_bp = APIBlueprint('openai', __name__, url_prefix='')

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

@openai_bp.get(
    '/v1/models',
    summary="List available models",
    description="Get a list of available models compatible with OpenAI API"
)
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
            "data": []
        }
        
        # 添加默认模型
        models_response["data"].append({
            "id": default_model,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "open-interpreter"
        })
        
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
        
        # 添加常用的Bedrock模型
        bedrock_models = [
            "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
            "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
            "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
            "bedrock/anthropic.claude-instant-v1",
            "bedrock/meta.llama2-13b-chat-v1",
            "bedrock/meta.llama2-70b-chat-v1"
        ]
        
        for model in bedrock_models:
            if model not in [item["id"] for item in models_response["data"]]:
                models_response["data"].append({
                    "id": model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "bedrock"
                })
        
        response = jsonify(models_response)
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    except Exception as e:
        current_app.logger.error(f"Error listing models: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        response = jsonify(error_response)
        response.status_code = status_code
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response, status_code

@openai_bp.get(
    '/v1/engines',
    summary="List available engines",
    description="Get a list of available engines compatible with OpenAI API (legacy)"
)
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
            "data": []
        }
        
        # 添加默认模型
        engines_response["data"].append({
            "id": default_model,
            "object": "engine",
            "created": int(time.time()),
            "owner": "open-interpreter",
            "ready": True
        })
        
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
        
        # 添加常用的Bedrock模型
        bedrock_models = [
            "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
            "bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
            "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
            "bedrock/anthropic.claude-instant-v1",
            "bedrock/meta.llama2-13b-chat-v1",
            "bedrock/meta.llama2-70b-chat-v1"
        ]
        
        for model in bedrock_models:
            if model not in [item["id"] for item in engines_response["data"]]:
                engines_response["data"].append({
                    "id": model,
                    "object": "engine",
                    "created": int(time.time()),
                    "owner": "bedrock",
                    "ready": True
                })
        
        response = jsonify(engines_response)
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    except Exception as e:
        current_app.logger.error(f"Error listing engines: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        response = jsonify(error_response)
        response.status_code = status_code
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response, status_code

@openai_bp.post(
    '/v1/chat/completions',
    summary="Create chat completion",
    description="OpenAI-compatible chat completion endpoint. Supports both streaming and non-streaming responses."
)
def chat_completions(body: ChatCompletionRequest):
    """
    OpenAI兼容的聊天完成接口
    
    支持POST方法:
    - POST: 标准OpenAI格式的JSON请求体
    
    Request Body (POST):
        {
            "messages": [OpenAI格式的消息数组],
            "stream": bool,
            "model": str (可选),
            "session_id": str (可选)
        }
    
    Returns:
        OpenAI格式的响应
    """
    try:
        # 获取聊天服务
        if not hasattr(current_app, 'chat_service'):
            from ..chat_service import ChatService
            current_app.chat_service = ChatService(current_app.session_manager)
        
        chat_service = current_app.chat_service
        
        # 从 body 参数获取数据
        message_dicts = []
        stream = body.stream if body.stream is not None else False
        session_id = body.session_id
        model = body.model
        
        # 转换消息为字典格式
        for msg in body.messages:
            if isinstance(msg, dict):
                message_dicts.append(msg)
            elif hasattr(msg, 'model_dump'):
                message_dicts.append(msg.model_dump())
            elif hasattr(msg, 'dict'):
                message_dicts.append(msg.dict())
            else:
                # 如果消息格式无法识别，尝试转换为字符串
                message_dicts.append({
                    "role": "user",
                    "content": str(msg),
                    "type": "message"
                })
        
        current_app.logger.info(f"Processing POST OpenAI chat request with {len(body.messages)} messages")
        
        if stream:
            # 流式响应
            def generate_stream():
                for chunk in chat_service.process_streaming_chat(
                    messages=message_dicts,
                    session_id=session_id,
                    model=model,
                    is_openai_format=True
                ):
                    yield chunk
            
            return Response(
                stream_with_context(generate_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                }
            )
        else:
            # 非流式响应
            result = chat_service.process_chat(
                messages=message_dicts,
                session_id=session_id,
                stream=stream,
                model=model,
                is_openai_format=True
            )
            
            # 检查是否是错误响应
            if isinstance(result, dict) and 'error' in result:
                error_code = result.get('error', {}).get('code', '')
                response = jsonify(result)
                response.status_code = 400 if error_code == 'session_busy' else 500
                
                # 添加CORS头
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                
                return response
            
            response = jsonify(result)
            
            # 添加CORS头
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            
            return response
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        response = jsonify(error_response)
        response.status_code = status_code
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
