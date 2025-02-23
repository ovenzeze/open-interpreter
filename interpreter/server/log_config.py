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
from .logging.formatters import ServerFormatter, ServerRichHandler
from .logging.handlers import DailyRotatingFileHandler

def setup_logging(
    app_name: str,
    log_level: str = 'INFO',
    log_dir: Optional[str] = None
) -> logging.Logger:
    """
    Configure enhanced logging with both file and rich console handlers
    """
    # Validate log level
    try:
        log_level_num = getattr(logging, log_level.upper())
    except AttributeError:
        raise ValueError(f"Invalid log level: {log_level}")
    
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level_num)
    
    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Setup log directory
    if not log_dir:
        log_dir = Path(__file__).parent.parent.parent / 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Ensure all handlers are properly closed on error
    try:
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
        
        # Console handler with Rich formatting
        console_handler = ServerRichHandler(level=log_level_num)
        
        # Add all handlers
        logger.addHandler(error_handler)
        logger.addHandler(info_handler)
        logger.addHandler(console_handler)
        
        return logger
    except Exception as e:
        # Clean up handlers if setup fails
        for handler in [error_handler, info_handler, console_handler]:
            try:
                handler.close()
            except:
                pass
        raise RuntimeError(f"Failed to setup logging: {str(e)}") from e

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
    """Log error with traceback"""
    logger = logging.getLogger('interpreter_server')
    logger.error(str(error), exc_info=True)