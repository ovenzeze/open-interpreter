"""
聊天相关的路由处理模块
包含原生聊天接口和OpenAI兼容接口
"""

import json
import uuid
import time
from flask import jsonify, request, Response, stream_with_context, current_app
from flask_openapi3 import APIBlueprint
from ..message import Message, StreamingChunk
from ..errors import ValidationError, format_error_response
from ..log_config import log_error
from ..openapi_models import ChatCompletionRequest, ChatCompletionResponse # 导入模型

bp = APIBlueprint('chat', __name__, url_prefix='')

@bp.post(
    '/v1/chat',
    summary="Native chat interface",
    description="Native Open Interpreter chat endpoint with streaming support",
    responses={"200": ChatCompletionResponse} # 使用 ChatCompletionResponse 作为响应
)
def chat(body: ChatCompletionRequest): # 更改函数签名以接收 Pydantic body
    """Chat endpoint that handles both streaming and non-streaming responses"""
    try:
        # 从 body 参数获取数据
        messages = body.messages
        if not messages:
            current_app.logger.error("Invalid request: empty messages array")
            raise ValidationError("Messages array is required")
            
        stream = body.stream if body.stream is not None else False
        session_id = body.session_id
        model = body.model
        
        # 获取聊天服务
        if not hasattr(current_app, 'chat_service'):
            from ..chat_service import ChatService
            current_app.chat_service = ChatService(current_app.session_manager)
        
        chat_service = current_app.chat_service
        
        # 转换消息为Message对象
        validated_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                msg = msg.copy()  # 创建副本以不修改原始数据
                msg.pop('start', None)
                msg.pop('end', None)
                # 确保消息类型正确设置
                if 'type' not in msg:
                    msg['type'] = 'message'
                # 验证角色，如果不符合要求则设置为用户消息
                if msg.get('role') not in ['user', 'assistant', 'computer']:
                    current_app.logger.warning(f"Invalid role in message: {msg.get('role')}, converting to 'user'")
                    msg['role'] = 'user'
            validated_messages.append(Message.from_dict(msg) if isinstance(msg, dict) else msg)
        messages = validated_messages
        
        current_app.logger.info(f"Processing chat request with {len(messages)} messages, session_id: {session_id}")
        
        if stream:
            # 流式响应
            def generate_stream():
                for chunk in chat_service.process_streaming_chat(
                    messages=messages,
                    session_id=session_id,
                    model=model,
                    is_openai_format=False  # 强制设置为False，确保使用原生格式
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
                messages=messages,
                session_id=session_id,
                stream=stream,
                model=model,
                is_openai_format=False  # 强制设置为False，确保使用原生格式
            )
            
            # 检查是否是错误响应
            if 'error' in result:
                return jsonify(result), 400 if 'code' in result.get('error', {}) and result['error']['code'] == 'session_busy' else 500
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
