"""OpenAI兼容接口路由处理"""
from flask import Blueprint, request, jsonify, Response
from ..services.chat_service import ChatService
from ..services.session_service import SessionService
from ..utils.error_utils import format_error_response

openai_bp = Blueprint('openai', __name__)
chat_service = ChatService()
session_service = SessionService()

@openai_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI兼容的聊天补全接口"""
    try:
        data = request.get_json()
        stream = data.get('stream', False)
        
        # 创建会话
        session = session_service.create_session()
        
        if stream:
            return Response(
                chat_service.process_openai_stream(data, session['session_id']),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        response = chat_service.process_openai_chat(data, session['session_id'])
        return jsonify(response)
        
    except Exception as e:
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 