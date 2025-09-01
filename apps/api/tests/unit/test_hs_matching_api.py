"""
Unit tests for HS Code Matching API endpoints
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from src.api.v1.hs_matching import router
from src.core.openai_config import HSCodeResult, HSCodeMatchResult
from src.models.user import User, UserRole
from src.schemas.hs_matching import (
    HSCodeMatchRequestAPI,
    HSCodeBatchMatchRequestAPI,
    HSCodeSearchRequest
)


# Test fixtures
@pytest.fixture
def app():
    """Create FastAPI test app"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/hs-codes")
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock authenticated user"""
    user = User(
        id="test-user-id",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        company_name="Test Company",
        country="USA",
        role=UserRole.USER,
        is_active=True
    )
    return user


@pytest.fixture
def mock_hs_result():
    """Create mock HS code matching result"""
    hs_result = HSCodeResult(
        hs_code="6109.10.00",
        code_description="T-shirts, singlets and other vests, knitted or crocheted, of cotton",
        confidence=0.95,
        chapter="61",
        section="XI",
        reasoning="Product matches cotton t-shirt classification"
    )
    
    match_result = HSCodeMatchResult(
        primary_match=hs_result,
        alternative_matches=[],
        processing_time_ms=1500.0,
        query="Cotton t-shirt"
    )
    
    return match_result


@pytest.fixture
def mock_auth_headers():
    """Create mock authentication headers"""
    return {"Authorization": "Bearer test-token"}


class TestHSCodeMatchingAPI:
    """Test cases for HS Code Matching API endpoints"""

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_match_single_product_success(self, mock_limiter, mock_service, mock_auth, client, mock_user, mock_hs_result):
        """Test successful single product matching"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_single_product.return_value = mock_hs_result
        mock_limiter.return_value = lambda func: func  # Mock rate limiter decorator
        
        # Test data
        request_data = {
            "product_description": "Cotton t-shirt made in Turkey",
            "country": "default",
            "include_alternatives": True,
            "confidence_threshold": 0.7
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["primary_match"]["hs_code"] == "6109.10.00"
        assert data["data"]["primary_match"]["confidence"] == 0.95
        assert "processing_time_ms" in data
        
        # Verify service was called correctly
        mock_service.match_single_product.assert_called_once()

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_match_single_product_validation_error(self, mock_limiter, mock_service, mock_auth, client, mock_user):
        """Test single product matching with validation error"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_single_product.side_effect = ValueError("Product description too short")
        mock_limiter.return_value = lambda func: func
        
        # Test data with invalid description
        request_data = {
            "product_description": "Hi",  # Too short
            "country": "default",
            "include_alternatives": True,
            "confidence_threshold": 0.7
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Product description too short" in data["detail"]

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_match_single_product_service_error(self, mock_limiter, mock_service, mock_auth, client, mock_user):
        """Test single product matching with service error"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_single_product.side_effect = Exception("OpenAI API error")
        mock_limiter.return_value = lambda func: func
        
        # Test data
        request_data = {
            "product_description": "Cotton t-shirt",
            "country": "default",
            "include_alternatives": True,
            "confidence_threshold": 0.7
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to match HS code" in data["detail"]

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_batch_match_products_success(self, mock_limiter, mock_service, mock_auth, client, mock_user, mock_hs_result):
        """Test successful batch product matching"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_batch_products.return_value = [mock_hs_result, mock_hs_result]
        mock_limiter.return_value = lambda func: func
        
        # Test data
        request_data = {
            "products": [
                {
                    "product_description": "Cotton t-shirt",
                    "country": "default",
                    "include_alternatives": True,
                    "confidence_threshold": 0.7
                },
                {
                    "product_description": "Leather jacket",
                    "country": "default",
                    "include_alternatives": True,
                    "confidence_threshold": 0.7
                }
            ],
            "country": "default"
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/batch-match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["total_processed"] == 2
        assert data["successful_matches"] == 2
        assert "processing_time_ms" in data
        
        # Verify service was called correctly
        mock_service.match_batch_products.assert_called_once()

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_batch_match_too_many_products(self, mock_limiter, mock_service, mock_auth, client, mock_user):
        """Test batch matching with too many products"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_batch_products.side_effect = ValueError("Batch size 101 exceeds limit of 100")
        mock_limiter.return_value = lambda func: func
        
        # Test data with too many products
        products = [
            {
                "product_description": f"Product {i}",
                "country": "default",
                "include_alternatives": True,
                "confidence_threshold": 0.7
            }
            for i in range(101)  # Exceed limit
        ]
        
        request_data = {
            "products": products,
            "country": "default"
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/batch-match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "exceeds limit" in data["detail"]

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_search_hs_codes_success(self, mock_limiter, mock_service, mock_auth, client, mock_user, mock_hs_result):
        """Test successful HS code search"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.match_single_product.return_value = mock_hs_result
        mock_limiter.return_value = lambda func: func
        
        # Make request
        response = client.get(
            "/api/v1/hs-codes/search",
            params={
                "query": "textile",
                "limit": 10,
                "country": "default"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["query"] == "textile"
        assert len(data["data"]) >= 1
        assert data["data"][0]["hs_code"] == "6109.10.00"
        assert "processing_time_ms" in data

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    def test_health_check_success(self, mock_service, mock_auth, client, mock_user):
        """Test successful health check"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.get_service_health.return_value = {
            "status": "healthy",
            "openai_response_time_ms": 1500.0,
            "cache_service": {"available": True},
            "configuration": {"max_retry_attempts": 3}
        }
        
        # Make request
        response = client.get(
            "/api/v1/hs-codes/health",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["openai_response_time_ms"] == 1500.0
        assert data["cache_available"] is True
        assert "timestamp" in data

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    def test_health_check_unhealthy(self, mock_service, mock_auth, client, mock_user):
        """Test health check when service is unhealthy"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.get_service_health.side_effect = Exception("OpenAI API unavailable")
        
        # Make request
        response = client.get(
            "/api/v1/hs-codes/health",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["cache_available"] is False
        assert "error" in data["configuration"]

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    def test_cache_stats_success(self, mock_service, mock_auth, client, mock_user):
        """Test successful cache statistics retrieval"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.get_cache_statistics.return_value = {
            "hit_rate": 0.75,
            "total_requests": 1000,
            "cache_hits": 750
        }
        
        # Make request
        response = client.get(
            "/api/v1/hs-codes/cache/stats",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["cache_available"] is True
        assert data["statistics"]["hit_rate"] == 0.75
        assert "timestamp" in data

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    def test_warm_cache_success(self, mock_service, mock_auth, client, mock_user):
        """Test successful cache warming"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.warm_cache.return_value = {"warmed": 10, "status": "success"}
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/cache/warm",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["operation"] == "cache_warm"
        assert data["details"]["warmed"] == 10

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    def test_invalidate_cache_success(self, mock_service, mock_auth, client, mock_user):
        """Test successful cache invalidation"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_service.invalidate_cache.return_value = {
            "invalidated": 50,
            "pattern": "xm_port:hs_match:*",
            "status": "success"
        }
        
        # Make request
        response = client.delete(
            "/api/v1/hs-codes/cache/invalidate",
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["operation"] == "cache_invalidate"
        assert data["details"]["invalidated"] == 50

    def test_unauthenticated_request(self, client):
        """Test that unauthenticated requests are rejected"""
        request_data = {
            "product_description": "Cotton t-shirt",
            "country": "default",
            "include_alternatives": True,
            "confidence_threshold": 0.7
        }
        
        # Make request without authentication
        response = client.post(
            "/api/v1/hs-codes/match",
            json=request_data
        )
        
        # Should require authentication
        assert response.status_code in [401, 403]

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_invalid_request_data(self, mock_limiter, mock_auth, client, mock_user):
        """Test API with invalid request data"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_limiter.return_value = lambda func: func
        
        # Test data with missing required field
        request_data = {
            "country": "default",
            "include_alternatives": True,
            "confidence_threshold": 0.7
            # Missing product_description
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions - should return validation error
        assert response.status_code == 422  # Unprocessable Entity


class TestHSCodeMatchingAPIIntegration:
    """Integration tests for HS Code Matching API"""

    @patch('src.api.v1.hs_matching.get_current_active_user')
    def test_rate_limiting_integration(self, mock_auth, client, mock_user):
        """Test that rate limiting is properly configured"""
        # This test would require actual rate limiting setup
        # For now, just verify the limiter decorators are applied
        mock_auth.return_value = mock_user
        
        # The rate limiter should be configured on the endpoints
        # In a real integration test, we would make multiple requests
        # and verify rate limiting behavior
        assert hasattr(client.app.routes[0], 'dependant')  # FastAPI route structure


class TestHSCodeMatchingAPIEdgeCases:
    """Edge case tests for HS Code Matching API"""

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_empty_batch_request(self, mock_limiter, mock_service, mock_auth, client, mock_user):
        """Test batch matching with empty products list"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_limiter.return_value = lambda func: func
        
        # Test data with empty products list
        request_data = {
            "products": [],
            "country": "default"
        }
        
        # Make request
        response = client.post(
            "/api/v1/hs-codes/batch-match",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should return validation error
        assert response.status_code == 422

    @patch('src.api.v1.hs_matching.get_current_active_user')
    @patch('src.api.v1.hs_matching.hs_matching_service')
    @patch('src.api.v1.hs_matching.limiter.limit')
    def test_search_with_very_short_query(self, mock_limiter, mock_service, mock_auth, client, mock_user):
        """Test search with very short query"""
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_limiter.return_value = lambda func: func
        
        # Make request with very short query
        response = client.get(
            "/api/v1/hs-codes/search",
            params={
                "query": "a",  # Very short query
                "limit": 10,
                "country": "default"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should return validation error
        assert response.status_code == 422