from interpreter.server.session import SessionManager
import json
import os

# 创建SessionManager实例
manager = SessionManager()

# 从命令行参数获取session_id或使用默认值
import sys
session_id = sys.argv[1] if len(sys.argv) > 1 else "test_session"

# 获取单个会话
session = manager.get_session(session_id)

if session:
    print(f"会话存在，ID: {session.get('session_id')}")
    print(f"会话创建时间: {session.get('created_at')}")
    print(f"会话最后活跃: {session.get('last_active')}")
    
    # 获取会话消息
    messages = manager.get_session_messages(session_id)
    print(f"消息数量: {len(messages)}")
    
    # 显示前3条消息
    for i, msg in enumerate(messages[:3]):
        print(f"{i+1}. 角色: {msg.get('role')}, 内容: {msg.get('content', '')[:50]}...")
else:
    print(f"会话 {session_id} 不存在") 