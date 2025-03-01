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
@bp.route('/v1/sessions', methods=['GET', 'POST'])
def sessions():
    """会话管理接口"""
    try:
        if request.method == 'GET':
            # 获取分页参数
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            
            # 获取会话列表
            sessions = current_app.session_manager.list_sessions(page, limit)
            
            # 规范化会话数据
            from ..utils import normalize_session_batch
            normalized_sessions = normalize_session_batch(sessions['sessions'])
            
            # 返回规范化后的会话列表
            return jsonify({
                'sessions': normalized_sessions,
                'total': sessions['total'],
                'page': page,
                'limit': limit
            })
            
        elif request.method == 'POST':
            # 创建新会话
            data = request.get_json()
            session = current_app.session_manager.create_session(data)
            
            # 规范化会话数据
            from ..utils import normalize_session
            normalized_session = normalize_session(session)
            
            return jsonify(normalized_session), 201
            
    except Exception as e:
        logger.error(f"Session operation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.route('/v1/sessions/<session_id>', methods=['GET', 'PATCH', 'DELETE'])
def manage_session(session_id):
    """管理单个会话"""
    try:
        if request.method == 'GET':
            session = current_app.session_manager.get_session(session_id)
            if not session:
                logger.debug(f"Session not found: {session_id}")
                return jsonify({"error": "Session not found"}), 404
                
            # 规范化会话数据
            from ..utils import normalize_session
            normalized_session = normalize_session(session)
                
            return jsonify(normalized_session)
            
        elif request.method == 'PATCH':
            data = request.get_json()
            session = current_app.session_manager.update_session(session_id, data)
            if not session:
                return jsonify({"error": "Session not found"}), 404
                
            # 规范化会话数据
            from ..utils import normalize_session
            normalized_session = normalize_session(session)
                
            return jsonify(normalized_session)
            
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
        # 首先检查会话是否存在
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when accessing messages: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        if request.method == 'GET':
            messages = current_app.session_manager.get_messages(session_id)
            if messages is None:
                messages = []
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
        # 首先检查会话是否存在
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when adding message: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        data = request.get_json()
        if not isinstance(data, dict) or 'content' not in data or 'role' not in data:
            raise ValidationError("Invalid message format")

        success = current_app.session_manager.add_message(session_id, data)
        if not success:
            raise ValidationError("Failed to add message")
            
        # 重新获取会话并规范化数据
        from ..utils import normalize_session
        updated_session = current_app.session_manager.get_session(session_id)
        if updated_session:
            normalized_session = normalize_session(updated_session)
            return jsonify({"success": True, "session": normalized_session})
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Message operation failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

# 辅助功能路由
@bp.route('/v1/sessions/<session_id>/load', methods=['POST'])
def load_session(session_id):
    """加载历史会话"""
    try:
        # 首先检查会话是否存在
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when loading: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
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
            logger.debug(f"Session not found when exporting: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session)
    except Exception as e:
        logger.error(f"Session export failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
