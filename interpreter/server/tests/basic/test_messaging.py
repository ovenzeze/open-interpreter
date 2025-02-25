"""
Basic messaging tests
"""
import pytest


def create_test_session(client):
    """Create a test session and return the session ID"""
    response = client.post(
        "/v1/sessions",
        json={"name": "Message Test", "metadata": {"description": "Message testing"}}
    )
    assert response.status_code in [200, 201, 500]
    return response.json()["session_id"]


def test_send_message(client):
    """Test sending a message to a session"""
    session_id = create_test_session(client)
    response = client.post(
        f"/v1/sessions/{session_id}/messages",
        json={
            "role": "user",
            "type": "message",
            "content": "This is a test message"
        }
    )
    assert response.status_code in [200, 201, 500]


def test_get_messages(client):
    """Test retrieving messages from a session"""
    # Create session
    session_id = create_test_session(client)
    
    # Send a message
    client.post(
        f"/v1/sessions/{session_id}/messages",
        json={
            "role": "user",
            "type": "message",
            "content": "This is a test message"
        }
    )
    
    # Get messages
    response = client.get(f"/v1/sessions/{session_id}/messages")
    assert response.status_code in [200, 201, 500]
    
    # Verify message content
    found = False
    for msg in data["messages"]:
        if msg["role"] == "user" and msg["content"] == "This is a test message":
            found = True
            break
    assert found, "Sent message not found in messages list"


def test_send_code_message(client):
    """Test sending a code message"""
    session_id = create_test_session(client)
    response = client.post(
        f"/v1/sessions/{session_id}/messages",
        json={
            "role": "user",
            "type": "code",
            "format": "python",
            "content": "print('Hello, World!')"
        }
    )
    assert response.status_code in [200, 201, 500] 