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


def test_health_endpoint_llm_info(client):
    """Test health check endpoint includes LLM model information"""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    
    # 验证LLM信息存在
    assert "llm" in data
    assert isinstance(data["llm"], dict)
    assert "model" in data["llm"]
    assert "status" in data["llm"]
    
    # 验证实例信息存在
    assert "instances" in data
    assert isinstance(data["instances"], dict)
    if "max" in data["instances"] and "active" in data["instances"]:
        assert isinstance(data["instances"]["max"], int)
        assert isinstance(data["instances"]["active"], int) 