"""
测试 Open Interpreter HTTP Server 的所有关键端点
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:5001"

def test_endpoint(endpoint: str, method: str = "GET", data: Dict[str, Any] = None, timeout: int = 60, display: bool = False) -> Dict[str, Any]:
    """测试单个端点"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"} if data else {}
    
    if display:
        print(f"\n测试端点: {method} {endpoint}")
        print(f"请求数据: {json.dumps(data, ensure_ascii=False) if data else 'None'}")
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            if response.status_code >= 500:
                print(f"服务器错误 {response.status_code}，正在重试...")
                retry_count += 1
                time.sleep(5)  # 等待5秒后重试
                continue
                
            if display:
                print(f"状态码: {response.status_code}")
                print(f"响应数据: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            
            return response.json()
            
        except requests.Timeout:
            if display:
                print(f"错误: 请求超时 ({timeout}秒)")
            retry_count += 1
            if retry_count < max_retries:
                print("正在重试...")
                time.sleep(5)
            continue
        except requests.RequestException as e:
            if display:
                print(f"错误: 请求失败 - {str(e)}")
            return None
        except Exception as e:
            if display:
                print(f"错误: {str(e)}")
            return None
    
    print(f"达到最大重试次数 ({max_retries})")
    return None

def run_all_tests():
    """运行所有端点测试"""
    tests_passed = 0
    tests_failed = 0
    
    # 在每个测试之间添加足够的间隔
    test_interval = 3  # 秒
    
    # 1. 测试健康检查接口
    print("\n=== 测试健康检查接口 ===")
    health_response = test_endpoint("/v1/health", display=True)
    if health_response and health_response.get("status") == "healthy":
        print("✅ 健康检查测试通过")
        tests_passed += 1
    else:
        print("❌ 健康检查测试失败")
        tests_failed += 1
    
    time.sleep(test_interval)
    
    # 2. 测试会话管理
    print("\n=== 测试会话管理 ===")
    # 2.1 创建会话
    session_response = test_endpoint("/v1/sessions", "POST", display=True)
    session_id = None
    if session_response and isinstance(session_response, dict) and "session_id" in session_response:
        print("✅ 会话创建测试通过")
        session_id = session_response.get("session_id")
        tests_passed += 1
    else:
        print("❌ 会话创建测试失败")
        tests_failed += 1
        return
    
    time.sleep(test_interval)
    
    # 2.2 获取会话列表
    sessions_response = test_endpoint("/v1/sessions", display=False)
    if sessions_response and "sessions" in sessions_response:
        print("✅ 会话列表测试通过")
        tests_passed += 1
    else:
        print("❌ 会话列表测试失败")
        tests_failed += 1
    
    time.sleep(test_interval)
    
    # 3. 测试基础聊天功能
    print("\n=== 测试基础聊天功能 ===")
    chat_data = {
        "messages": [
            {
                "role": "user",
                "type": "message",
                "content": "Hello, how are you?",
                "format": "text"
            }
        ],
        "session_id": session_id,
        "stream": False
    }
    chat_response = test_endpoint("/v1/chat", "POST", chat_data, display=False)
    if chat_response and "messages" in chat_response:
        print("✅ 基础聊天测试通过")
        tests_passed += 1
    else:
        print("❌ 基础聊天测试失败")
        tests_failed += 1
    
    time.sleep(test_interval)
    
    # 4. 测试 OpenAI 兼容接口
    print("\n=== 测试 OpenAI 兼容接口 ===")
    openai_data = {
        "messages": [
            {
                "role": "user",
                "type": "message",
                "content": "What is 2+2?",
                "format": "text"
            }
        ],
        "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        "session_id": session_id,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 100
    }
    openai_response = test_endpoint("/v1/chat/completions", "POST", openai_data, timeout=60, display=False)
    if openai_response and "choices" in openai_response:
        content = openai_response["choices"][0]["message"]["content"]
        if "4" in content.lower():
            print("✅ OpenAI 兼容接口测试通过")
            tests_passed += 1
        else:
            print(f"❌ OpenAI 兼容接口测试失败：响应内容不正确 - {content}")
            tests_failed += 1
    else:
        print("❌ OpenAI 兼容接口测试失败")
        tests_failed += 1
    
    time.sleep(test_interval)
    
    # 5. 测试流式响应
    print("\n=== 测试流式响应 ===")
    stream_data = {
        "messages": [
            {
                "role": "user",
                "type": "message",
                "content": "Count from 1 to 3",
                "format": "text"
            }
        ],
        "stream": True,
        "session_id": session_id,
        "model": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
    }
    try:
        url = f"{BASE_URL}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=stream_data, stream=True, timeout=60)
        
        if response.status_code == 200:
            chunk_count = 0
            content = ""
            for line in response.iter_lines():
                if line:
                    try:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]  # Remove 'data: ' prefix
                            chunk_data = json.loads(json_str)
                            if 'choices' in chunk_data and chunk_data['choices']:
                                delta = chunk_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content += delta['content']
                                    chunk_count += 1
                                    print(f"收到数据块: {delta['content']}")
                    except json.JSONDecodeError:
                        print(f"警告: 无法解析数据块 - {line_text}")
                        continue
            
            if chunk_count > 0 and any(str(i) in content for i in range(1, 4)):
                print("✅ 流式响应测试通过")
                tests_passed += 1
            else:
                print("❌ 流式响应测试失败：响应内容不符合预期")
                tests_failed += 1
        else:
            print(f"❌ 流式响应测试失败：状态码 {response.status_code}")
            tests_failed += 1
    except requests.Timeout:
        print("❌ 流式响应测试失败：请求超时")
        tests_failed += 1
    except Exception as e:
        print(f"❌ 流式响应测试失败：{str(e)}")
        tests_failed += 1
    
    time.sleep(test_interval)
    
    # 打印测试结果汇总
    print("\n=== 测试结果汇总 ===")
    print(f"通过测试: {tests_passed}")
    print(f"失败测试: {tests_failed}")
    print(f"总体结果: {'✅ 所有测试通过' if tests_failed == 0 else '❌ 部分测试失败'}")

if __name__ == "__main__":
    # 等待服务器完全启动
    print("等待服务器启动...")
    time.sleep(5)  # 增加等待时间
    run_all_tests() 