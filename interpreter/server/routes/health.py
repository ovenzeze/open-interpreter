"""
健康检查路由模块
"""

from flask import jsonify, request, current_app
from flask_openapi3 import APIBlueprint
from ..log_config import log_error, logger
from ..errors import format_error_response
from ..openapi_models import HealthCheckResponse, FullHealthCheckResponse # 注意：修改这里以从 openapi_models 导入
from ..utils import get_system_info, format_size
import time
import psutil
import os

bp = APIBlueprint('health', __name__, url_prefix='')

def get_uptime():
    """获取服务器运行时间"""
    try:
        process = psutil.Process(os.getpid())
        return time.time() - process.create_time()
    except Exception as e:
        logger.error(f"Error getting uptime: {str(e)}")
        return None

def format_uptime(seconds):
    """格式化运行时间为人类可读的字符串"""
    if seconds is None:
        return "unknown"
    
    days = int(seconds // (24 * 3600))
    hours = int((seconds % (24 * 3600)) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

@bp.get(
    '/v1/health',
    summary="Health check",
    description="Get system health status and information",
    responses={
        "200": FullHealthCheckResponse,
        "200_basic": HealthCheckResponse
    }
)
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
            "uptime": format_uptime(get_uptime())
        }
        
        # 添加 LLM 相关信息
        if hasattr(current_app, 'interpreter_instance'):
            try:
                interpreter = current_app.interpreter_instance
                model = getattr(interpreter.llm, 'model', 'unknown')
                response["llm"] = {
                    "model": model,
                    "status": "ready"
                }
            except Exception as e:
                logger.error(f"Error getting LLM info from interpreter instance: {str(e)}")
                response["llm"] = {
                    "model": "unknown",
                    "status": "error",
                    "error": str(e)
                }
        elif hasattr(current_app, 'session_manager'):
            try:
                # 使用 instance_manager 获取实例状态
                instance_manager = current_app.session_manager.instance_manager
                instances_status = instance_manager.get_instances_status()
                
                # 如果有活跃实例，获取第一个实例的模型信息
                if instances_status["active_instances"] > 0:
                    # 获取第一个活跃实例的会话ID
                    first_session_id = next(iter(instance_manager.interpreter_instances.keys()))
                    interpreter = instance_manager.get_instance(first_session_id)
                    if interpreter:
                        model = getattr(interpreter.llm, 'model', 'unknown')
                        response["llm"] = {
                            "model": model,
                            "status": "ready"
                        }
                    else:
                        response["llm"] = {
                            "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                            "status": "ready",
                            "note": "Using default model from config"
                        }
                else:
                    response["llm"] = {
                        "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                        "status": "ready",
                        "note": "No active instances, using default model"
                    }
            except Exception as e:
                logger.error(f"Error getting LLM info from session manager: {str(e)}")
                response["llm"] = {
                    "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                    "status": "error",
                    "error": str(e)
                }
        else:
            response["llm"] = {
                "model": current_app.config.get('DEFAULT_MODEL', 'unknown'),
                "status": "not_initialized",
                "note": "LLM not initialized yet"
            }
        
        # 获取实例状态
        if hasattr(current_app, 'session_manager'):
            try:
                # 使用 instance_manager 获取实例状态
                instance_manager = current_app.session_manager.instance_manager
                instances_status = instance_manager.get_instances_status()
                
                response["instances"] = {
                    "max": instances_status["max_instances"],
                    "active": instances_status["active_instances"],
                    "status": "available",
                    "status_counts": instances_status.get("status_counts", {}),
                    "is_optimizing": instances_status.get("is_optimizing", False)
                }
            except Exception as e:
                logger.error(f"Error getting instance status: {str(e)}")
                response["instances"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            response["instances"] = {
                "status": "not_initialized",
                "note": "Session manager not initialized"
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
                logger.error(f"Error getting system info: {str(e)}")
                response["system"] = {"error": str(e)}
            
        return jsonify(response)
    except Exception as e:
        log_error(e)
        error_response, status_code = format_error_response(e)
        return jsonify(error_response), status_code
