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
    """OpenAI兼容的聊天补全接口"""
    try:
        if not request.is_json:
            raise ValidationError("Content-Type must be application/json")
            
        data = request.get_json()
        if data is None:
            raise ValidationError("Invalid request data")
            
        messages = data.get('messages', [])
        if not messages:
            raise ValidationError("Messages array is required")
            
        stream = data.get('stream', False)
        
        # 获取会话管理器
        session_manager = current_app.session_manager
        
        # 创建会话
        session = session_manager.create_session()
        session_id = session['session_id']
        
        # 获取interpreter实例
        interpreter_instance = session_manager.get_interpreter(session_id)
        if not interpreter_instance:
            raise ValidationError("Failed to get interpreter instance")
            
        # 如果提供了模型，更新interpreter配置
        if 'model' in data:
            interpreter_instance.llm.model = data['model']
            
        # 转换消息格式
        interpreter_messages = convert_openai_to_interpreter(messages)
        interpreter_instance.messages = [msg.to_dict() for msg in interpreter_messages[:-1]]
        
        # 发送最后一条消息
        response = interpreter_instance.chat(interpreter_messages[-1].content, stream=stream)
        
        if stream:
            def generate():
                try:
                    for chunk in response:
                        if isinstance(chunk, dict):
                            chunk = chunk.copy()
                            chunk.pop('start', None)
                            chunk.pop('end', None)
                        yield format_openai_stream_chunk(chunk)
                except Exception as e:
                    current_app.logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
                    error_chunk = {
                        'role': 'assistant',
                        'type': 'error',
                        'content': str(e)
                    }
                    yield format_openai_stream_chunk(error_chunk)
                    
            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
            
        # 处理非流式响应
        content = ''
        for chunk in response:
            if isinstance(chunk, dict):
                chunk = chunk.copy()
                chunk.pop('start', None)
                chunk.pop('end', None)
            chunk = Message.from_dict(chunk) if isinstance(chunk, dict) else chunk
            if chunk.type == 'message' and chunk.role == 'assistant':
                if content:
                    content += '\n'
                content += chunk.content
                
        return jsonify({
            'id': f'chatcmpl-{str(uuid.uuid4())}',
            'object': 'chat.completion',
            'created': int(time.time()),
            'model': interpreter_instance.llm.model,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': content
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing chat completions request: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 