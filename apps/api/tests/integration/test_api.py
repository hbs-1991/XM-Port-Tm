"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "xm-port-api"


@pytest.mark.integration
def test_root_endpoint(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "XM-Port API is running"
    assert data["version"] == "1.0.0"


@pytest.mark.integration
def test_auth_endpoints(client: TestClient):
    """Test authentication endpoints exist"""
    # Test login endpoint exists
    response = client.post("/api/v1/auth/login")
    # Should return 422 (validation error) since no data provided
    # but confirms endpoint exists
    assert response.status_code == 422 or response.status_code == 200
    
    # Test register endpoint exists
    response = client.post("/api/v1/auth/register") 
    assert response.status_code == 422 or response.status_code == 200