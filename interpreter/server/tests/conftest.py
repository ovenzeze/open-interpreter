import pytest
import requests


@pytest.fixture
def api_url():
    """Base API URL"""
    return "http://localhost:5002"


@pytest.fixture
def headers():
    """Basic request headers"""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-api-key"
    }


@pytest.fixture
def client(api_url, headers):
    """Simple test client"""
    class TestClient:
        def __init__(self, base_url, default_headers):
            self.base_url = base_url
            self.headers = default_headers
        
        def get(self, path, **kwargs):
            headers = kwargs.pop("headers", {})
            all_headers = self.headers.copy()
            all_headers.update(headers)
            return requests.get(f"{self.base_url}{path}", headers=all_headers, **kwargs)
        
        def post(self, path, **kwargs):
            headers = kwargs.pop("headers", {})
            all_headers = self.headers.copy()
            all_headers.update(headers)
            return requests.post(f"{self.base_url}{path}", headers=all_headers, **kwargs)
        
        def delete(self, path, **kwargs):
            headers = kwargs.pop("headers", {})
            all_headers = self.headers.copy()
            all_headers.update(headers)
            return requests.delete(f"{self.base_url}{path}", headers=all_headers, **kwargs)
    
    return TestClient(api_url, headers) 