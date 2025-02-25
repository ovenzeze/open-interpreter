"""
Basic authentication tests
"""
import requests
import pytest


@pytest.mark.skip(reason="Authentication is not currently required")
def test_auth_required(api_url):
    """Test that authentication is required"""
    response = requests.get(f"{api_url}/v1/health")
    assert response.status_code == 401


@pytest.mark.skip(reason="Authentication is not currently validated")
def test_invalid_auth(api_url):
    """Test invalid authentication"""
    headers = {"Authorization": "Bearer invalid-key"}
    response = requests.get(f"{api_url}/v1/health", headers=headers)
    assert response.status_code == 401


def test_valid_auth(client):
    """Test valid authentication"""
    response = client.get("/v1/health")
    assert response.status_code == 200 