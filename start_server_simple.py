#!/usr/bin/env python3
"""
简化的服务器启动脚本 - 避免导入不需要的依赖
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入server模块
from interpreter.server.app import create_app
from waitress import serve

def main():
    """启动服务器"""
    host = "0.0.0.0"
    port = 5002

    print(f"Starting server on http://{host}:{port}")
    print("Press Ctrl+C to stop")

    try:
        app = create_app()
        serve(app, host=host, port=port)
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
