#!/usr/bin/env python3
"""
代码块格式化问题验证测试脚本

用于测试Open Interpreter LLM接口的代码格式化输出，特别是shell命令的分割问题。
使用方法：
1. 确保服务器已启动 (./server.sh start-dev)
2. 运行脚本 (python validation_test.py)
3. 检查输出结果是否有格式问题
"""

import requests
import json
import time
import os
import argparse

def test_command_formatting(command, server_url="http://localhost:5001", save_dir=None):
    """测试命令格式化输出
    
    Args:
        command: 要测试的命令
        server_url: 服务器地址
        save_dir: 保存结果的目录，如果为None则不保存
    
    Returns:
        命令执行结果
    """
    print(f"\n### 测试命令: {command}")

    try:
        # 发送命令到服务器
        response = requests.post(
            f"{server_url}/v1/chat/completions", 
            json={
                "messages": [{"role": "user", "content": f"执行并解释这个命令: {command}"}],
                "stream": True
            },
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        # 收集结果
        output = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        data = json.loads(line[6:])
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            output += content
                            print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        print(f"无法解析JSON: {line}")
                        continue

        # 保存输出到文件，便于分析
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            safe_command = command.replace('/', '_').replace('|', '_').replace('>', '_')[:30]
            filename = f"{save_dir}/test_{safe_command}_{int(time.time())}.txt"
            with open(filename, "w") as f:
                f.write(output)
                print(f"\n结果已保存到: {filename}")
        
        print("\n-------测试完成-------\n")
        return output
    
    except requests.exceptions.ConnectionError:
        print(f"Error: 无法连接到服务器 {server_url}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def basic_tests(save_dir=None):
    """基本测试套件"""
    basic_test_cases = [
        "ifconfig | grep inet6 | grep -v fe80::",
        "ls -la | grep '.py'",
        "for i in {1..5}; do echo $i; done",
        "find . -name '*.py' | xargs wc -l | sort -nr | head -n 5"
    ]
    
    for cmd in basic_test_cases:
        test_command_formatting(cmd, save_dir=save_dir)

def advanced_tests(save_dir=None):
    """复杂命令测试套件"""
    complex_commands = [
        # 长管道命令
        "ps aux | grep python | awk '{print $2}' | xargs echo",
        
        # 包含多种特殊字符的命令
        "echo \"Testing 'quotes' and \\\"escapes\\\" with $HOME and $(hostname)\"",
        
        # 多行脚本
        """cat << EOF > test_script.sh
#!/bin/bash
for i in {1..3}; do
  echo "Line $i"
done
EOF
cat test_script.sh
rm test_script.sh""",

        # 嵌套命令
        "find . -type f -name \"*.md\" -maxdepth 2 | grep -v 'node_modules' | head -3"
    ]
    
    for cmd in complex_commands:
        test_command_formatting(cmd, save_dir=save_dir)

def main():
    parser = argparse.ArgumentParser(description='代码块格式化问题验证测试')
    parser.add_argument('--url', type=str, default='http://localhost:5001', 
                        help='服务器地址 (默认: http://localhost:5001)')
    parser.add_argument('--save-dir', type=str, default=None,
                        help='结果保存目录 (默认: 不保存)')
    parser.add_argument('--mode', choices=['basic', 'advanced', 'all'], default='all',
                        help='测试模式: basic, advanced, 或 all (默认: all)')
    
    args = parser.parse_args()
    
    print("开始代码块格式化验证测试")
    print(f"服务器地址: {args.url}")
    if args.save_dir:
        print(f"结果将保存到: {args.save_dir}")
    
    if args.mode in ['basic', 'all']:
        print("\n## 运行基本测试...")
        basic_tests(args.save_dir)
    
    if args.mode in ['advanced', 'all']:
        print("\n## 运行高级测试...")
        advanced_tests(args.save_dir)
    
    print("\n所有测试已完成!")

if __name__ == "__main__":
    main() 