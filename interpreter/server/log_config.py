"""
Logging configuration for Open Interpreter HTTP Server
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(app_name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    Configure logging with both file and console handlers
    
    Args:
        app_name: Name of the application for the logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 创建日志目录
    log_dir = os.path.join(root_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 移除现有的处理器
    logger.handlers = []
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建并配置错误日志处理器
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'server_err.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # 创建并配置输出日志处理器
    output_handler = RotatingFileHandler(
        os.path.join(log_dir, 'server_out.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    output_handler.setLevel(getattr(logging, log_level.upper()))
    output_handler.setFormatter(formatter)
    
    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(error_handler)
    logger.addHandler(output_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_request_info(logger: logging.Logger, request) -> None:
    """
    记录详细的请求信息
    
    Args:
        logger: Logger实例
        request: Flask请求对象
    """
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    if request.is_json:
        logger.debug(f"JSON Data: {request.get_json()}")

def log_response_info(logger: logging.Logger, response) -> None:
    """
    记录响应信息
    
    Args:
        logger: Logger实例
        response: Flask响应对象
    """
    logger.info(f"Response Status: {response.status_code}")
    logger.debug(f"Response Headers: {dict(response.headers)}")
    if response.is_json:
        logger.debug(f"Response Data: {response.get_json()}")

def log_error(error: Exception) -> None:
    """
    记录错误信息
    
    Args:
        error: 异常实例
    """
    logger = logging.getLogger('interpreter_server')
    logger.error(str(error), exc_info=True) 