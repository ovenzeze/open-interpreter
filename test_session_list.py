from interpreter.server.session import SessionManager

# 创建SessionManager实例，设置更长的会话超时时间（30天）
manager = SessionManager(session_timeout=30*24*3600)

# 打印存储路径和超时设置
print(f'会话存储路径: {manager.storage_path}')
print(f'会话超时时间: {manager.session_timeout} 秒')

# 获取会话列表
results = manager.list_sessions(1, 20)

# 打印结果
print(f'找到会话数: {len(results["sessions"])}')
print(f'返回的字段: {results.keys()}')

# 打印前3个会话的信息
for i, s in enumerate(results['sessions'][:3]):
    print(f'{i+1}. 会话ID: {s.get("session_id", "无ID")}, 最后活跃: {s.get("last_active", "未知")}') 