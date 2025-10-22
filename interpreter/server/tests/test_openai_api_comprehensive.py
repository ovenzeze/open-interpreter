"""
全面的 OpenAI 兼容性 API 测试

测试覆盖：
1. /v1/models - 获取模型列表
2. /v1/engines - 获取引擎列表（旧版兼容）
3. /v1/chat/completions - 聊天完成接口（POST和GET）
4. 流式响应测试
5. 方法验证测试（OPTIONS）
"""
import pytest
import json
import time


class TestOpenAIModelsAPI:
    """测试 /v1/models 端点"""

    def test_list_models_get(self, client):
        """测试 GET /v1/models - 获取模型列表"""
        response = client.get("/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # 验证模型对象结构
        model = data["data"][0]
        assert "id" in model
        assert "object" in model
        assert model["object"] == "model"
        assert "created" in model
        assert "owned_by" in model

    def test_list_models_options(self, client):
        """测试 OPTIONS /v1/models - 验证CORS预检请求"""
        response = client.options("/v1/models")
        assert response.status_code == 200

        # 验证CORS头
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

    def test_list_models_method_not_allowed(self, client):
        """测试不支持的HTTP方法"""
        response = client.post("/v1/models", json={})
        assert response.status_code == 405
        assert "Allow" in response.headers


class TestOpenAIEnginesAPI:
    """测试 /v1/engines 端点（旧版兼容）"""

    def test_list_engines_get(self, client):
        """测试 GET /v1/engines - 获取引擎列表"""
        response = client.get("/v1/engines")
        assert response.status_code == 200

        data = response.json()
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # 验证引擎对象结构
        engine = data["data"][0]
        assert "id" in engine
        assert "object" in engine
        assert engine["object"] == "engine"
        assert "created" in engine
        assert "owner" in engine
        assert "ready" in engine
        assert engine["ready"] == True

    def test_list_engines_options(self, client):
        """测试 OPTIONS /v1/engines - 验证CORS预检请求"""
        response = client.options("/v1/engines")
        assert response.status_code == 200

        # 验证CORS头
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers


class TestOpenAIChatCompletionsAPI:
    """测试 /v1/chat/completions 端点"""

    def test_chat_completions_post_basic(self, client):
        """测试 POST /v1/chat/completions - 基本聊天请求"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Say 'test' only"}
                ],
                "stream": False
            }
        )
        assert response.status_code == 200

        data = response.json()
        # 验证 OpenAI 标准响应格式
        assert "id" in data
        assert "object" in data
        assert data["object"] in ["chat.completion", "chat.completion.chunk"]
        assert "created" in data
        assert isinstance(data["created"], int)
        assert "model" in data
        assert "choices" in data
        assert isinstance(data["choices"], list)
        assert len(data["choices"]) > 0

        # 验证 choice 结构
        choice = data["choices"][0]
        assert "index" in choice
        assert "message" in choice
        assert "finish_reason" in choice

        # 验证 message 结构
        message = choice["message"]
        assert "role" in message
        assert message["role"] == "assistant"
        assert "content" in message
        assert isinstance(message["content"], str)

    def test_chat_completions_post_with_system_message(self, client):
        """测试带系统消息的聊天请求"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello"}
                ],
                "stream": False
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_chat_completions_post_with_model(self, client):
        """测试指定模型的聊天请求"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
                "stream": False
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "model" in data

    def test_chat_completions_post_with_session_id(self, client):
        """测试带会话ID的聊天请求"""
        # 首先创建一个会话
        session_response = client.post("/api/sessions")
        assert session_response.status_code == 201
        session_id = session_response.json()["session"]["session_id"]

        # 使用会话ID进行聊天
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "session_id": session_id,
                "stream": False
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data

    def test_chat_completions_get_method(self, client):
        """测试 GET /v1/chat/completions - URL参数方式"""
        response = client.get(
            "/v1/chat/completions?message=Hello&stream=false"
        )
        assert response.status_code == 200

        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_chat_completions_options(self, client):
        """测试 OPTIONS /v1/chat/completions - CORS预检"""
        response = client.options("/v1/chat/completions")
        assert response.status_code == 200

        # 验证CORS头
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers

    def test_chat_completions_streaming(self, client):
        """测试流式响应"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Count to 3"}
                ],
                "stream": True
            }
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/event-stream"

        # 验证流式响应
        chunks = []
        for line in response.data.decode('utf-8').split('\n'):
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str.strip() and data_str.strip() != '[DONE]':
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        pass

        # 验证至少收到了一些数据块
        assert len(chunks) > 0

        # 验证数据块结构
        for chunk in chunks:
            assert "id" in chunk
            assert "object" in chunk
            assert chunk["object"] == "chat.completion.chunk"
            assert "created" in chunk
            assert "choices" in chunk

            if chunk["choices"]:
                choice = chunk["choices"][0]
                assert "index" in choice
                assert "delta" in choice


class TestOpenAIErrorHandling:
    """测试错误处理"""

    def test_chat_completions_missing_messages(self, client):
        """测试缺少消息的请求"""
        response = client.post(
            "/v1/chat/completions",
            json={}
        )
        assert response.status_code in [400, 500]  # 应该返回错误

        data = response.json()
        assert "error" in data

    def test_chat_completions_invalid_json(self, client):
        """测试无效的JSON"""
        response = client.post(
            "/v1/chat/completions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 500]

    def test_chat_completions_empty_messages(self, client):
        """测试空消息数组"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": []
            }
        )
        assert response.status_code in [400, 500]


class TestOpenAICompatibility:
    """测试 OpenAI 兼容性"""

    def test_response_format_matches_openai(self, client):
        """测试响应格式是否匹配 OpenAI 标准"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": False
            }
        )
        assert response.status_code == 200

        data = response.json()

        # OpenAI 标准字段
        required_fields = ["id", "object", "created", "model", "choices"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # choices 必须是列表
        assert isinstance(data["choices"], list)

        # 每个 choice 必须有这些字段
        if len(data["choices"]) > 0:
            choice_required_fields = ["index", "message", "finish_reason"]
            for field in choice_required_fields:
                assert field in data["choices"][0], f"Missing choice field: {field}"

            # message 必须有 role 和 content
            message = data["choices"][0]["message"]
            assert "role" in message
            assert "content" in message

    def test_cors_headers_present(self, client):
        """测试CORS头是否存在"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        )

        # 验证CORS头
        assert "Access-Control-Allow-Origin" in response.headers

    def test_content_type_json(self, client):
        """测试响应的Content-Type"""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": False
            }
        )

        assert "application/json" in response.headers.get("Content-Type", "")


# 运行测试的辅助函数
def run_comprehensive_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_comprehensive_tests()
