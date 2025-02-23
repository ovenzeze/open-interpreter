"""
会话管理相关的路由处理模块
包含会话的创建、列表、消息获取等功能
"""

from flask import Blueprint, jsonify, request, current_app
from ..errors import ValidationError, format_error_response
from ..log_config import log_error

bp = Blueprint('session', __name__)

@bp.route('/v1/sessions', methods=['GET'])
def list_sessions():
    """
    获取所有可用会话列表
    
    Returns:
        JSON响应，包含会话列表
    """
    try:
        sessions = current_app.session_manager.list_sessions()
        return jsonify({"sessions": sessions})
    except Exception as e:
        current_app.logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions', methods=['POST'])
def create_session():
    """
    创建新的会话
    
    Returns:
        JSON响应，包含新创建的会话信息
    """
    try:
        metadata = request.get_json() if request.is_json else None
        session = current_app.session_manager.create_session(metadata=metadata)
        current_app.logger.info(f"Created new session with ID: {session['session_id']}")
        return jsonify(session)
    except Exception as e:
        current_app.logger.error(f"Error creating session: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """
    获取指定会话的所有消息
    
    Args:
        session_id: 会话ID
        
    Returns:
        JSON响应，包含会话中的所有消息
    """
    try:
        messages = current_app.session_manager.get_messages(session_id)
        if messages is None:
            raise ValidationError(f"Session {session_id} not found")
        return jsonify({"messages": messages})
    except Exception as e:
        current_app.logger.error(f"Error getting messages for session {session_id}: {str(e)}", exc_info=True)
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
