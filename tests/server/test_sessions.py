import pytest
import json
from unittest.mock import patch

def test_create_session(client):
    """测试创建会话"""
    response = client.post('/v1/sessions', json={
        'title': 'Test Session',
        'metadata': {
            'description': 'Test description'
        }
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'session_id' in data
    assert data['metadata']['title'] == 'Test Session'
    
def test_list_sessions(client):
    """测试列出会话"""
    # 先创建几个会话
    sessions = []
    for i in range(3):
        response = client.post('/v1/sessions', json={
            'title': f'Session {i}'
        })
        sessions.append(response.get_json())
    
    # 获取会话列表
    response = client.get('/v1/sessions')
    assert response.status_code == 200
    data = response.get_json()
    assert 'sessions' in data
    assert isinstance(data['sessions'], list)
    assert len(data['sessions']) >= len(sessions)

def test_get_session(client):
    """测试获取单个会话"""
    # 创建会话
    create_response = client.post('/v1/sessions', json={
        'title': 'Test Session'
    })
    session_id = create_response.get_json()['session_id']
    
    # 获取会话
    response = client.get(f'/v1/sessions/{session_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['session_id'] == session_id
    assert data['metadata']['title'] == 'Test Session'

def test_update_session(client):
    """测试更新会话"""
    # 创建会话
    create_response = client.post('/v1/sessions', json={
        'title': 'Original Title'
    })
    session_id = create_response.get_json()['session_id']
    
    # 更新会话
    response = client.patch(f'/v1/sessions/{session_id}', json={
        'metadata': {
            'title': 'Updated Title',
            'description': 'New description'
        }
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['metadata']['title'] == 'Updated Title'
    
def test_session_messages(client):
    """测试会话消息管理"""
    # 创建会话
    create_response = client.post('/v1/sessions', json={
        'title': 'Message Test Session'
    })
    session_id = create_response.get_json()['session_id']
    
    # 添加消息
    message = {
        'role': 'user',
        'content': 'Hello, world!',
        'type': 'message'
    }
    response = client.post(f'/v1/sessions/{session_id}/messages', json=message)
    assert response.status_code == 200
    
    # 获取消息
    response = client.get(f'/v1/sessions/{session_id}/messages')
    assert response.status_code == 200
    data = response.get_json()
    assert 'messages' in data
    assert len(data['messages']) == 1
    assert data['messages'][0]['content'] == 'Hello, world!'
    
    # 清空消息
    response = client.delete(f'/v1/sessions/{session_id}/messages')
    assert response.status_code == 200
    
    # 验证消息已清空
    response = client.get(f'/v1/sessions/{session_id}/messages')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['messages']) == 0

def test_delete_session(client):
    """测试删除会话"""
    # 创建会话
    create_response = client.post('/v1/sessions', json={
        'title': 'To Be Deleted'
    })
    session_id = create_response.get_json()['session_id']
    
    # 删除会话
    response = client.delete(f'/v1/sessions/{session_id}')
    assert response.status_code == 200
    
    # 验证会话已删除
    response = client.get(f'/v1/sessions/{session_id}')
    assert response.status_code == 404

def test_session_not_found(client):
    """测试访问不存在的会话"""
    fake_id = "non-existent-id"
    response = client.get(f'/v1/sessions/{fake_id}')
    assert response.status_code == 404
