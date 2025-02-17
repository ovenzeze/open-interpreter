"""
健康检查路由模块
"""

from flask import Blueprint, jsonify, current_app
from ..log_config import log_error
from ..errors import format_error_response

bp = Blueprint('health', __name__)

@bp.route('/v1/health', methods=['GET'])
def health_check():
    """
    系统健康检查端点
    
    Returns:
        JSON响应，包含系统状态信息
    """
    try:
        response = {
            "status": "healthy",
            "version": current_app.version,
            "llm": {
                "model": current_app.interpreter_instance.llm.model,
                "status": "ready"
            }
        }
        return jsonify(response)
    except Exception as e:
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code 