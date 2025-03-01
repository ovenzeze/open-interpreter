"""OpenAI兼容接口路由处理"""
from flask import Blueprint, request, jsonify, Response, current_app, stream_with_context
from ..message import Message, StreamingChunk
from ..errors import ValidationError, format_error_response
from ..message_processor import MessageProcessor
import uuid
import time

openai_bp = Blueprint('openai', __name__)

@openai_bp.route('/v1/chat/completions', methods=['POST'])
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
            
        messages = data.get('messages', [])
        messages = MessageProcessor.validate_messages(messages)
            
        stream = data.get('stream', False)
        session_id = data.get('session_id')
        model = data.get('model')
        
        # 获取聊天服务
        if not hasattr(current_app, 'chat_service'):
            from ..chat_service import ChatService
            current_app.chat_service = ChatService(current_app.session_manager)
        
        chat_service = current_app.chat_service
        
        current_app.logger.info(f"Processing OpenAI chat request with {len(messages)} messages")
        
        if stream:
            # 流式响应
            def generate_stream():
                for chunk in chat_service.process_streaming_chat(
                    messages=messages,
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
                is_openai_format=True
            )
            
            # 检查是否是错误响应
            if 'error' in result:
                return jsonify(result), 400 if 'code' in result.get('error', {}) and result['error']['code'] == 'session_busy' else 500
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 