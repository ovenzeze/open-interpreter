"""
OpenAPI 规范自动生成脚本

扫描 Flask 路由和 Pydantic 模型，生成 openapi.json。
"""
import os
import json
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
import yaml

# 动态导入 Flask app 和 Pydantic 模型
from interpreter.server.app import create_app
from interpreter.server.models import (
    # List all Pydantic models you want to include
    MessageBase, MessageCreate, Session, SessionUpdate, 
    SessionCreate, SessionListResponse, APIResponse
)

# 创建 Flask app 实例 (不运行)
app = create_app()

# 配置 APISpec
spec = APISpec(
    title="Open Interpreter Server API",
    version="1.0.0",
    openapi_version="3.0.3",
    plugins=[FlaskPlugin(), MarshmallowPlugin()],
    info={
        "description": "OpenAI-compatible API server for Open Interpreter, with auto-generated OpenAPI documentation."
    }
)

# 定义 Pydantic 模型如何映射到 OpenAPI 组件
# (This part is still under development in apispec, we might need a workaround)


# 扫描所有 Flask 路由
with app.test_request_context():
    for rule in app.url_map.iter_rules():
        # 忽略 Flask 默认的 /static 路由
        if rule.endpoint != 'static':
            try:
                spec.path(view=app.view_functions[rule.endpoint])
            except Exception as e:
                print(f"Could not generate spec for endpoint {rule.endpoint}: {e}")


# 生成并保存 openapi.json
output_path = os.path.join(os.path.dirname(__file__), 'openapi.json')
with open(output_path, 'w') as f:
    json.dump(spec.to_dict(), f, indent=2)

print(f"✅ OpenAPI specification generated successfully at: {output_path}")
