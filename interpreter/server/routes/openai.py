"""OpenAI兼容接口路由处理"""
from flask import Blueprint, request, jsonify, Response, current_app
from ..message import Message
from ..errors import ValidationError, format_error_response
from ..utils import convert_openai_to_interpreter, format_openai_stream_chunk
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
        
        # 获取会话管理器
        session_manager = current_app.session_manager
        
        # 如果没有提供session_id，创建新会话
        if not session_id:
            session = session_manager.create_session()
            session_id = session['session_id']
        
        # 获取interpreter实例
        interpreter_instance = session_manager.get_interpreter(session_id)
        if not interpreter_instance:
            current_app.logger.error(f"No interpreter instance found for session {session_id}")
            return jsonify({
                "error": {
                    "message": "会话已过期或不存在",
                    "code": "session_expired",
                    "details": {
                        "session_id": session_id
                    }
                }
            }), 404
        
        # 如果提供了模型，更新interpreter配置
        if 'model' in data:
            interpreter_instance.llm.model = data['model']
        
        current_app.logger.info(f"Processing chat completions request with {len(messages)} messages for session {session_id}")
        interpreter_instance.auto_run = True

        # 加载会话消息
        session_messages = session_manager.get_messages(session_id)
        if session_messages:
            if isinstance(session_messages, dict):
                session_messages = [session_messages]
            elif not isinstance(session_messages, list):
                session_messages = []
            messages = session_messages + (messages if isinstance(messages, list) else [messages])
        
        # 转换消息格式并发送请求
        interpreter_messages = convert_openai_to_interpreter(messages)
        interpreter_instance.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]  # 加载历史消息
        response = interpreter_instance.chat(interpreter_messages[-1].content, stream=stream)
        
        if not stream:
            result = MessageProcessor.process_response(response, session_manager, session_id)
            return jsonify(result)
        
        def generate_stream():
            """生成OpenAI格式的流式响应"""
            try:
                for chunk in response:
                    chunk = StreamingChunk.from_dict(chunk)
                    if chunk.type == 'message':
                        session_manager.add_message(session_id, Message(
                            role=chunk.role,
                            type=chunk.type,
                            content=chunk.content,
                            format=chunk.format
                        ).to_dict())
                    yield format_openai_stream_chunk(chunk)
            except Exception as e:
                current_app.logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                error_chunk = StreamingChunk(
                    role='assistant',
                    type='error',
                    content=str(e),
                    recipient='user'
                )
                yield format_openai_stream_chunk(error_chunk)
        
        return Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
            
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 