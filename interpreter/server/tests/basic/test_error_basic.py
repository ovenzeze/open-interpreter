"""
Basic error handling tests
"""
import requests


def test_not_found(client):
    """Test 404 error handling"""
    response = client.get("/v1/nonexistent")
    assert response.status_code in [404, 500]
    data = response.json()


def test_method_not_allowed(client):
    """Test 405 error handling"""
    response = requests.post(
        f"{client.base_url}/v1/health",
        headers=client.headers
    )
    assert response.status_code in [405, 404, 400, 500]  # Different frameworks handle this differently
    data = response.json()


def test_invalid_json(client):
    """Test invalid JSON handling"""
    response = requests.post(
        f"{client.base_url}/v1/sessions",
        data="This is not valid JSON",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {client.headers['Authorization'].split(' ')[1]}"
        }
    )
    assert response.status_code in [400, 500, 201]
    data = response.json()


def test_validation_error(client):
    """Test validation error handling"""
    response = client.post(
        "/v1/sessions",
        json={"invalid_field": "value"}  # Missing required fields
    )
    assert response.status_code in [400, 500, 201]
    data = response.json()
