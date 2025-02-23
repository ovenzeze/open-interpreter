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
    logger = None
    try:
        # 记录启动环境信息
        env_info = {
            'INTERPRETER_HOME': os.getenv('INTERPRETER_HOME'),
            'PYTHONPATH': os.getenv('PYTHONPATH'),
            'PYTHON_VERSION': sys.version,
            'CWD': os.getcwd(),
        }
        
        # 设置日志
        logger = setup_logging(
            app_name="interpreter_server",
            log_level=log_level if not debug else 'DEBUG'
        )
        
        # 输出环境信息
        logger.info("Starting server with environment:")
        for key, value in env_info.items():
            logger.info(f"  {key}: {value}")
        
        # 验证端口可用性
        if not is_port_available(host, port):
            raise RuntimeError(f"Port {port} is already in use")
        
        logger.info("Initializing application...")
        app = create_app()
        logger.info("Application initialized successfully")
        
        # 配置服务器
        if debug:
            logger.info(f"Starting debug server on http://{host}:{port}")
            app.debug = True
            app.run(host=host, port=port, use_reloader=True)
        else:
            logger.info(f"Starting production server on http://{host}:{port}")
            logger.info("Server configuration:")
            logger.info(f"  Host: {host}")
            logger.info(f"  Port: {port}")
            logger.info(f"  Debug: {debug}")
            logger.info(f"  Log Level: {log_level}")
            
            try:
                serve(app, host=host, port=port)
            except Exception as e:
                logger.error(f"Server failed to start: {str(e)}", exc_info=True)
                raise
            
    except Exception as e:
        if logger:
            logger.error(f"Server startup failed: {str(e)}", exc_info=True)
        else:
            print(f"Fatal error during startup: {str(e)}", file=sys.stderr)
            print("Environment information:")
            for key, value in env_info.items():
                print(f"  {key}: {value}")
        sys.exit(1)

def is_port_available(host: str, port: int) -> bool:
    """检查端口是否可用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except socket.error:
            return False

if __name__ == '__main__':
    main()