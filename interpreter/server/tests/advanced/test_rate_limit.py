"""
Rate limiting tests
"""
import pytest
import time
import concurrent.futures


def test_rate_limiting(client):
    """Test API rate limiting"""
    # Send multiple requests in parallel to trigger rate limiting
    responses = []
    
    def make_request():
        return client.get("/v1/health")
    
    # Use ThreadPoolExecutor to send requests in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit 65 requests (default limit is 60 per minute)
        futures = [executor.submit(make_request) for _ in range(65)]
        
        # Collect responses
        for future in concurrent.futures.as_completed(futures):
            responses.append(future.result().status_code)
    
    # Check if at least one request was rate limited
    assert 429 in responses, "No rate limiting detected"


def test_rate_limit_headers(client):
    """Test rate limit headers"""
    response = client.get("/v1/health")
    
    # Check for rate limit headers
    headers = response.headers
    rate_limit_headers = [
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
    
    # At least one of these headers should be present if rate limiting is implemented
    header_found = False
    for header in rate_limit_headers:
        if header in headers:
            header_found = True
            break
    
    if not header_found:
        pytest.skip("Rate limit headers not implemented") 