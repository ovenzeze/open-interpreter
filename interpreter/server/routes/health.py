"""
健康检查路由模块
"""

from flask import Blueprint, jsonify, request, current_app
from ..log_config import log_error
from ..errors import format_error_response
from ..utils import get_system_info, format_size

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
            "uptime": get_system_info().get("uptime", "unknown")
        }
        
        # 添加 LLM 相关信息
        # 首先尝试从默认解释器实例获取
        if hasattr(current_app, 'interpreter_instance'):
            try:
                interpreter = current_app.interpreter_instance
                model = getattr(interpreter.llm, 'model', 'unknown')
                response["llm"] = {
                    "model": model,
                    "status": "ready"
                }
            except Exception as e:
                response["llm"] = {
                    "model": "unknown",
                    "status": "unknown",
                    "error": str(e)
                }
        # 如果没有默认解释器实例，尝试从会话管理器中获取活跃的解释器实例
        elif hasattr(current_app, 'session_manager') and hasattr(current_app.session_manager, 'interpreter_instances'):
            try:
                # 获取第一个活跃的解释器实例
                instances = current_app.session_manager.interpreter_instances
                if instances:
                    # 获取第一个实例的模型信息
                    first_instance = next(iter(instances.values()))
                    model = getattr(first_instance.llm, 'model', 'unknown')
                    response["llm"] = {
                        "model": model,
                        "status": "ready"
                    }
                else:
                    # 如果没有活跃实例，使用配置中的默认模型
                    model = current_app.config.get('DEFAULT_MODEL', 'unknown')
                    response["llm"] = {
                        "model": model,
                        "status": "ready"
                    }
            except Exception as e:
                response["llm"] = {
                    "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                    "status": "ready",
                    "note": f"Using default model from config due to error: {str(e)}"
                }
        else:
            # 如果无法获取实例，使用配置中的默认值
            response["llm"] = {
                "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                "status": "ready"
            }
        
        # 使用无锁的方式获取实例状态
        if hasattr(current_app, 'session_manager'):
            try:
                active_count = len(current_app.session_manager.interpreter_instances)
                max_count = current_app.session_manager.max_active_instances
                response["instances"] = {
                    "max": max_count,
                    "active": active_count
                }
            except:
                response["instances"] = {
                    "status": "unavailable"
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