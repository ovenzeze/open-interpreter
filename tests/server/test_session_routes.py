import pytest
from interpreter.server.models import Session, MessageBase

def test_create_session(client):
    response = client.post('/v1/sessions', json={'name': 'Test Session'})
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    assert data['name'] == 'Test Session'

def test_session_messages(client):
    # Create session
    session_response = client.post('/v1/sessions', json={'name': 'Test'})
    session_id = session_response.get_json()['id']
    
    # Test message operations
    message = {'role': 'user', 'content': 'Hello'}
    response = client.post(f'/v1/sessions/{session_id}/messages', json=message)
    assert response.status_code == 200

def test_session_crud(client):
    """Test session CRUD operations"""
    # Create
    response = client.post('/v1/sessions', json={'title': 'Test Session'})
    assert response.status_code == 200
    session_id = response.json['session_id']
    
    # Read
    response = client.get(f'/v1/sessions/{session_id}')
    assert response.status_code == 200
    assert response.json['metadata']['title'] == 'Test Session'
    
    # Update
    response = client.patch(f'/v1/sessions/{session_id}', 
                          json={'metadata': {'description': 'Updated'}})
    assert response.status_code == 200
    
    # Delete
    response = client.delete(f'/v1/sessions/{session_id}')
    assert response.status_code == 200
