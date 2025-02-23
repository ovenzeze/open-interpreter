import pytest
from interpreter.server.session import SessionManager

def test_interpreter_instance_management():
    manager = SessionManager(max_active_instances=2)
    
    # 测试实例限制
    session1 = manager.create_session()
    interpreter1 = manager.get_interpreter(session1['session_id'])
    assert interpreter1 is not None
    
    session2 = manager.create_session()
    interpreter2 = manager.get_interpreter(session2['session_id'])
    assert interpreter2 is not None
    
    session3 = manager.create_session()
    interpreter3 = manager.get_interpreter(session3['session_id'])
    assert interpreter3 is not None
    
    # 验证最旧的实例被清理
    assert len(manager.interpreter_instances) <= 2
    
    # 验证实例状态
    status = manager.get_instances_status()
    assert status["active_instances"] <= status["max_instances"]

def test_instance_cleanup():
    manager = SessionManager(
        max_active_instances=2,
        session_timeout=1,  # 1秒超时，便于测试
        cleanup_interval=0.5
    )
    
    session = manager.create_session()
    session_id = session['session_id']
    
    interpreter = manager.get_interpreter(session_id)
    assert interpreter is not None
    
    import time
    time.sleep(2)  # 等待超时
    
    # 验证实例被清理
    assert session_id not in manager.interpreter_instances
    assert session_id not in manager.instance_last_used
