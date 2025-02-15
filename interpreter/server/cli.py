"""
命令行接口模块
"""

import os
import sys
import click
from flask import Flask
from waitress import serve
from .app import create_app
from .log_config import setup_logging

@click.command()
@click.option('--host', default='0.0.0.0', help='服务器主机地址')
@click.option('--port', default=5001, help='服务器端口')
@click.option('--debug', is_flag=True, help='是否启用调试模式')
@click.option('--log-level', 
              default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
              help='设置日志级别')
def main(host, port, debug, log_level):
    """启动 Open Interpreter HTTP Server"""
    try:
        # 设置日志
        logger = setup_logging(
            app_name="interpreter_server",
            log_level=log_level if not debug else 'DEBUG'
        )
        
        logger.info("Initializing server...")
        
        # 创建应用
        app = create_app()
        
        # 配置服务器
        if debug:
            logger.info(f"Starting server in DEBUG mode on http://{host}:{port}")
            app.debug = True
            app.run(host=host, port=port, use_reloader=True)
        else:
            logger.info(f"Starting server on http://{host}:{port}")
            serve(app, host=host, port=port)
            
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 