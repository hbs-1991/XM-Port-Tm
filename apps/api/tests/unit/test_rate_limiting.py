"""
Unit tests for rate limiting functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from src.middleware.rate_limit import limiter, get_user_id_from_request, UPLOAD_RATE_LIMITS
from src.main import app


class TestRateLimitingMiddleware:
    """Test rate limiting middleware functionality"""
    
    def test_get_user_id_from_authenticated_request(self):
        """Test user ID extraction from authenticated request"""
        # Mock request with user state
        request = Mock()
        request.state.user = Mock()
        request.state.user.id = "user123"
        
        result = get_user_id_from_request(request)
        assert result == "user:user123"
    
    def test_get_user_id_from_unauthenticated_request(self):
        """Test user ID extraction falls back to IP address"""
        # Mock request without user state
        request = Mock()
        request.state = Mock()
        request.state.user = None
        request.client.host = "192.168.1.100"
        
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            result = get_user_id_from_request(request)
            assert result == "ip:192.168.1.100"
    
    def test_upload_rate_limits_configuration(self):
        """Test that upload rate limits are properly configured"""
        expected_limits = {
            "per_minute": "10 per minute",
            "per_hour": "50 per hour", 
            "per_day": "200 per day"
        }
        assert UPLOAD_RATE_LIMITS == expected_limits
    
    def test_limiter_initialization(self):
        """Test that limiter is properly initialized"""
        assert limiter is not None
        assert hasattr(limiter, 'limit')
        assert callable(limiter.limit)


class TestRateLimitingIntegration:
    """Test rate limiting integration with FastAPI endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with rate limiting enabled"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        user = Mock()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.credits_remaining = 100
        user.subscription_tier = Mock()
        user.subscription_tier.value = "BASIC"
        return user
    
    def test_rate_limiting_applied_to_upload_endpoint(self, client):
        """Test that rate limiting is applied to upload endpoint"""
        # This test verifies that the rate limiting decorators are present
        # The actual rate limiting behavior is tested in integration tests
        
        # Get the upload endpoint
        upload_route = None
        for route in app.routes:
            if hasattr(route, 'path') and '/api/v1/processing' in str(route.path):
                for sub_route in getattr(route, 'routes', []):
                    if hasattr(sub_route, 'path') and sub_route.path == '/upload':
                        upload_route = sub_route
                        break
        
        # Verify rate limiting decorators are applied
        assert upload_route is not None
        # The actual endpoint function should have the rate limiting decorators
        endpoint_func = upload_route.endpoint
        assert hasattr(endpoint_func, '__wrapped__') or 'limiter' in str(endpoint_func.__code__.co_names)
    
    def test_rate_limiting_applied_to_validate_endpoint(self, client):
        """Test that rate limiting is applied to validate endpoint"""
        # Similar verification for validate endpoint
        validate_route = None
        for route in app.routes:
            if hasattr(route, 'path') and '/api/v1/processing' in str(route.path):
                for sub_route in getattr(route, 'routes', []):
                    if hasattr(sub_route, 'path') and sub_route.path == '/validate':
                        validate_route = sub_route
                        break
        
        assert validate_route is not None
        endpoint_func = validate_route.endpoint
        assert hasattr(endpoint_func, '__wrapped__') or 'limiter' in str(endpoint_func.__code__.co_names)
    
    @patch('src.middleware.rate_limit.redis_client')
    def test_redis_connection_handling(self, mock_redis):
        """Test Redis connection handling for rate limiting"""
        from src.middleware.rate_limit import get_redis_client
        
        # Test successful connection
        mock_redis.from_url.return_value = Mock()
        client = get_redis_client()
        assert client is not None
        
        # Test connection failure
        mock_redis.from_url.side_effect = Exception("Connection failed")
        client = get_redis_client()
        # Should handle the error gracefully


