"""
健康检查路由模块
"""

from flask import Blueprint, jsonify, request, current_app
from ..log_config import log_error
from ..errors import format_error_response
from ..utils import get_system_info, format_size  # Updated import path

bp = Blueprint('health', __name__)

@bp.route('/v1/health', methods=['GET'])
def health_check():
    """
    系统健康检查端点
    
    Returns:
        JSON响应，包含系统状态信息
    """
    try:
        detail = request.args.get('detail', 'basic')
        response = {
            "status": "healthy",
            "version": getattr(current_app, 'version', 'unknown'),
            "llm": {
                "model": getattr(current_app.interpreter_instance.llm, 'model', 'unknown'),
                "status": "ready"
            }
        }
        
        if detail == 'full':
            try:
                sys_info = get_system_info()
                if "memory" in sys_info:
                    sys_info["memory"]["total"] = format_size(sys_info["memory"]["total"])
                    sys_info["memory"]["available"] = format_size(sys_info["memory"]["available"])
                if "disk" in sys_info:
                    sys_info["disk"]["total"] = format_size(sys_info["disk"]["total"])
                    sys_info["disk"]["free"] = format_size(sys_info["disk"]["free"])
                response["system"] = sys_info
            except Exception as e:
                response["system"] = {"error": str(e)}
            
        return jsonify(response)
    except Exception as e:
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code