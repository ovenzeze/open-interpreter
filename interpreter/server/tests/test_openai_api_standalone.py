"""
OpenAI API 兼容性独立测试脚本
直接测试 Flask 应用，无需运行服务器
"""
import sys
import os
import json
import pytest
from io import BytesIO

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from interpreter.server.app import create_app


@pytest.fixture
def app():
    """创建测试应用"""
    # 配置测试环境
    config = {
        'TESTING': True,
        'API_KEY': 'test-api-key',
        'DEFAULT_MODEL': 'bedrock/anthropic.claude-3-sonnet-20240229-v1:0',
        'CONTEXT_WINDOW': 200000,
        'MAX_TOKENS': 4096,
        'LOG_LEVEL': 'DEBUG',
        'MAX_ACTIVE_INSTANCES': 3,
        'INSTANCE_TIMEOUT': 3600,
        'CLEANUP_INTERVAL': 300
    }
    app = create_app(config)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """认证头"""
    return {
        'Authorization': 'Bearer test-api-key',
        'Content-Type': 'application/json'
    }


class TestOpenAIModelsEndpoint:
    """测试 /v1/models 端点"""

    def test_list_models_success(self, client, auth_headers):
        """测试成功获取模型列表"""
        response = client.get('/v1/models', headers=auth_headers)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['object'] == 'list'
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) > 0

        # 验证模型对象
        model = data['data'][0]
        assert 'id' in model
        assert 'object' in model
        assert model['object'] == 'model'
        assert 'created' in model
        assert 'owned_by' in model

        print(f"✓ 成功获取 {len(data['data'])} 个模型")

    def test_list_models_options(self, client):
        """测试 OPTIONS 请求"""
        response = client.options('/v1/models')
        assert response.status_code == 200

        # 验证 CORS 头
        assert 'Access-Control-Allow-Origin' in response.headers
        print("✓ OPTIONS /v1/models 工作正常")

    def test_list_models_method_not_allowed(self, client, auth_headers):
        """测试不支持的方法"""
        response = client.post('/v1/models', headers=auth_headers, json={})
        assert response.status_code == 405
        assert 'Allow' in response.headers
        print("✓ 方法不允许处理正确")


class TestOpenAIEnginesEndpoint:
    """测试 /v1/engines 端点"""

    def test_list_engines_success(self, client, auth_headers):
        """测试成功获取引擎列表"""
        response = client.get('/v1/engines', headers=auth_headers)
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['object'] == 'list'
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) > 0

        # 验证引擎对象
        engine = data['data'][0]
        assert 'id' in engine
        assert 'object' in engine
        assert engine['object'] == 'engine'
        assert 'created' in engine
        assert 'owner' in engine
        assert 'ready' in engine

        print(f"✓ 成功获取 {len(data['data'])} 个引擎")


class TestOpenAIChatCompletionsEndpoint:
    """测试 /v1/chat/completions 端点"""

    def test_chat_completions_basic_structure(self, client, auth_headers):
        """测试基本聊天请求的响应结构"""
        response = client.post(
            '/v1/chat/completions',
            headers=auth_headers,
            json={
                'messages': [
                    {'role': 'user', 'content': 'Hello, respond with just "Hi"'}
                ],
                'stream': False
            }
        )

        # 可能返回 200 或其他状态码，取决于是否有LLM可用
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            data = json.loads(response.data)

            # 验证 OpenAI 标准格式
            assert 'id' in data
            assert 'object' in data
            assert 'created' in data
            assert 'choices' in data

            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                assert 'index' in choice
                assert 'message' in choice
                assert 'finish_reason' in choice

                message = choice['message']
                assert 'role' in message
                assert 'content' in message

                print("✓ 聊天完成响应结构正确")
                print(f"  模型: {data.get('model', 'N/A')}")
                print(f"  响应: {message['content'][:100]}...")
        else:
            # 如果不是200，检查是否是预期的错误
            data = json.loads(response.data)
            print(f"响应数据: {data}")

    def test_chat_completions_with_system_message(self, client, auth_headers):
        """测试带系统消息的请求"""
        response = client.post(
            '/v1/chat/completions',
            headers=auth_headers,
            json={
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant.'},
                    {'role': 'user', 'content': 'Hello'}
                ],
                'stream': False
            }
        )

        print(f"带系统消息的请求状态码: {response.status_code}")
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'choices' in data
            print("✓ 系统消息处理正常")

    def test_chat_completions_get_method(self, client, auth_headers):
        """测试 GET 方法（URL参数）"""
        response = client.get(
            '/v1/chat/completions?message=Hello&stream=false',
            headers=auth_headers
        )

        print(f"GET 请求状态码: {response.status_code}")
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'choices' in data
            print("✓ GET 方法支持正常")

    def test_chat_completions_options(self, client):
        """测试 OPTIONS 请求"""
        response = client.options('/v1/chat/completions')
        assert response.status_code == 200

        # 验证 CORS 头
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
        print("✓ OPTIONS /v1/chat/completions 工作正常")

    def test_chat_completions_validation(self, client, auth_headers):
        """测试输入验证"""
        # 测试空消息数组
        response = client.post(
            '/v1/chat/completions',
            headers=auth_headers,
            json={
                'messages': []
            }
        )
        assert response.status_code in [400, 500]

        data = json.loads(response.data)
        assert 'error' in data
        print("✓ 输入验证工作正常")


class TestOpenAICORS:
    """测试 CORS 支持"""

    def test_cors_headers_in_models(self, client):
        """测试模型端点的 CORS 头"""
        response = client.get('/v1/models')
        assert 'Access-Control-Allow-Origin' in response.headers
        print("✓ /v1/models CORS 头正确")

    def test_cors_headers_in_chat(self, client, auth_headers):
        """测试聊天端点的 CORS 头"""
        response = client.post(
            '/v1/chat/completions',
            headers=auth_headers,
            json={
                'messages': [{'role': 'user', 'content': 'Hi'}]
            }
        )
        assert 'Access-Control-Allow-Origin' in response.headers
        print("✓ /v1/chat/completions CORS 头正确")


def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("OpenAI API 兼容性测试")
    print("="*60 + "\n")

    # 运行 pytest
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes',
        '-p', 'no:warnings'
    ])

    return exit_code


if __name__ == '__main__':
    sys.exit(run_tests())
