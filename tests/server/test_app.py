"""
Tests for Open Interpreter HTTP Server
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from interpreter.server.app import create_app


@pytest.fixture
def app():
    """Create application for testing"""
    mock_interpreter = MagicMock()
    mock_interpreter.llm.model = "test-model"
    mock_interpreter.llm.context_window = 10000
    mock_interpreter.llm.max_tokens = 4096
    app = create_app(mock_interpreter)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app: Flask):
    """Create test client"""
    return app.test_client()


def test_health_check(app, client):
    """Test health check endpoint"""
    with app.app_context():
        response = client.get('/v1/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'llm' in data
        assert data['llm']['model'] == 'test-model'
        assert data['llm']['status'] == 'ready'


def test_chat_endpoint(app, client):
    """Test basic chat endpoint functionality"""
    request_data = {
        'messages': [{'role': 'user', 'type': 'message', 'content': 'Hello'}],
        'stream': False
    }
    
    mock_response = [{'role': 'assistant', 'type': 'message', 'content': 'Hi there!'}]
    app.interpreter_instance.chat.return_value = mock_response
    
    response = client.post('/v1/chat',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'messages' in data
    assert len(data['messages']) == 1
    assert data['messages'][0]['content'] == 'Hi there!'


def test_chat_completions_endpoint(app, client):
    """Test basic chat completions endpoint functionality"""
    request_data = {
        'model': 'test-model',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'stream': False
    }
    
    mock_response = [{'role': 'assistant', 'type': 'message', 'content': 'Hi there!'}]
    app.interpreter_instance.chat.return_value = mock_response
    
    response = client.post('/v1/chat/completions',
                         data=json.dumps(request_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'choices' in data
    assert len(data['choices']) == 1
    assert data['choices'][0]['message']['role'] == 'assistant'
    assert data['choices'][0]['message']['content'] == 'Hi there!'


def test_invalid_request(app, client):
    """Test error handling for invalid requests"""
    # Test empty messages array
    response = client.post('/v1/chat',
                         data=json.dumps({'messages': []}),
                         content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Messages array is required'
    
    # Test missing messages field
    response = client.post('/v1/chat',
                         data=json.dumps({}),
                         content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Messages array is required'
    
    # Test invalid content type
    response = client.post('/v1/chat',
                         data=json.dumps({'messages': [{'role': 'user', 'content': 'test'}]}),
                         content_type='text/plain')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Content-Type must be application/json' 