"""
会话管理相关的路由处理模块
包含会话的创建、列表、消息获取等功能
"""

from flask import Blueprint, jsonify, request, current_app
from ..errors import ValidationError, format_error_response
from ..models import SessionCreate, SessionMetadata, Session
from ..log_config import log_request_info, log_response_info, logger  # 导入 logger

bp = Blueprint('session', __name__)

@bp.before_request
def log_request():
    """记录请求信息"""
    log_request_info(request)

@bp.after_request
def log_response(response):
    """记录响应信息"""
    log_response_info(response)
    return response

# 基础会话管理路由
@bp.route('/v1/sessions', methods=['GET'])
def list_sessions():
    """获取会话列表"""
    try:
        sessions = current_app.session_manager.list_sessions()
        return jsonify({"sessions": sessions, "total": len(sessions)})
    except Exception as e:
        logger.error("Failed to list sessions", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions', methods=['POST'])
def create_session():
    """创建新会话"""
    try:
        data = request.get_json() or {}
        session_create = SessionCreate(**data)
        session = current_app.session_manager.create_session(session_create.model_dump())

        # 修复嵌套的元数据结构
        if 'metadata' in session and isinstance(session['metadata'], dict):
            if 'metadata' in session['metadata']:
                session['metadata'] = session['metadata']['metadata']

        response_data = {
            "session_id": session['session_id'],
            "created_at": session['created_at'],
            "metadata": session['metadata']  # 现在是正确的单层结构
        }
        return jsonify(response_data), 201
    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/v1/sessions/<session_id>', methods=['GET', 'PATCH', 'DELETE'])
def manage_session(session_id):
    """管理单个会话"""
    try:
        if request.method == 'GET':
            session = current_app.session_manager.get_session(session_id)
            if not session:
                return jsonify({"error": "Session not found"}), 404
            # 确保返回的metadata结构正确
            session['metadata'] = session.get('metadata', {})
            if isinstance(session['metadata'], dict) and 'metadata' in session['metadata']:
                session['metadata'] = session['metadata']['metadata']
            return jsonify(session)
            
        elif request.method == 'PATCH':
            data = request.get_json()
            session = current_app.session_manager.update_session(session_id, data)
            if not session:
                return jsonify({"error": "Session not found"}), 404
            return jsonify(session)
            
        elif request.method == 'DELETE':
            if not current_app.session_manager.get_session(session_id):
                return jsonify({"error": "Session not found"}), 404
            current_app.session_manager._remove_session(session_id)
            return jsonify({"success": True})
            
    except Exception as e:
        logger.error(f"Session operation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

# 会话消息管理路由
@bp.route('/v1/sessions/<session_id>/messages', methods=['GET', 'POST', 'DELETE'])
def manage_messages(session_id):
    """管理会话消息"""
    try:
        if request.method == 'GET':
            messages = current_app.session_manager.get_messages(session_id)
            return jsonify({"messages": messages})
            
        elif request.method == 'POST':
            message = request.get_json()
            success = current_app.session_manager.add_message(session_id, message)
            return jsonify({"success": success})
            
        elif request.method == 'DELETE':
            current_app.session_manager.update_session(session_id, {"messages": []})
            return jsonify({"success": True})
            
    except Exception as e:
        logger.error(f"Message operation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions/<session_id>/messages', methods=['POST'])
def add_message(session_id):
    """添加消息到会话"""
    try:
        data = request.get_json()
        if not isinstance(data, dict) or 'content' not in data or 'role' not in data:
            raise ValidationError("Invalid message format")

        # 获取锁确保并发安全
        if not current_app.session_manager.acquire_session_lock(session_id):
            raise ValidationError("Session is locked")

        try:
            success = current_app.session_manager.add_message(session_id, data)
            if not success:
                raise ValidationError("Failed to add message")
            return jsonify({"success": True})
        finally:
            current_app.session_manager.release_session_lock(session_id)

    except Exception as e:
        logger.error(f"Message operation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

# 辅助功能路由
@bp.route('/v1/sessions/<session_id>/load', methods=['POST'])
def load_session(session_id):
    """加载历史会话"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        current_app.session_manager.merge_messages(session_id, messages)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Session load failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions/<session_id>/export', methods=['GET'])
def export_session(session_id):
    """导出会话数据"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            raise ValidationError(f"Session {session_id} not found")
        return jsonify(session)
    except Exception as e:
        logger.error(f"Session export failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
