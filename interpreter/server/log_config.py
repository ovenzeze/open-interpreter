"""
Logging configuration for Open Interpreter HTTP Server
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

class ServerFormatter(logging.Formatter):
    """自定义日志格式化器"""
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

class ServerRichHandler(logging.StreamHandler):
    """自定义控制台处理器"""
    def __init__(self, level=logging.INFO):
        super().__init__()
        self.setLevel(level)
        self.setFormatter(ServerFormatter())

class DailyRotatingFileHandler(RotatingFileHandler):
    """自定义每日轮转文件处理器"""
    def __init__(self, filename):
        maxBytes = 10 * 1024 * 1024  # 10MB
        backupCount = 5
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount)

# 创建 logger
logger = logging.getLogger('interpreter_server')

def setup_logging(
    app_name: str,
    log_level: str = 'INFO',
    log_dir: Optional[str] = None
) -> logging.Logger:
    """Configure enhanced logging with both file and rich console handlers"""
    global logger
    
    # 初始化处理器变量
    error_handler = None
    info_handler = None
    console_handler = None
    
    try:
        # Validate log level
        log_level_num = getattr(logging, log_level.upper())
        
        logger = logging.getLogger(app_name)
        logger.setLevel(log_level_num)
        
        # Prevent duplicate handlers
        if logger.hasHandlers():
            logger.handlers.clear()
        
        # Setup log directory
        if not log_dir:
            log_dir = Path(__file__).parent.parent.parent / 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Create handlers
        error_handler = DailyRotatingFileHandler(
            os.path.join(log_dir, 'error.log')
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(ServerFormatter())
        
        info_handler = DailyRotatingFileHandler(
            os.path.join(log_dir, 'info.log')
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(ServerFormatter())
        
        console_handler = ServerRichHandler(level=log_level_num)
        
        # Add handlers
        logger.addHandler(error_handler)
        logger.addHandler(info_handler)
        logger.addHandler(console_handler)
        
        return logger
        
    except Exception as e:
        # Clean up handlers if setup fails
        handlers = [h for h in (error_handler, info_handler, console_handler) if h is not None]
        for handler in handlers:
            try:
                handler.close()
            except:
                pass
        raise RuntimeError(f"Failed to setup logging: {str(e)}") from e

def log_request_info(request) -> None:
    """记录请求信息"""
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    # 只在非 GET 请求且内容类型为 JSON 时解析 JSON 数据
    if request.method != 'GET' and request.is_json:
        try:
            logger.debug(f"JSON Data: {request.get_json()}")
        except Exception as e:
            logger.warning(f"Failed to parse JSON data: {str(e)}")

def log_response_info(response) -> None:
    """记录响应信息"""
    logger.info(f"Response Status: {response.status_code}")
    logger.debug(f"Response Headers: {dict(response.headers)}")
    if response.is_json:
        try:
            logger.debug(f"Response Data: {response.get_json()}")
        except Exception as e:
            logger.warning(f"Failed to parse response JSON data: {str(e)}")

def log_error(error: Exception) -> None:
    """记录错误信息"""
    logger.error(str(error), exc_info=True)

__all__ = ['logger', 'setup_logging', 'log_request_info', 'log_response_info', 'log_error']