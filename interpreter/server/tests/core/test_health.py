"""
Health check API tests
"""


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_endpoint_detailed(client):
    """Test detailed health check endpoint"""
    response = client.get("/v1/health?detail=full")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Detailed response may include system info
    if "system" in data:
        assert isinstance(data["system"], dict) 