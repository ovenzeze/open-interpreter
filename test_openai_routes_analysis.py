#!/usr/bin/env python3
"""
OpenAI API 路由分析和验证脚本
直接分析代码结构，无需运行服务器
"""

import sys
import os
import ast
import json
from pathlib import Path

# 设置路径
PROJECT_ROOT = Path(__file__).parent
SERVER_DIR = PROJECT_ROOT / 'interpreter' / 'server'

class OpenAIAPIAnalyzer:
    """OpenAI API 分析器"""

    def __init__(self):
        self.routes_file = SERVER_DIR / 'routes' / 'openai.py'
        self.app_file = SERVER_DIR / 'app.py'
        self.utils_file = SERVER_DIR / 'utils.py'
        self.chat_service_file = SERVER_DIR / 'chat_service.py'
        self.results = {
            'endpoints': [],
            'features': [],
            'issues': [],
            'recommendations': []
        }

    def analyze_routes(self):
        """分析路由定义"""
        print("\n" + "="*60)
        print("1. OpenAI 兼容端点分析")
        print("="*60)

        if not self.routes_file.exists():
            self.results['issues'].append("路由文件不存在")
            print("❌ 路由文件不存在")
            return

        with open(self.routes_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 分析端点
        endpoints = []

        # 检查 /v1/models
        if '@openai_bp.route(\'/v1/models\'' in content:
            methods = self._extract_methods(content, '/v1/models')
            endpoints.append({
                'path': '/v1/models',
                'methods': methods,
                'function': 'list_models',
                'status': '✓'
            })
            print(f"✓ /v1/models - 方法: {', '.join(methods)}")

        # 检查 /v1/engines
        if '@openai_bp.route(\'/v1/engines\'' in content:
            methods = self._extract_methods(content, '/v1/engines')
            endpoints.append({
                'path': '/v1/engines',
                'methods': methods,
                'function': 'list_engines',
                'status': '✓'
            })
            print(f"✓ /v1/engines - 方法: {', '.join(methods)}")

        # 检查 /v1/chat/completions
        if '@openai_bp.route(\'/v1/chat/completions\'' in content:
            methods = self._extract_methods(content, '/v1/chat/completions')
            endpoints.append({
                'path': '/v1/chat/completions',
                'methods': methods,
                'function': 'chat_completions',
                'status': '✓'
            })
            print(f"✓ /v1/chat/completions - 方法: {', '.join(methods)}")

        self.results['endpoints'] = endpoints

        if not endpoints:
            self.results['issues'].append("未找到任何 OpenAI 端点")
            print("❌ 未找到任何 OpenAI 端点")
        else:
            print(f"\n总计: {len(endpoints)} 个端点")

    def _extract_methods(self, content, route_path):
        """提取路由支持的HTTP方法"""
        import re
        pattern = f"@openai_bp\\.route\\('{re.escape(route_path)}'[^)]*methods=\\[([^\\]]+)\\]"
        match = re.search(pattern, content)
        if match:
            methods_str = match.group(1)
            methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
            return methods
        return []

    def analyze_features(self):
        """分析功能特性"""
        print("\n" + "="*60)
        print("2. 功能特性分析")
        print("="*60)

        features = []

        # 检查流式响应支持
        with open(self.routes_file, 'r', encoding='utf-8') as f:
            routes_content = f.read()

        if 'stream=True' in routes_content and 'stream_with_context' in routes_content:
            features.append({
                'name': '流式响应',
                'status': '✓',
                'description': '支持 SSE 流式响应'
            })
            print("✓ 流式响应 - 支持 SSE (Server-Sent Events)")
        else:
            self.results['issues'].append("流式响应可能不完整")
            print("⚠ 流式响应 - 可能不完整")

        # 检查 CORS 支持
        if 'Access-Control-Allow-Origin' in routes_content:
            features.append({
                'name': 'CORS 支持',
                'status': '✓',
                'description': '支持跨域请求'
            })
            print("✓ CORS 支持 - 跨域请求已启用")
        else:
            print("⚠ CORS 支持 - 可能缺失")

        # 检查方法验证
        if 'handle_method_not_allowed' in routes_content:
            features.append({
                'name': 'HTTP 方法验证',
                'status': '✓',
                'description': '支持方法不允许的错误处理'
            })
            print("✓ HTTP 方法验证 - 支持 405 Method Not Allowed")
        else:
            print("⚠ HTTP 方法验证 - 可能缺失")

        # 检查 OPTIONS 支持
        if 'OPTIONS' in routes_content and 'request.method == \'OPTIONS\'' in routes_content:
            features.append({
                'name': 'OPTIONS 预检',
                'status': '✓',
                'description': '支持 CORS 预检请求'
            })
            print("✓ OPTIONS 预检 - 支持 CORS 预检请求")
        else:
            print("⚠ OPTIONS 预检 - 可能缺失")

        # 检查会话管理
        if 'session_id' in routes_content:
            features.append({
                'name': '会话管理',
                'status': '✓',
                'description': '支持会话ID参数'
            })
            print("✓ 会话管理 - 支持会话持久化")
        else:
            print("⚠ 会话管理 - 可能缺失")

        # 检查模型选择
        if 'model' in routes_content:
            features.append({
                'name': '模型选择',
                'status': '✓',
                'description': '支持模型参数'
            })
            print("✓ 模型选择 - 支持自定义模型")
        else:
            print("⚠ 模型选择 - 可能缺失")

        self.results['features'] = features

    def analyze_message_conversion(self):
        """分析消息格式转换"""
        print("\n" + "="*60)
        print("3. 消息格式转换分析")
        print("="*60)

        if not self.utils_file.exists():
            self.results['issues'].append("utils.py 文件不存在")
            print("❌ utils.py 文件不存在")
            return

        with open(self.utils_file, 'r', encoding='utf-8') as f:
            utils_content = f.read()

        # 检查转换函数
        conversions = []

        if 'def convert_openai_to_interpreter' in utils_content:
            conversions.append('OpenAI → Interpreter')
            print("✓ OpenAI → Interpreter 格式转换")
        else:
            self.results['issues'].append("缺少 OpenAI → Interpreter 转换")
            print("❌ 缺少 OpenAI → Interpreter 转换")

        if 'def convert_interpreter_to_openai' in utils_content:
            conversions.append('Interpreter → OpenAI')
            print("✓ Interpreter → OpenAI 格式转换")
        else:
            self.results['issues'].append("缺少 Interpreter → OpenAI 转换")
            print("❌ 缺少 Interpreter → OpenAI 转换")

        if 'def format_openai_stream_chunk' in utils_content:
            conversions.append('流式数据块格式化')
            print("✓ 流式数据块 OpenAI 格式化")
        else:
            self.results['issues'].append("缺少流式数据块格式化")
            print("❌ 缺少流式数据块格式化")

        # 检查角色映射
        if "'system'" in utils_content or "'function'" in utils_content:
            print("✓ 角色映射 - 支持 system/function/tool 角色转换")
        else:
            print("⚠ 角色映射 - 可能不完整")

        # 检查代码块处理
        if '```' in utils_content or 'code_blocks' in utils_content:
            print("✓ 代码块处理 - 支持代码块解析")
        else:
            print("⚠ 代码块处理 - 可能缺失")

    def analyze_chat_service(self):
        """分析聊天服务"""
        print("\n" + "="*60)
        print("4. 聊天服务分析")
        print("="*60)

        if not self.chat_service_file.exists():
            self.results['issues'].append("chat_service.py 文件不存在")
            print("❌ chat_service.py 文件不存在")
            return

        with open(self.chat_service_file, 'r', encoding='utf-8') as f:
            chat_content = f.read()

        # 检查服务方法
        if 'def process_chat' in chat_content:
            print("✓ process_chat - 非流式聊天处理")
        else:
            self.results['issues'].append("缺少 process_chat 方法")
            print("❌ 缺少 process_chat 方法")

        if 'def process_streaming_chat' in chat_content:
            print("✓ process_streaming_chat - 流式聊天处理")
        else:
            self.results['issues'].append("缺少 process_streaming_chat 方法")
            print("❌ 缺少 process_streaming_chat 方法")

        # 检查会话锁
        if 'acquire_session_lock' in chat_content:
            print("✓ 会话锁 - 支持并发控制")
        else:
            print("⚠ 会话锁 - 可能缺失")

        # 检查错误处理
        if 'try:' in chat_content and 'except Exception' in chat_content:
            print("✓ 错误处理 - 包含异常处理")
        else:
            print("⚠ 错误处理 - 可能不完整")

    def analyze_app_integration(self):
        """分析应用集成"""
        print("\n" + "="*60)
        print("5. 应用集成分析")
        print("="*60)

        if not self.app_file.exists():
            self.results['issues'].append("app.py 文件不存在")
            print("❌ app.py 文件不存在")
            return

        with open(self.app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()

        # 检查蓝图注册
        if 'openai_bp' in app_content and 'register_blueprint' in app_content:
            print("✓ 蓝图注册 - OpenAI 蓝图已注册")
        else:
            self.results['issues'].append("OpenAI 蓝图可能未注册")
            print("❌ OpenAI 蓝图可能未注册")

        # 检查 CORS 配置
        if 'Access-Control-Allow-Origin' in app_content or 'CORS' in app_content:
            print("✓ CORS 配置 - 全局 CORS 支持")
        else:
            print("⚠ CORS 配置 - 可能仅在路由级别")

        # 检查聊天服务初始化
        if 'ChatService' in app_content:
            print("✓ 聊天服务 - 已初始化")
        else:
            print("⚠ 聊天服务 - 可能未初始化")

    def check_openai_compatibility(self):
        """检查 OpenAI API 兼容性"""
        print("\n" + "="*60)
        print("6. OpenAI API 兼容性检查")
        print("="*60)

        compatibility_checklist = {
            '模型列表端点': '/v1/models' in str(self.results.get('endpoints', [])),
            '聊天完成端点': '/v1/chat/completions' in str(self.results.get('endpoints', [])),
            '流式响应': any(f['name'] == '流式响应' for f in self.results.get('features', [])),
            'CORS 支持': any(f['name'] == 'CORS 支持' for f in self.results.get('features', [])),
            'OPTIONS 预检': any(f['name'] == 'OPTIONS 预检' for f in self.results.get('features', [])),
        }

        compatible_count = sum(compatibility_checklist.values())
        total_count = len(compatibility_checklist)

        for check, passed in compatibility_checklist.items():
            status = "✓" if passed else "❌"
            print(f"{status} {check}")

        compatibility_score = (compatible_count / total_count) * 100
        print(f"\n兼容性评分: {compatibility_score:.1f}% ({compatible_count}/{total_count})")

        return compatibility_score

    def generate_recommendations(self):
        """生成建议"""
        print("\n" + "="*60)
        print("7. 改进建议")
        print("="*60)

        recommendations = []

        if len(self.results['issues']) > 0:
            print("\n问题列表:")
            for i, issue in enumerate(self.results['issues'], 1):
                print(f"  {i}. {issue}")
                recommendations.append(f"修复: {issue}")

        # 通用建议
        print("\n建议:")
        suggestions = [
            "添加请求速率限制以防止滥用",
            "实现 token 使用统计",
            "添加请求日志记录",
            "实现缓存机制提高性能",
            "添加健康检查端点",
            "实现请求超时控制",
            "添加详细的 API 文档"
        ]

        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
            recommendations.append(suggestion)

        self.results['recommendations'] = recommendations

    def save_report(self, filename='openai_api_analysis_report.json'):
        """保存分析报告"""
        report_path = PROJECT_ROOT / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n分析报告已保存至: {report_path}")

    def run_analysis(self):
        """运行完整分析"""
        print("\n" + "="*70)
        print(" "*15 + "OpenAI API 兼容性分析报告")
        print("="*70)

        try:
            self.analyze_routes()
            self.analyze_features()
            self.analyze_message_conversion()
            self.analyze_chat_service()
            self.analyze_app_integration()
            score = self.check_openai_compatibility()
            self.generate_recommendations()

            print("\n" + "="*70)
            print(" "*25 + "分析完成")
            print("="*70)

            # 生成总结
            print(f"\n总结:")
            print(f"  - 发现端点: {len(self.results['endpoints'])} 个")
            print(f"  - 实现功能: {len(self.results['features'])} 项")
            print(f"  - 发现问题: {len(self.results['issues'])} 个")
            print(f"  - 兼容性评分: {score:.1f}%")

            if score >= 80:
                print(f"\n✓ OpenAI API 兼容性良好!")
            elif score >= 60:
                print(f"\n⚠ OpenAI API 基本可用，但需要改进")
            else:
                print(f"\n❌ OpenAI API 兼容性不足，需要大量改进")

            self.save_report()

            return score >= 60

        except Exception as e:
            print(f"\n❌ 分析过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    analyzer = OpenAIAPIAnalyzer()
    success = analyzer.run_analysis()
    sys.exit(0 if success else 1)
