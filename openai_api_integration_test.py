#!/usr/bin/env python3
"""
OpenAI API 集成测试脚本
基于OpenAPI规范和LLM服务的通用测试框架
"""

import requests
import json
import time
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import threading
import queue

class APITestResult:
    """测试结果类"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error_message = ""
        self.response_data = None
        self.response_time = 0.0
        self.status_code = None

class OpenAIAPITester:
    """OpenAI API 集成测试器"""
    
    def __init__(self, base_url: str = "http://localhost:5002", api_key: str = "test-key"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.results: List[APITestResult] = []
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def print_header(self, text: str):
        """打印测试标题"""
        print("\n" + "="*70)
        print(f" {text}")
        print("="*70)
    
    def print_test_result(self, result: APITestResult):
        """打印单个测试结果"""
        status = "✓ PASS" if result.passed else "✗ FAIL"
        color_code = "\033[92m" if result.passed else "\033[91m"
        reset_code = "\033[0m"
        
        print(f"{color_code}{status}{reset_code} {result.name}")
        if result.response_time > 0:
            print(f"      响应时间: {result.response_time:.3f}s")
        if result.status_code:
            print(f"      状态码: {result.status_code}")
        if result.error_message:
            print(f"      错误: {result.error_message}")
    
    def test_models_endpoint(self) -> APITestResult:
        """测试 /v1/models 端点"""
        result = APITestResult("GET /v1/models")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/v1/models", timeout=10)
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code != 200:
                result.error_message = f"状态码错误: {response.status_code}"
                return result
            
            data = response.json()
            result.response_data = data
            
            # 验证OpenAI标准格式
            if data.get("object") != "list":
                result.error_message = f"object字段错误: {data.get('object')}"
                return result
            
            if "data" not in data or not isinstance(data["data"], list):
                result.error_message = "缺少data数组或格式错误"
                return result
            
            if len(data["data"]) == 0:
                result.error_message = "模型列表为空"
                return result
            
            # 验证模型对象结构
            model = data["data"][0]
            required_fields = ["id", "object", "created", "owned_by"]
            missing_fields = [f for f in required_fields if f not in model]
            
            if missing_fields:
                result.error_message = f"模型对象缺少字段: {missing_fields}"
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_engines_endpoint(self) -> APITestResult:
        """测试 /v1/engines 端点"""
        result = APITestResult("GET /v1/engines")
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/v1/engines", timeout=10)
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code != 200:
                result.error_message = f"状态码错误: {response.status_code}"
                return result
            
            data = response.json()
            result.response_data = data
            
            # 验证OpenAI标准格式
            if data.get("object") != "list":
                result.error_message = f"object字段错误: {data.get('object')}"
                return result
            
            if "data" not in data or not isinstance(data["data"], list):
                result.error_message = "缺少data数组或格式错误"
                return result
            
            # 验证引擎对象结构
            engine = data["data"][0]
            required_fields = ["id", "object", "created"]
            missing_fields = [f for f in required_fields if f not in engine]
            
            if missing_fields:
                result.error_message = f"引擎对象缺少字段: {missing_fields}"
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_chat_completions_non_streaming(self) -> APITestResult:
        """测试非流式聊天完成"""
        result = APITestResult("POST /v1/chat/completions (非流式)")
        
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "简单回复：你好"}
                ],
                "stream": False,
                "model": "gpt-3.5-turbo"
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code != 200:
                result.error_message = f"状态码错误: {response.status_code}"
                try:
                    error_data = response.json()
                    result.error_message += f" - {error_data}"
                except:
                    pass
                return result
            
            data = response.json()
            result.response_data = data
            
            # 验证OpenAI标准响应格式
            required_fields = ["id", "object", "created", "model", "choices"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.error_message = f"响应缺少字段: {missing_fields}"
                return result
            
            # 验证choices
            if not data["choices"] or len(data["choices"]) == 0:
                result.error_message = "choices数组为空"
                return result
            
            choice = data["choices"][0]
            if "message" not in choice:
                result.error_message = "缺少message字段"
                return result
            
            message = choice["message"]
            if "role" not in message or "content" not in message:
                result.error_message = "消息结构不完整"
                return result
            
            if message["role"] != "assistant":
                result.error_message = f"角色错误: {message['role']}"
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_chat_completions_streaming(self) -> APITestResult:
        """测试流式聊天完成"""
        result = APITestResult("POST /v1/chat/completions (流式)")
        
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "数数：1, 2, 3"}
                ],
                "stream": True
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                stream=True,
                timeout=30
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code != 200:
                result.error_message = f"状态码错误: {response.status_code}"
                return result
            
            # 验证Content-Type
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type:
                result.error_message = f"Content-Type错误: {content_type}"
                return result
            
            # 解析SSE流
            chunks = []
            chunk_count = 0
            has_done = False
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        if data_str.strip() == '[DONE]':
                            has_done = True
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            chunk_count += 1
                        except json.JSONDecodeError:
                            continue
            
            if chunk_count == 0:
                result.error_message = "未收到任何数据块"
                return result
            
            # 验证数据块格式
            if chunks:
                first_chunk = chunks[0]
                required_fields = ["id", "object", "created", "choices"]
                missing_fields = [f for f in required_fields if f not in first_chunk]
                
                if missing_fields:
                    result.error_message = f"数据块缺少字段: {missing_fields}"
                    return result
                
                if first_chunk.get("object") != "chat.completion.chunk":
                    result.error_message = f"数据块类型错误: {first_chunk.get('object')}"
                    return result
            
            result.passed = True
            result.response_data = {
                "chunks_received": chunk_count,
                "has_done_marker": has_done,
                "content_type": content_type
            }
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_chat_completions_with_code_execution(self) -> APITestResult:
        """测试需要代码执行的聊天完成"""
        result = APITestResult("POST /v1/chat/completions (代码执行)")
        
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "请用Python列出当前目录的文件"}
                ],
                "stream": False
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=60  # 代码执行需要更长时间
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code != 200:
                result.error_message = f"状态码错误: {response.status_code}"
                try:
                    error_data = response.json()
                    result.error_message += f" - {error_data}"
                except:
                    pass
                return result
            
            data = response.json()
            result.response_data = data
            
            # 验证基本响应格式
            required_fields = ["id", "object", "created", "model", "choices"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.error_message = f"响应缺少字段: {missing_fields}"
                return result
            
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content", "")
            
            # 检查是否有内容（即使是错误信息也算响应）
            if not content:
                result.error_message = "响应内容为空"
                return result
            
            # 检查是否包含代码执行相关的错误或结果
            if "is_openai_format" in content:
                # 这是一个已知的错误，但我们仍然认为API在工作
                result.error_message = f"检测到已知错误: {content[:100]}..."
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_cors_support(self) -> APITestResult:
        """测试CORS支持"""
        result = APITestResult("CORS支持测试")
        
        try:
            # 测试OPTIONS预检请求
            headers = {
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization"
            }
            
            start_time = time.time()
            response = self.session.options(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                timeout=5
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            if response.status_code not in [200, 204]:
                result.error_message = f"OPTIONS请求失败: {response.status_code}"
                return result
            
            # 验证CORS头
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
            }
            
            result.response_data = cors_headers
            
            # 检查基本的CORS头
            if not cors_headers["Access-Control-Allow-Origin"]:
                result.error_message = "缺少Access-Control-Allow-Origin头"
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def test_error_handling(self) -> APITestResult:
        """测试错误处理"""
        result = APITestResult("错误处理测试")
        
        try:
            # 发送无效请求
            payload = {
                "messages": "invalid_format",  # 应该是数组
                "stream": False
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=10
            )
            result.response_time = time.time() - start_time
            result.status_code = response.status_code
            
            # 期望收到错误响应
            if response.status_code == 200:
                result.error_message = "应该返回错误但返回了200"
                return result
            
            # 验证错误响应格式
            try:
                error_data = response.json()
                result.response_data = error_data
                
                if "error" not in error_data:
                    result.error_message = "错误响应缺少error字段"
                    return result
                
                error_obj = error_data["error"]
                if "message" not in error_obj:
                    result.error_message = "错误对象缺少message字段"
                    return result
                
            except json.JSONDecodeError:
                result.error_message = "错误响应不是有效的JSON"
                return result
            
            result.passed = True
            return result
            
        except Exception as e:
            result.error_message = str(e)
            return result
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        self.print_header("OpenAI API 集成测试开始")
        print(f"测试服务器: {self.base_url}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 测试列表
        tests = [
            self.test_models_endpoint,
            self.test_engines_endpoint,
            self.test_chat_completions_non_streaming,
            self.test_chat_completions_streaming,
            self.test_chat_completions_with_code_execution,
            self.test_cors_support,
            self.test_error_handling
        ]
        
        # 运行测试
        for test_func in tests:
            try:
                result = test_func()
                self.results.append(result)
                self.print_test_result(result)
            except Exception as e:
                result = APITestResult(test_func.__name__)
                result.error_message = f"测试执行异常: {str(e)}"
                self.results.append(result)
                self.print_test_result(result)
        
        # 生成报告
        return self.generate_report()
    
    def generate_report(self) -> bool:
        """生成测试报告"""
        self.print_header("测试报告")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n总计: {total} 个测试")
        print(f"✓ 通过: {passed}")
        print(f"✗ 失败: {failed}")
        print(f"通过率: {pass_rate:.1f}%")
        
        if failed > 0:
            print("\n失败的测试:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.name}: {result.error_message}")
        
        # 保存详细报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "results": []
        }
        
        for result in self.results:
            report["results"].append({
                "name": result.name,
                "passed": result.passed,
                "error_message": result.error_message,
                "response_time": result.response_time,
                "status_code": result.status_code,
                "response_data": result.response_data
            })
        
        report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细报告已保存至: {report_file}")
        
        return passed == total

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenAI API 集成测试")
    parser.add_argument("--url", default="http://localhost:5002", help="服务器URL")
    parser.add_argument("--api-key", default="test-key", help="API密钥")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = OpenAIAPITester(base_url=args.url, api_key=args.api_key)
    
    # 运行测试
    success = tester.run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()