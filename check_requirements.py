#!/usr/bin/env python3
"""
测试脚本依赖检查和可移植性验证
"""

import sys
import importlib
import subprocess
import platform

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print("❌ Python版本过低，需要3.6+")
        return False
    else:
        print("✅ Python版本符合要求")
        return True

def check_required_modules():
    """检查必需的模块"""
    required_modules = [
        ("json", "标准库"),
        ("requests", "第三方库"),
        ("datetime", "标准库"),
        ("time", "标准库"),
        ("argparse", "标准库")
    ]
    
    all_available = True
    
    for module, source in required_modules:
        try:
            if source == "标准库":
                importlib.import_module(module)
                print(f"✅ {module} ({source}) - 可用")
            else:
                importlib.import_module(module)
                print(f"✅ {module} ({source}) - 可用")
        except ImportError:
            print(f"❌ {module} ({source}) - 不可用")
            if source == "第三方库":
                print(f"   安装命令: pip install {module}")
            all_available = False
    
    return all_available

def check_network_connectivity(base_url="http://localhost:5002"):
    """检查网络连接"""
    try:
        import requests
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        if response.status_code == 200:
            print(f"✅ 网络连接正常 - {base_url}")
            return True
        else:
            print(f"⚠️  网络连接异常 - 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 网络连接失败 - {str(e)}")
        return False

def check_system_info():
    """显示系统信息"""
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python实现: {platform.python_implementation()}")

def main():
    """主检查函数"""
    print("="*50)
    print(" OpenAI API 测试脚本可移植性检查")
    print("="*50)
    
    check_system_info()
    print()
    
    # 检查Python版本
    python_ok = check_python_version()
    print()
    
    # 检查模块依赖
    modules_ok = check_required_modules()
    print()
    
    # 检查网络连接（可选）
    print("网络连接检查（可选）:")
    network_ok = check_network_connectivity()
    print()
    
    # 总结
    print("="*50)
    print(" 检查总结")
    print("="*50)
    
    if python_ok and modules_ok:
        print("✅ 测试脚本可以在此环境运行")
        if not network_ok:
            print("⚠️  注意: 目标服务器不可达，请确保服务器正在运行")
        return True
    else:
        print("❌ 测试脚本无法在此环境运行")
        print("\n解决方案:")
        if not python_ok:
            print("- 升级Python到3.6或更高版本")
        if not modules_ok:
            print("- 安装缺失的依赖: pip install requests")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)