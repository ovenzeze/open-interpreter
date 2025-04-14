"""
测试OpenAI兼容接口的405方法不允许响应
"""
import pytest


def test_openai_chat_completions_method_not_allowed(client):
    """测试OpenAI聊天完成接口对不允许的HTTP方法的处理"""
    # 测试GET方法 (应该返回405)
    response = client.get("/v1/chat/completions")
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"
    # 验证 Allow 头部是否正确设置
    assert "Allow" in response.headers
    assert "POST" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    
    # 测试PUT方法 (应该返回405)
    response = client.put(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hello"}]}
    )
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"
    # 验证 Allow 头部是否正确设置
    assert "Allow" in response.headers
    assert "POST" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    
    # 测试DELETE方法 (应该返回405)
    response = client.delete("/v1/chat/completions")
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"


def test_openai_models_method_not_allowed(client):
    """测试OpenAI模型列表接口对不允许的HTTP方法的处理"""
    # 测试POST方法 (应该返回405)
    response = client.post(
        "/v1/models",
        json={}
    )
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"
    # 验证 Allow 头部是否正确设置
    assert "Allow" in response.headers
    assert "GET" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    
    # 测试PUT方法 (应该返回405)
    response = client.put("/v1/models", json={})
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"


def test_openai_engines_method_not_allowed(client):
    """测试OpenAI引擎列表接口对不允许的HTTP方法的处理"""
    # 测试POST方法 (应该返回405)
    response = client.post(
        "/v1/engines",
        json={}
    )
    assert response.status_code == 405
    assert "error" in response.json()
    assert response.json()["error"]["type"] == "MethodNotAllowedError"
    # 验证 Allow 头部是否正确设置
    assert "Allow" in response.headers
    assert "GET" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]


def test_openai_options_method(client):
    """测试OpenAI接口对OPTIONS方法的处理"""
    # 测试聊天完成接口的OPTIONS方法
    response = client.options("/v1/chat/completions")
    assert response.status_code == 200
    # 验证响应内容
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    assert "message" in response.json()
    # 验证头部信息
    assert "Allow" in response.headers
    assert "POST" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers
    
    # 测试模型列表接口的OPTIONS方法
    response = client.options("/v1/models")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    # 验证头部信息
    assert "Allow" in response.headers
    assert "GET" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    assert "Access-Control-Allow-Methods" in response.headers
    
    # 测试引擎列表接口的OPTIONS方法
    response = client.options("/v1/engines")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "success"
    # 验证头部信息
    assert "Allow" in response.headers
    assert "GET" in response.headers["Allow"]
    assert "OPTIONS" in response.headers["Allow"]
    assert "Access-Control-Allow-Methods" in response.headers 