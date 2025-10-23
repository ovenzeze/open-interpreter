"""
会话管理相关的路由处理模块
包含会话的创建、列表、消息获取等功能
"""

from flask import jsonify, request, current_app
from flask_openapi3 import APIBlueprint
from ..errors import ValidationError, format_error_response
from ..models import SessionCreate, Session, SessionUpdate, SessionListResponse, MessageBase
from ..openapi_models import AddMessageRequest, AddMessageResponse, SuccessResponse, LoadSessionRequest, MessageMeta, SessionFull, MessagesListResponse
from ..log_config import log_request_info, log_response_info, logger  # 导入 logger
from typing import List, Dict, Any, Optional # 导入必要的类型

bp = APIBlueprint('session', __name__, url_prefix='')

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
@bp.get(
    '/v1/sessions',
    summary="List sessions",
    description="Get a paginated list of all sessions",
    responses={"200": SessionListResponse}
)
def list_sessions():
    """获取会话列表"""
    try:
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
    except Exception as e:
        logger.error(f"List sessions failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.post(
    '/v1/sessions',
    summary="Create session",
    description="Create a new chat session",
    responses={"200": SessionFull} # 返回完整会话信息
)
def create_session():
    """创建新会话"""
    try:
        # 创建新会话
        data = request.json # 从请求体获取数据
        session = current_app.session_manager.create_session(data)
        
        # 规范化会话数据
        from ..utils import normalize_session
        normalized_session = normalize_session(session)
        
        return jsonify(normalized_session), 201
    except Exception as e:
        logger.error(f"Create session failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.get(
    '/v1/sessions/<session_id>',
    summary="Get session",
    description="Get details of a specific session",
    responses={"200": SessionFull}
)
def get_session(session_id: str):
    """获取单个会话"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        # 规范化会话数据
        from ..utils import normalize_session
        normalized_session = normalize_session(session)
            
        return jsonify(normalized_session)
    except Exception as e:
        logger.error(f"Get session failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.patch(
    '/v1/sessions/<session_id>',
    summary="Update session",
    description="Update session metadata",
    responses={"200": SessionFull}
)
def update_session(session_id: str):
    """更新会话"""
    try:
        data = request.json # 从请求体获取数据
        session = current_app.session_manager.update_session(session_id, data)
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        # 规范化会话数据
        from ..utils import normalize_session
        normalized_session = normalize_session(session)
            
        return jsonify(normalized_session)
    except Exception as e:
        logger.error(f"Update session failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.delete(
    '/v1/sessions/<session_id>',
    summary="Delete session",
    description="Delete a session",
    responses={"200": SuccessResponse}
)
def delete_session(session_id: str):
    """删除会话"""
    try:
        if not current_app.session_manager.get_session(session_id):
            return jsonify({"error": "Session not found"}), 404
        current_app.session_manager._remove_session(session_id)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Delete session failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

# 会话消息管理路由
@bp.get(
    '/v1/sessions/<session_id>/messages',
    summary="Get messages",
    description="Get all messages from a session",
    responses={
        "200": MessagesListResponse,
        "404": {"description": "Session not found"}
    }
)
def get_messages(session_id: str):
    """获取会话消息"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when accessing messages: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        messages = current_app.session_manager.get_messages(session_id)
        if messages is None:
            messages = []
        return jsonify({"messages": messages})
    except Exception as e:
        logger.error(f"Get messages failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.post(
    '/v1/sessions/<session_id>/messages',
    summary="Add message",
    description="Add a message to a session",
    responses={"200": AddMessageResponse}
)
def add_message(session_id: str):
    """添加消息到会话"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when adding message: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        data = request.json

        success = current_app.session_manager.add_message(session_id, data)
        if not success:
            raise ValidationError("Failed to add message")
            
        from ..utils import normalize_session
        updated_session = current_app.session_manager.get_session(session_id)
        if updated_session:
            normalized_session = normalize_session(updated_session)
            return jsonify({"success": True, "session": normalized_session})
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Add message failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.delete(
    '/v1/sessions/<session_id>/messages',
    summary="Clear messages",
    description="Clear all messages from a session",
    responses={"200": SuccessResponse}
)
def clear_messages(session_id: str):
    """清空会话消息"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        current_app.session_manager.update_session(session_id, {"messages": []})
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Clear messages failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

# 辅助功能路由
@bp.post(
    '/v1/sessions/<session_id>/load',
    summary="Load session history",
    description="Load messages into a session",
    responses={"200": SuccessResponse}
)
def load_session(session_id: str):
    """加载历史会话"""
    try:
        session = current_app.session_manager.get_session(session_id)
        if not session:
            logger.debug(f"Session not found when loading: {session_id}")
            return jsonify({"error": "Session not found"}), 404
            
        messages = [MessageBase.model_validate(msg) for msg in request.json.get('messages', [])]
        current_app.session_manager.merge_messages(session_id, messages)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Session load failed: {str(e)}", exc_info=True)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code

@bp.get(
    '/v1/sessions/<session_id>/export',
    summary="Export session",
    description="Export complete session data",
    responses={"200": SessionFull}
)
def export_session(session_id: str):
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
