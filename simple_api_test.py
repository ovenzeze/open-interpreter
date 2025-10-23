#!/usr/bin/env python3
"""
简化的OpenAI API集成测试脚本
专注于核心功能验证，易于移植和维护
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_api_endpoint(base_url: str, endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """测试单个API端点"""
    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-key"
    }
    
    try:
        start_time = time.time()
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "OPTIONS":
            response = requests.options(url, headers=headers, timeout=5)
        else:
            return {"success": False, "error": f"不支持的方法: {method}"}
        
        response_time = time.time() - start_time
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response_time": response_time,
            "response_data": response.json() if response.content else None,
            "headers": dict(response.headers)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def print_test_result(test_name: str, result: dict):
    """打印测试结果"""
    if result["success"]:
        if 200 <= result["status_code"] < 300:
            status = "✓ PASS"
            color = "\033[92m"
        else:
            status = "✗ FAIL"
            color = "\033[91m"
    else:
        status = "✗ ERROR"
        color = "\033[91m"
    
    reset = "\033[0m"
    print(f"{color}{status}{reset} {test_name}")
    
    if result["success"]:
        print(f"      状态码: {result['status_code']}")
        print(f"      响应时间: {result['response_time']:.3f}s")
    else:
        print(f"      错误: {result['error']}")

def main():
    """主测试函数"""
    base_url = "http://localhost:5002"
    
    print("="*60)
    print(" OpenAI API 简化集成测试")
    print("="*60)
    print(f"测试服务器: {base_url}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试用例
    tests = [
        {
            "name": "模型列表",
            "endpoint": "/v1/models",
            "method": "GET"
        },
        {
            "name": "引擎列表", 
            "endpoint": "/v1/engines",
            "method": "GET"
        },
        {
            "name": "非流式聊天",
            "endpoint": "/v1/chat/completions",
            "method": "POST",
            "data": {
                "messages": [{"role": "user", "content": "你好"}],
                "stream": False
            }
        },
        {
            "name": "流式聊天",
            "endpoint": "/v1/chat/completions", 
            "method": "POST",
            "data": {
                "messages": [{"role": "user", "content": "数数: 1, 2, 3"}],
                "stream": True
            }
        },
        {
            "name": "CORS预检",
            "endpoint": "/v1/chat/completions",
            "method": "OPTIONS"
        }
    ]
    
    # 运行测试
    results = []
    for test in tests:
        result = test_api_endpoint(
            base_url=base_url,
            endpoint=test["endpoint"],
            method=test["method"],
            data=test.get("data")
        )
        result["name"] = test["name"]
        results.append(result)
        print_test_result(test["name"], result)
        print()
    
    # 生成总结
    passed = sum(1 for r in results if r["success"] and 200 <= r["status_code"] < 300)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print("="*60)
    print(" 测试总结")
    print("="*60)
    print(f"总计: {total} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {pass_rate:.1f}%")
    
    # 保存简单报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": base_url,
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": pass_rate,
        "tests": []
    }
    
    for result in results:
        report["tests"].append({
            "name": result["name"],
            "success": result["success"],
            "status_code": result.get("status_code"),
            "response_time": result.get("response_time"),
            "error": result.get("error")
        })
    
    with open("simple_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存至: simple_test_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)