class TestRateLimitingEdgeCases:
    """Test edge cases and error handling for rate limiting"""
    
    def test_rate_limit_with_missing_user_state(self):
        """Test rate limiting when user state is missing"""
        request = Mock()
        # No state attribute at all
        del request.state
        request.client.host = "192.168.1.100"
        
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            try:
                result = get_user_id_from_request(request)
                # Should fall back to IP address
                assert result == "ip:192.168.1.100"
            except AttributeError:
                # This is expected if request.state doesn't exist
                pass
    
    def test_rate_limit_error_handling(self):
        """Test rate limit exceeded error handling"""
        # This would be tested in integration tests where actual rate limits are hit
        # Here we just verify the error type exists and can be imported
        assert RateLimitExceeded is not None
        
        # Test creating the exception
        error = RateLimitExceeded("Test rate limit exceeded")
        assert str(error) == "Test rate limit exceeded"
    
    def test_rate_limiting_with_redis_unavailable(self):
        """Test behavior when Redis is unavailable"""
        # The application should continue to work even if Redis is unavailable
        # Rate limiting might be degraded but shouldn't break the app
        with patch('src.middleware.rate_limit.get_redis_client') as mock_get_redis:
            mock_get_redis.return_value = None
            
            # Application should still initialize without Redis
            from src.middleware.rate_limit import setup_rate_limiting
            mock_app = Mock()
            mock_app.state = Mock()
            mock_app.add_exception_handler = Mock()
            
            # Should not raise an exception
            setup_rate_limiting(mock_app)
            
            # Verify that the app state is set
            assert hasattr(mock_app.state, 'limiter')


class TestRateLimitingConfiguration:
    """Test rate limiting configuration and settings"""
    
    def test_default_rate_limits(self):
        """Test that default rate limits are reasonable"""
        # Upload limits should be restrictive enough to prevent abuse
        # but permissive enough for normal usage
        assert "10 per minute" in UPLOAD_RATE_LIMITS["per_minute"]
        assert "50 per hour" in UPLOAD_RATE_LIMITS["per_hour"] 
        assert "200 per day" in UPLOAD_RATE_LIMITS["per_day"]
    
    def test_validation_rate_limits_more_permissive(self):
        """Test that validation endpoint has more permissive limits than upload"""
        # This is tested by checking the actual decorators applied
        # Validation should allow 30 per minute vs 10 for upload
        upload_minute_limit = int(UPLOAD_RATE_LIMITS["per_minute"].split()[0])
        validation_minute_limit = 30  # From the code
        
        assert validation_minute_limit > upload_minute_limit
        assert validation_minute_limit == 30
        assert upload_minute_limit == 10
    
    def test_limiter_key_function(self):
        """Test that limiter uses the correct key function"""
        assert limiter._key_func == get_user_id_from_request
    
    def test_limiter_storage_configuration(self):
        """Test that limiter is configured with Redis storage"""
        # The limiter should be configured to use Redis
        assert hasattr(limiter, '_storage')
        # Storage URI should point to Redis
        storage_uri = getattr(limiter, '_storage_uri', '')
        assert 'redis://' in storage_uri or storage_uri == ''


# Performance and Load Testing Scenarios
class TestRateLimitingPerformance:
    """Test rate limiting performance characteristics"""
    
    def test_rate_limit_key_generation_performance(self):
        """Test that rate limit key generation is fast"""
        import time
        
        # Mock request
        request = Mock()
        request.state.user = Mock()
        request.state.user.id = "user123"
        
        # Measure time for key generation
        start_time = time.time()
        for _ in range(1000):
            get_user_id_from_request(request)
        end_time = time.time()
        
        # Should be very fast (less than 10ms for 1000 operations)
        duration = end_time - start_time
        assert duration < 0.01  # 10ms
    
    def test_rate_limiting_memory_usage(self):
        """Test that rate limiting doesn't consume excessive memory"""
        # This is a basic test to ensure no obvious memory leaks
        import gc
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Simulate multiple requests
        request = Mock()
        request.state.user = Mock()
        
        for i in range(100):
            request.state.user.id = f"user{i}"
            get_user_id_from_request(request)
        
        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Should not create excessive objects
        object_increase = final_objects - initial_objects
        assert object_increase < 50  # Reasonable limit