"""
Integration tests for Analytics API endpoints

These tests verify the analytics API endpoints work correctly with authentication,
rate limiting, and proper error handling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from src.main import app
from src.services.analytics_service import MatchingMetrics, UsageAnalytics, PerformanceMetrics


class TestAnalyticsAPIIntegration:
    """Integration tests for analytics API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user"""
        user = MagicMock()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.is_active = True
        return user

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def mock_analytics_service(self):
        """Mock analytics service for testing"""
        service = AsyncMock()
        
        # Setup default return values
        service.get_matching_metrics.return_value = MatchingMetrics(
            total_matches=100,
            successful_matches=95,
            failed_matches=5,
            average_response_time_ms=1500.0,
            cache_hit_rate=0.75,
            confidence_distribution={"high": 60, "medium": 30, "low": 10},
            popular_hs_codes=[("12345678", 25), ("87654321", 15)],
            processing_time_percentiles={"p50": 1200.0, "p95": 2800.0, "p99": 3500.0}
        )
        
        service.get_usage_analytics.return_value = UsageAnalytics(
            total_users=50,
            active_users_today=10,
            active_users_week=25,
            total_processing_jobs=200,
            jobs_completed_today=15,
            average_products_per_job=5.5,
            top_users_by_volume=[("user1@example.com", 100), ("user2@example.com", 75)]
        )
        
        service.get_performance_metrics.return_value = PerformanceMetrics(
            average_processing_time_ms=1500.0,
            p50_processing_time_ms=1200.0,
            p95_processing_time_ms=2800.0,
            p99_processing_time_ms=3500.0,
            error_rate_percentage=5.0,
            timeout_rate_percentage=1.0,
            api_calls_per_minute=20.0
        )
        
        service.get_confidence_score_analysis.return_value = {
            "total_matches": 100,
            "average_confidence": 0.85,
            "minimum_confidence": 0.45,
            "maximum_confidence": 0.99,
            "manual_review_required": 10,
            "manual_review_percentage": 10.0,
            "confidence_distribution": {
                "0.9-1.0": 30,
                "0.8-0.9": 40,
                "0.7-0.8": 20,
                "0.6-0.7": 7,
                "0.5-0.6": 3
            }
        }
        
        service.get_system_health_metrics.return_value = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": [],
            "performance": {
                "average_response_time_ms": 1500.0,
                "error_rate_percentage": 5.0,
                "api_calls_per_minute": 20.0,
                "p95_response_time_ms": 2800.0
            },
            "cache": {
                "available": True,
                "statistics": {"hit_rate": 0.75, "total_hits": 150, "total_misses": 50}
            },
            "memory_usage": {
                "recent_matches_count": 100,
                "performance_samples_count": 200,
                "api_call_timestamps_count": 50
            }
        }
        
        return service

    def test_get_matching_metrics_success(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test successful matching metrics retrieval"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):  # Bypass rate limiting
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics?days=7&include_real_time=true",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    assert data["success"] is True
                    assert data["period_days"] == 7
                    assert "data" in data
                    assert data["data"]["total_matches"] == 100
                    assert data["data"]["successful_matches"] == 95
                    assert data["data"]["success_rate_percentage"] == 95.0
                    assert data["data"]["cache_hit_rate"] == 0.75

    def test_get_matching_metrics_invalid_days(self, client, auth_headers, mock_auth_user):
        """Test matching metrics with invalid days parameter"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                
                # Test days too high
                response = client.get(
                    "/api/v1/hs-codes/analytics/metrics?days=100",
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "between 1 and 90" in response.json()["detail"]
                
                # Test days too low
                response = client.get(
                    "/api/v1/hs-codes/analytics/metrics?days=0",
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_usage_analytics_success(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test successful usage analytics retrieval"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/usage?days=30",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    assert data["success"] is True
                    assert data["period_days"] == 30
                    assert "data" in data
                    assert data["data"]["total_users"] == 50
                    assert data["data"]["active_users_today"] == 10
                    assert len(data["data"]["top_users_by_volume"]) == 2

    def test_get_usage_analytics_invalid_days(self, client, auth_headers, mock_auth_user):
        """Test usage analytics with invalid days parameter"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                
                response = client.get(
                    "/api/v1/hs-codes/analytics/usage?days=400",
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "between 1 and 365" in response.json()["detail"]

    def test_get_performance_metrics_success(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test successful performance metrics retrieval"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/performance?minutes=60",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    assert data["success"] is True
                    assert data["period_minutes"] == 60
                    assert "data" in data
                    assert data["data"]["average_processing_time_ms"] == 1500.0
                    assert data["data"]["error_rate_percentage"] == 5.0
                    assert data["data"]["api_calls_per_minute"] == 20.0

    def test_get_performance_metrics_invalid_minutes(self, client, auth_headers, mock_auth_user):
        """Test performance metrics with invalid minutes parameter"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                
                response = client.get(
                    "/api/v1/hs-codes/analytics/performance?minutes=1500",
                    headers=auth_headers
                )
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "between 1 and 1440" in response.json()["detail"]

    def test_get_confidence_analysis_success(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test successful confidence score analysis retrieval"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/confidence?days=7",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    assert data["success"] is True
                    assert data["period_days"] == 7
                    assert "data" in data
                    assert data["data"]["total_matches"] == 100
                    assert data["data"]["average_confidence"] == 0.85
                    assert data["data"]["manual_review_percentage"] == 10.0
                    assert "confidence_distribution" in data["data"]

    def test_get_system_health_success(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test successful system health retrieval"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/system-health",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    assert data["success"] is True
                    assert "data" in data
                    assert data["data"]["status"] == "healthy"
                    assert "performance" in data["data"]
                    assert "cache" in data["data"]
                    assert "memory_usage" in data["data"]

    def test_analytics_endpoints_authentication_required(self, client):
        """Test that analytics endpoints require authentication"""
        endpoints = [
            "/api/v1/hs-codes/analytics/metrics",
            "/api/v1/hs-codes/analytics/usage",
            "/api/v1/hs-codes/analytics/performance",
            "/api/v1/hs-codes/analytics/confidence",
            "/api/v1/hs-codes/analytics/system-health"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should get authentication error (401 or 403)
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_analytics_service_error_handling(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test analytics API error handling when service fails"""
        # Setup service to raise exception
        mock_analytics_service.get_matching_metrics.side_effect = Exception("Service error")
        
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK  # Error handled gracefully
                    data = response.json()
                    
                    assert data["success"] is False
                    assert "error" in data
                    assert data["error"] == "Service error"

    def test_analytics_metrics_default_parameters(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test analytics endpoints with default parameters"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    # Test metrics with default days (7)
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["period_days"] == 7  # Default value
                    
                    # Test usage with default days (30)
                    response = client.get(
                        "/api/v1/hs-codes/analytics/usage",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["period_days"] == 30  # Default value
                    
                    # Test performance with default minutes (60)
                    response = client.get(
                        "/api/v1/hs-codes/analytics/performance",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["period_minutes"] == 60  # Default value

    @pytest.mark.asyncio
    async def test_analytics_service_call_parameters(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test that correct parameters are passed to analytics service"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    # Test metrics endpoint
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics?days=14&include_real_time=false",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    
                    # Verify service was called with correct parameters
                    mock_analytics_service.get_matching_metrics.assert_called_once_with(14, False)

    def test_response_schema_validation(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test that API responses match expected schema"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    # Test metrics response schema
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    # Verify required fields
                    required_fields = ["success", "period_days", "timestamp"]
                    for field in required_fields:
                        assert field in data
                    
                    if data["success"]:
                        assert "data" in data
                        metrics_data = data["data"]
                        
                        # Verify metrics data structure
                        metrics_fields = [
                            "total_matches", "successful_matches", "failed_matches",
                            "success_rate_percentage", "average_response_time_ms",
                            "cache_hit_rate", "confidence_distribution",
                            "popular_hs_codes", "processing_time_percentiles"
                        ]
                        
                        for field in metrics_fields:
                            assert field in metrics_data

    def test_concurrent_analytics_requests(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test handling of concurrent analytics requests"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    # Make multiple concurrent requests
                    responses = []
                    for i in range(5):
                        response = client.get(
                            f"/api/v1/hs-codes/analytics/metrics?days={i+1}",
                            headers=auth_headers
                        )
                        responses.append(response)
                    
                    # Verify all requests succeeded
                    for i, response in enumerate(responses):
                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["period_days"] == i + 1

    def test_analytics_timestamps(self, client, auth_headers, mock_auth_user, mock_analytics_service):
        """Test that analytics responses include proper timestamps"""
        with patch('src.api.v1.hs_matching.get_current_active_user', return_value=mock_auth_user):
            with patch('src.api.v1.hs_matching.analytics_service', mock_analytics_service):
                with patch('src.api.v1.hs_matching.limiter.limit', lambda x: lambda f: f):
                    
                    response = client.get(
                        "/api/v1/hs-codes/analytics/metrics",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    
                    # Verify timestamp format
                    timestamp = data["timestamp"]
                    assert isinstance(timestamp, str)
                    
                    # Should be able to parse as ISO format
                    parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    assert isinstance(parsed_timestamp, datetime)
                    
                    # Should be recent (within last minute)
                    now = datetime.utcnow()
                    time_diff = abs((now - parsed_timestamp.replace(tzinfo=None)).total_seconds())
                    assert time_diff < 60  # Within 60 seconds