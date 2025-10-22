#!/usr/bin/env python3
"""
OpenAI API 集成测试脚本
测试真实运行的服务器
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

class IntegrationTestRunner:
    """集成测试运行器"""

    def __init__(self, base_url: str = "http://localhost:5002", api_key: str = "test-integration-key-12345"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }
        self.start_time = None
        self.end_time = None

    def print_header(self, text: str):
        """打印测试标题"""
        print("\n" + "="*70)
        print(f" {text}")
        print("="*70)

    def print_test(self, name: str, passed: bool, message: str = ""):
        """打印测试结果"""
        status = "✓ PASS" if passed else "✗ FAIL"
        color_code = "\033[92m" if passed else "\033[91m"
        reset_code = "\033[0m"

        print(f"{color_code}{status}{reset_code} {name}")
        if message:
            print(f"      {message}")

    def wait_for_server(self, timeout: int = 30) -> bool:
        """等待服务器启动"""
        self.print_header("等待服务器启动")
        print(f"正在检查服务器 {self.base_url}...")

        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(f"{self.base_url}/api/health", timeout=2)
                if response.status_code == 200:
                    print(f"✓ 服务器已就绪 (耗时 {time.time() - start:.1f}s)")
                    return True
            except:
                pass
            time.sleep(1)
            print(".", end="", flush=True)

        print(f"\n✗ 服务器启动超时")
        return False

    def test_health_check(self) -> bool:
        """测试健康检查端点"""
        self.print_header("测试 1: 健康检查")

        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)

            if response.status_code != 200:
                self.print_test("健康检查", False, f"状态码: {response.status_code}")
                self.results["failed"].append({"test": "健康检查", "error": f"状态码 {response.status_code}"})
                return False

            data = response.json()

            # 验证响应结构
            if "status" not in data:
                self.print_test("健康检查", False, "缺少 'status' 字段")
                self.results["failed"].append({"test": "健康检查", "error": "缺少 status 字段"})
                return False

            self.print_test("健康检查", True, f"状态: {data.get('status')}")
            self.results["passed"].append({"test": "健康检查", "response": data})
            return True

        except Exception as e:
            self.print_test("健康检查", False, str(e))
            self.results["failed"].append({"test": "健康检查", "error": str(e)})
            return False

    def test_models_endpoint(self) -> bool:
        """测试 /v1/models 端点"""
        self.print_header("测试 2: Models 端点")

        try:
            # 测试 GET 请求
            response = requests.get(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                self.print_test("GET /v1/models", False, f"状态码: {response.status_code}")
                self.results["failed"].append({"test": "GET /v1/models", "error": f"状态码 {response.status_code}"})
                return False

            data = response.json()

            # 验证响应格式
            if data.get("object") != "list":
                self.print_test("模型列表格式", False, f"object 字段不是 'list': {data.get('object')}")
                self.results["failed"].append({"test": "模型列表格式", "error": "object 字段错误"})
                return False

            if "data" not in data or not isinstance(data["data"], list):
                self.print_test("模型列表数据", False, "缺少 data 数组")
                self.results["failed"].append({"test": "模型列表数据", "error": "缺少 data 数组"})
                return False

            if len(data["data"]) == 0:
                self.print_test("模型列表数据", False, "模型列表为空")
                self.results["failed"].append({"test": "模型列表数据", "error": "模型列表为空"})
                return False

            # 验证模型对象结构
            model = data["data"][0]
            required_fields = ["id", "object", "created", "owned_by"]
            missing_fields = [f for f in required_fields if f not in model]

            if missing_fields:
                self.print_test("模型对象结构", False, f"缺少字段: {missing_fields}")
                self.results["failed"].append({"test": "模型对象结构", "error": f"缺少字段: {missing_fields}"})
                return False

            self.print_test("GET /v1/models", True, f"找到 {len(data['data'])} 个模型")
            self.print_test("模型列表格式", True, "符合 OpenAI 标准")

            # 测试 OPTIONS 请求
            response = requests.options(
                f"{self.base_url}/v1/models",
                headers=self.headers,
                timeout=5
            )

            if response.status_code == 200:
                self.print_test("OPTIONS /v1/models", True, "CORS 预检支持")
            else:
                self.print_test("OPTIONS /v1/models", False, f"状态码: {response.status_code}")

            self.results["passed"].append({"test": "Models 端点", "models_count": len(data["data"])})
            return True

        except Exception as e:
            self.print_test("Models 端点", False, str(e))
            self.results["failed"].append({"test": "Models 端点", "error": str(e)})
            return False

    def test_chat_completions_non_streaming(self) -> bool:
        """测试非流式聊天完成"""
        self.print_header("测试 3: 非流式聊天完成")

        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
                ],
                "stream": False
            }

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                self.print_test("POST /v1/chat/completions", False, f"状态码: {response.status_code}")
                try:
                    error_data = response.json()
                    self.print_test("错误详情", False, json.dumps(error_data, indent=2))
                except:
                    pass
                self.results["failed"].append({"test": "非流式聊天", "error": f"状态码 {response.status_code}"})
                return False

            data = response.json()

            # 验证 OpenAI 标准响应格式
            required_fields = ["id", "object", "created", "model", "choices"]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                self.print_test("响应格式", False, f"缺少字段: {missing_fields}")
                self.results["failed"].append({"test": "响应格式", "error": f"缺少字段: {missing_fields}"})
                return False

            # 验证 choices
            if not data["choices"] or len(data["choices"]) == 0:
                self.print_test("响应 choices", False, "choices 数组为空")
                self.results["failed"].append({"test": "响应 choices", "error": "choices 数组为空"})
                return False

            choice = data["choices"][0]
            if "message" not in choice:
                self.print_test("响应消息", False, "缺少 message 字段")
                self.results["failed"].append({"test": "响应消息", "error": "缺少 message 字段"})
                return False

            message = choice["message"]
            if "role" not in message or "content" not in message:
                self.print_test("消息结构", False, "消息缺少 role 或 content")
                self.results["failed"].append({"test": "消息结构", "error": "消息结构不完整"})
                return False

            if message["role"] != "assistant":
                self.print_test("消息角色", False, f"角色不是 'assistant': {message['role']}")
                self.results["failed"].append({"test": "消息角色", "error": f"角色错误: {message['role']}"})
                return False

            self.print_test("POST /v1/chat/completions", True, "请求成功")
            self.print_test("响应格式", True, "符合 OpenAI 标准")
            self.print_test("响应内容", True, f"收到回复: {message['content'][:50]}...")

            self.results["passed"].append({
                "test": "非流式聊天",
                "response_length": len(message["content"]),
                "model": data.get("model")
            })
            return True

        except Exception as e:
            self.print_test("非流式聊天", False, str(e))
            self.results["failed"].append({"test": "非流式聊天", "error": str(e)})
            return False

    def test_chat_completions_streaming(self) -> bool:
        """测试流式聊天完成"""
        self.print_header("测试 4: 流式聊天完成")

        try:
            payload = {
                "messages": [
                    {"role": "user", "content": "Count from 1 to 3"}
                ],
                "stream": True
            }

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=60
            )

            if response.status_code != 200:
                self.print_test("流式请求", False, f"状态码: {response.status_code}")
                self.results["failed"].append({"test": "流式聊天", "error": f"状态码 {response.status_code}"})
                return False

            # 验证 Content-Type
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type:
                self.print_test("Content-Type", False, f"不是 SSE: {content_type}")
                self.results["failed"].append({"test": "流式 Content-Type", "error": f"错误的类型: {content_type}"})
                return False

            self.print_test("Content-Type", True, "text/event-stream")

            # 解析 SSE 流
            chunks = []
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀

                        if data_str.strip() == '[DONE]':
                            self.print_test("流式结束标记", True, "收到 [DONE]")
                            break

                        try:
                            chunk = json.loads(data_str)
                            chunks.append(chunk)
                            chunk_count += 1
                        except json.JSONDecodeError:
                            pass

            if chunk_count == 0:
                self.print_test("流式数据块", False, "未收到任何数据块")
                self.results["failed"].append({"test": "流式数据块", "error": "未收到数据块"})
                return False

            self.print_test("流式数据块", True, f"收到 {chunk_count} 个数据块")

            # 验证数据块格式
            if chunks:
                first_chunk = chunks[0]
                required_fields = ["id", "object", "created", "choices"]
                missing_fields = [f for f in required_fields if f not in first_chunk]

                if missing_fields:
                    self.print_test("数据块格式", False, f"缺少字段: {missing_fields}")
                else:
                    self.print_test("数据块格式", True, "符合 OpenAI 标准")

                    if first_chunk.get("object") == "chat.completion.chunk":
                        self.print_test("数据块类型", True, "chat.completion.chunk")
                    else:
                        self.print_test("数据块类型", False, f"类型错误: {first_chunk.get('object')}")

            self.results["passed"].append({
                "test": "流式聊天",
                "chunks_received": chunk_count
            })
            return True

        except Exception as e:
            self.print_test("流式聊天", False, str(e))
            self.results["failed"].append({"test": "流式聊天", "error": str(e)})
            return False

    def test_session_management(self) -> bool:
        """测试会话管理"""
        self.print_header("测试 5: 会话管理")

        try:
            # 创建会话
            response = requests.post(
                f"{self.base_url}/api/sessions",
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 201:
                self.print_test("创建会话", False, f"状态码: {response.status_code}")
                self.results["failed"].append({"test": "会话管理", "error": f"创建会话失败"})
                return False

            session_data = response.json()

            if "session" not in session_data:
                self.print_test("会话响应", False, "缺少 session 字段")
                self.results["failed"].append({"test": "会话管理", "error": "响应格式错误"})
                return False

            session_id = session_data["session"]["session_id"]
            self.print_test("创建会话", True, f"会话 ID: {session_id[:20]}...")

            # 使用会话发送消息
            payload = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "session_id": session_id,
                "stream": False
            }

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                self.print_test("使用会话聊天", True, "会话消息发送成功")
            else:
                self.print_test("使用会话聊天", False, f"状态码: {response.status_code}")

            # 获取会话信息
            response = requests.get(
                f"{self.base_url}/api/sessions/{session_id}",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                session_info = response.json()
                self.print_test("获取会话信息", True, f"会话存在")

                if "messages" in session_info.get("session", {}):
                    msg_count = len(session_info["session"]["messages"])
                    self.print_test("会话消息历史", True, f"包含 {msg_count} 条消息")
            else:
                self.print_test("获取会话信息", False, f"状态码: {response.status_code}")

            self.results["passed"].append({
                "test": "会话管理",
                "session_id": session_id
            })
            return True

        except Exception as e:
            self.print_test("会话管理", False, str(e))
            self.results["failed"].append({"test": "会话管理", "error": str(e)})
            return False

    def test_cors_support(self) -> bool:
        """测试 CORS 支持"""
        self.print_header("测试 6: CORS 支持")

        try:
            # 测试 OPTIONS 预检
            response = requests.options(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Origin": "http://example.com",
                    "Access-Control-Request-Method": "POST"
                },
                timeout=5
            )

            if response.status_code != 200:
                self.print_test("OPTIONS 预检", False, f"状态码: {response.status_code}")
                self.results["failed"].append({"test": "CORS", "error": "OPTIONS 请求失败"})
                return False

            # 验证 CORS 头
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers")
            }

            self.print_test("OPTIONS 预检", True, "请求成功")

            for header, value in cors_headers.items():
                if value:
                    self.print_test(f"CORS 头 - {header}", True, value)
                else:
                    self.print_test(f"CORS 头 - {header}", False, "缺失")

            self.results["passed"].append({
                "test": "CORS",
                "headers": cors_headers
            })
            return True

        except Exception as e:
            self.print_test("CORS 支持", False, str(e))
            self.results["failed"].append({"test": "CORS", "error": str(e)})
            return False

    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        self.print_header("测试报告")

        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["skipped"])
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        skipped = len(self.results["skipped"])

        pass_rate = (passed / total * 100) if total > 0 else 0

        duration = 0
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time

        print(f"\n总计: {total} 个测试")
        print(f"✓ 通过: {passed}")
        print(f"✗ 失败: {failed}")
        print(f"⊘ 跳过: {skipped}")
        print(f"通过率: {pass_rate:.1f}%")
        print(f"耗时: {duration:.2f}s")

        if failed > 0:
            print("\n失败的测试:")
            for result in self.results["failed"]:
                print(f"  - {result['test']}: {result.get('error', 'Unknown error')}")

        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": pass_rate,
            "duration": duration,
            "results": self.results
        }

        # 保存报告
        with open("integration_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n详细报告已保存至: integration_test_report.json")

        return report

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        self.start_time = time.time()

        print("\n" + "="*70)
        print(" "*15 + "OpenAI API 集成测试")
        print("="*70)
        print(f"测试服务器: {self.base_url}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 等待服务器就绪
        if not self.wait_for_server():
            print("\n✗ 服务器未就绪，测试中止")
            return False

        # 运行测试
        tests = [
            self.test_health_check,
            self.test_models_endpoint,
            self.test_chat_completions_non_streaming,
            self.test_chat_completions_streaming,
            self.test_session_management,
            self.test_cors_support
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n✗ 测试异常: {str(e)}")
                self.results["failed"].append({"test": test.__name__, "error": str(e)})

        self.end_time = time.time()

        # 生成报告
        report = self.generate_report()

        # 返回测试是否全部通过
        return len(self.results["failed"]) == 0


if __name__ == "__main__":
    # 从命令行参数获取配置
    import argparse

    parser = argparse.ArgumentParser(description="OpenAI API 集成测试")
    parser.add_argument("--url", default="http://localhost:5002", help="服务器 URL")
    parser.add_argument("--api-key", default="test-integration-key-12345", help="API Key")

    args = parser.parse_args()

    # 运行测试
    runner = IntegrationTestRunner(base_url=args.url, api_key=args.api_key)
    success = runner.run_all_tests()

    # 退出码
    sys.exit(0 if success else 1)
