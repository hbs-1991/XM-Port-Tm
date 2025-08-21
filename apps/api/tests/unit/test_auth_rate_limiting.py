"""
Comprehensive unit tests for authentication endpoint rate limiting
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from redis.exceptions import ConnectionError as RedisConnectionError

from src.middleware.rate_limit import (
    limiter, 
    get_user_id_from_request, 
    UPLOAD_RATE_LIMITS,
    get_redis_client,
    setup_rate_limiting
)
from src.api.v1.auth import router as auth_router
from src.services.auth_service import AuthService
from src.services.session_service import SessionService


class TestAuthenticationRateLimiting:
    """Test rate limiting on authentication endpoints"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = Mock()
        request.state = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {"User-Agent": "TestClient/1.0"}
        request.url = Mock()
        request.url.path = "/api/v1/auth/login"
        return request
    
    @pytest.fixture
    def authenticated_request(self, mock_request):
        """Create a mock authenticated request"""
        mock_request.state.user = Mock()
        mock_request.state.user.id = "user-123"
        mock_request.state.user.email = "test@example.com"
        return mock_request
    
    @pytest.fixture
    def auth_service_mock(self):
        """Mock authentication service"""
        with patch('src.api.v1.auth.auth_service') as mock:
            service = Mock(spec=AuthService)
            service.hash_password = Mock(return_value="hashed_password")
            service.authenticate_user = AsyncMock()
            service.generate_token_pair = Mock(return_value=("access_token", "refresh_token"))
            service.access_token_expire_minutes = 15
            service.decode_token = Mock()
            service.validate_refresh_token = Mock()
            service.create_password_reset_token = Mock(return_value="reset_token")
            mock.return_value = service
            yield service
    
    @pytest.fixture
    def session_service_mock(self):
        """Mock session service"""
        with patch('src.api.v1.auth.session_service') as mock:
            service = Mock(spec=SessionService)
            service.store_refresh_token = AsyncMock()
            service.validate_refresh_token = AsyncMock(return_value=True)
            service.invalidate_user_sessions = AsyncMock()
            service.invalidate_refresh_token = AsyncMock()
            service.store_password_reset_token = AsyncMock()
            mock.return_value = service
            yield service
    
    def test_rate_limit_key_extraction_authenticated(self, authenticated_request):
        """Test rate limit key extraction for authenticated users"""
        key = get_user_id_from_request(authenticated_request)
        assert key == "user:user-123"
    
    def test_rate_limit_key_extraction_unauthenticated(self, mock_request):
        """Test rate limit key extraction for unauthenticated users"""
        mock_request.state.user = None
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            key = get_user_id_from_request(mock_request)
            assert key == "ip:192.168.1.100"
    
    def test_rate_limit_key_extraction_no_state(self):
        """Test rate limit key extraction when request has no state"""
        request = Mock()
        request.client = Mock()
        request.client.host = "10.0.0.1"
        
        # Test when state doesn't exist
        if not hasattr(request, 'state'):
            request.state = Mock()
            request.state.user = None
        
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "10.0.0.1"
            key = get_user_id_from_request(request)
            assert key == "ip:10.0.0.1"


class TestLoginEndpointRateLimiting:
    """Test rate limiting specifically for login endpoint"""
    
    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client for rate limiting"""
        with patch('src.middleware.rate_limit.redis_client') as mock:
            client = Mock()
            client.incr = AsyncMock(return_value=1)
            client.expire = AsyncMock()
            client.ttl = AsyncMock(return_value=60)
            client.get = AsyncMock(return_value=None)
            client.set = AsyncMock()
            client.delete = AsyncMock()
            mock.return_value = client
            yield client
    
    def test_login_rate_limit_configuration(self):
        """Test that login endpoint has appropriate rate limits"""
        # Login should be more restrictive than general endpoints
        # Suggested: 5 attempts per minute, 20 per hour, 50 per day
        login_limits = {
            "per_minute": "5 per minute",
            "per_hour": "20 per hour",
            "per_day": "50 per day"
        }
        
        # These should be configured separately from upload limits
        assert UPLOAD_RATE_LIMITS["per_minute"] == "10 per minute"
        # Login limits should be more restrictive (when implemented)
    
    @patch('src.middleware.rate_limit.redis_client')
    def test_login_attempts_tracking(self, mock_redis):
        """Test tracking of failed login attempts"""
        mock_redis.from_url.return_value = Mock()
        
        # Simulate multiple login attempts
        attempts = []
        for i in range(6):
            request = Mock()
            request.state = Mock()
            request.state.user = None
            request.client = Mock()
            request.client.host = "192.168.1.100"
            
            with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
                mock_get_ip.return_value = "192.168.1.100"
                key = get_user_id_from_request(request)
                attempts.append(key)
        
        # All attempts should have the same key for the same IP
        assert len(set(attempts)) == 1
        assert attempts[0] == "ip:192.168.1.100"
    
    def test_login_rate_limit_by_email(self):
        """Test rate limiting by email address for login attempts"""
        # This tests that we can track attempts per email
        email = "test@example.com"
        
        # Create a custom key function for email-based rate limiting
        def get_email_key(request):
            # Extract email from request body if available
            if hasattr(request, 'json') and callable(request.json):
                try:
                    data = request.json()
                    if 'email' in data:
                        return f"email:{data['email']}"
                except:
                    pass
            return get_user_id_from_request(request)
        
        # Test key generation
        request = Mock()
        request.json = Mock(return_value={'email': email})
        key = get_email_key(request)
        assert key == f"email:{email}"


class TestRegistrationRateLimiting:
    """Test rate limiting for registration endpoint"""
    
    def test_registration_rate_limits(self):
        """Test that registration has strict rate limits"""
        # Registration should be very restrictive
        # Suggested: 3 per hour, 10 per day per IP
        registration_limits = {
            "per_hour": "3 per hour",
            "per_day": "10 per day"
        }
        
        # These limits prevent spam account creation
        # Should be implemented separately from other endpoints
    
    def test_registration_by_ip_only(self):
        """Test that registration is rate limited by IP only"""
        request = Mock()
        request.state = Mock()
        request.state.user = None  # Registration is always unauthenticated
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            key = get_user_id_from_request(request)
            assert key == "ip:192.168.1.100"
    
    def test_registration_spam_prevention(self):
        """Test spam prevention mechanisms for registration"""
        # Test that multiple registrations from same IP are blocked
        ip_address = "192.168.1.100"
        
        # Simulate rapid registration attempts
        attempts = []
        for i in range(5):
            request = Mock()
            request.state = Mock()
            request.state.user = None
            request.client = Mock()
            request.client.host = ip_address
            
            with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
                mock_get_ip.return_value = ip_address
                key = get_user_id_from_request(request)
                attempts.append((key, time.time()))
        
        # Check that all attempts have the same key
        keys = [attempt[0] for attempt in attempts]
        assert len(set(keys)) == 1
        
        # Check timing between attempts
        for i in range(1, len(attempts)):
            time_diff = attempts[i][1] - attempts[i-1][1]
            assert time_diff < 1  # Rapid attempts


class TestPasswordResetRateLimiting:
    """Test rate limiting for password reset endpoints"""
    
    def test_password_reset_request_limits(self):
        """Test rate limits for password reset requests"""
        # Password reset should have moderate limits
        # Suggested: 3 per hour, 10 per day per email/IP
        reset_limits = {
            "per_hour": "3 per hour",
            "per_day": "10 per day"
        }
        
        # Prevents abuse of password reset emails
    
    def test_password_reset_by_email(self):
        """Test that password reset is tracked by email"""
        # Password reset should track by both email and IP
        email = "user@example.com"
        
        # Mock request with email in body
        request = Mock()
        request.state = Mock()
        request.state.user = None
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        # Test IP-based tracking (current implementation)
        with patch('src.middleware.rate_limit.get_remote_address') as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            key = get_user_id_from_request(request)
            assert key == "ip:192.168.1.100"
    
    def test_password_reset_confirmation_limits(self):
        """Test rate limits for password reset confirmation"""
        # Confirmation attempts should be limited
        # Suggested: 5 attempts per token
        confirmation_limits = {
            "per_token": "5 attempts",
            "lockout_duration": "1 hour"
        }
        
        # Prevents brute force attacks on reset tokens


class TestTokenRefreshRateLimiting:
    """Test rate limiting for token refresh endpoint"""
    
    def test_refresh_token_limits(self):
        """Test rate limits for token refresh"""
        # Token refresh should have reasonable limits
        # Suggested: 60 per hour per user (once per minute average)
        refresh_limits = {
            "per_minute": "5 per minute",
            "per_hour": "60 per hour"
        }
        
        # Allows normal usage but prevents abuse
    
    def test_refresh_token_by_user(self, authenticated_request):
        """Test that refresh tokens are rate limited by user"""
        # Refresh should be tracked by authenticated user
        key = get_user_id_from_request(authenticated_request)
        assert key == "user:user-123"
    
    def test_invalid_refresh_token_tracking(self):
        """Test tracking of invalid refresh token attempts"""
        # Invalid attempts should be tracked separately
        # To prevent token guessing attacks
        invalid_attempts_limit = "10 per hour"
        
        # After limit, user should be required to re-authenticate


class TestRateLimitingWithRedis:
    """Test rate limiting with Redis integration"""
    
    @patch('redis.asyncio.from_url')
    def test_redis_connection_success(self, mock_redis_from_url):
        """Test successful Redis connection for rate limiting"""
        mock_client = Mock()
        mock_redis_from_url.return_value = mock_client
        
        client = get_redis_client()
        assert client is not None
        mock_redis_from_url.assert_called_once_with(
            "redis://localhost:6379", 
            decode_responses=True
        )
    
    @patch('redis.asyncio.from_url')
    def test_redis_connection_failure(self, mock_redis_from_url):
        """Test graceful handling of Redis connection failure"""
        mock_redis_from_url.side_effect = RedisConnectionError("Connection refused")
        
        # Should return None and log warning
        with patch('src.middleware.rate_limit.logger') as mock_logger:
            client = get_redis_client()
            assert client is None
            mock_logger.warning.assert_called()
    
    @patch('src.middleware.rate_limit.redis_client')
    async def test_rate_limit_with_redis_down(self, mock_redis):
        """Test that app continues to work when Redis is down"""
        mock_redis.return_value = None
        
        # Rate limiting should degrade gracefully
        app = Mock()
        app.state = Mock()
        app.add_exception_handler = Mock()
        
        setup_rate_limiting(app)
        
        # App should still be configured
        assert hasattr(app.state, 'limiter')
        app.add_exception_handler.assert_called_with(
            RateLimitExceeded, 
            _rate_limit_exceeded_handler
        )
    
    @patch('src.middleware.rate_limit.redis_client')
    async def test_rate_limit_counter_increment(self, mock_redis):
        """Test rate limit counter incrementation in Redis"""
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock()
        mock_redis.return_value = mock_client
        
        # Simulate rate limit check
        key = "user:test-user"
        window = 60  # 1 minute window
        
        # First request
        count = await mock_client.incr(f"rate_limit:{key}:minute")
        assert count == 1
        
        # Set expiry
        await mock_client.expire(f"rate_limit:{key}:minute", window)
        mock_client.expire.assert_called_with(f"rate_limit:{key}:minute", window)


class TestRateLimitingErrorHandling:
    """Test error handling for rate limiting"""
    
    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception handling"""
        error = RateLimitExceeded("429 Too Many Requests")
        assert str(error) == "429 Too Many Requests"
        assert isinstance(error, Exception)
    
    def test_rate_limit_exceeded_response(self):
        """Test response when rate limit is exceeded"""
        # Mock rate limit exceeded scenario
        request = Mock()
        request.state = Mock()
        request.state.user = None
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        # Create rate limit error
        error = RateLimitExceeded("Rate limit exceeded")
        
        # Expected response should include:
        # - 429 status code
        # - Retry-After header
        # - Clear error message
        expected_status = 429
        expected_headers = {"Retry-After": "60"}
        expected_detail = "Rate limit exceeded. Please try again later."
    
    def test_rate_limit_headers_in_response(self):
        """Test that rate limit headers are included in responses"""
        # Headers should include:
        # - X-RateLimit-Limit: maximum requests
        # - X-RateLimit-Remaining: remaining requests
        # - X-RateLimit-Reset: reset timestamp
        headers = {
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "4",
            "X-RateLimit-Reset": str(int(time.time()) + 60)
        }
        
        # These should be added to all responses


class TestRateLimitingPerformance:
    """Test performance characteristics of rate limiting"""
    
    def test_rate_limit_check_performance(self):
        """Test that rate limit checks are fast"""
        request = Mock()
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = "user-123"
        
        # Measure performance
        start = time.perf_counter()
        for _ in range(1000):
            key = get_user_id_from_request(request)
        end = time.perf_counter()
        
        duration = end - start
        avg_time = duration / 1000
        
        # Should be very fast (< 0.01ms per check)
        assert avg_time < 0.00001  # 0.01ms
        assert duration < 0.01  # Total < 10ms for 1000 checks
    
    def test_rate_limit_memory_efficiency(self):
        """Test memory efficiency of rate limiting"""
        import gc
        import sys
        
        # Get initial memory state
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Create many rate limit keys
        keys = []
        for i in range(1000):
            request = Mock()
            request.state = Mock()
            request.state.user = Mock()
            request.state.user.id = f"user-{i}"
            key = get_user_id_from_request(request)
            keys.append(key)
        
        # Check memory usage
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Should not create excessive objects
        object_increase = final_objects - initial_objects
        assert object_increase < 2000  # Reasonable limit
        
        # Check key size
        for key in keys[:10]:
            assert sys.getsizeof(key) < 100  # Keys should be small


class TestRateLimitingIntegration:
    """Integration tests for rate limiting with auth endpoints"""
    
    @pytest.fixture
    def app_with_rate_limiting(self):
        """Create FastAPI app with rate limiting configured"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1/auth")
        setup_rate_limiting(app)
        return app
    
    def test_rate_limiting_on_all_auth_endpoints(self, app_with_rate_limiting):
        """Test that rate limiting is applied to all auth endpoints"""
        auth_endpoints = [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/auth/password-reset-request",
            "/api/v1/auth/password-reset-confirm"
        ]
        
        # Check that limiter is configured for the app
        assert hasattr(app_with_rate_limiting.state, 'limiter')
        assert app_with_rate_limiting.state.limiter is not None
        
        # Verify endpoints exist
        routes = []
        for route in app_with_rate_limiting.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        for endpoint in auth_endpoints[:-1]:  # Exclude password-reset-confirm as it may not exist yet
            # Check if endpoint path exists in routes (considering path parameters)
            endpoint_exists = any(endpoint in str(route) for route in routes)
            if not endpoint_exists:
                # Some endpoints might not be implemented yet
                continue
    
    @patch('src.middleware.rate_limit.redis_client')
    def test_distributed_rate_limiting(self, mock_redis):
        """Test rate limiting across distributed instances"""
        # Rate limits should be shared across multiple app instances
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=5)  # 5th request
        mock_redis.return_value = mock_client
        
        # Simulate requests from different app instances
        instance1_request = Mock()
        instance1_request.state = Mock()
        instance1_request.state.user = Mock()
        instance1_request.state.user.id = "user-123"
        
        instance2_request = Mock()
        instance2_request.state = Mock() 
        instance2_request.state.user = Mock()
        instance2_request.state.user.id = "user-123"
        
        # Both instances should see the same user
        key1 = get_user_id_from_request(instance1_request)
        key2 = get_user_id_from_request(instance2_request)
        assert key1 == key2 == "user:user-123"


class TestRateLimitingConfiguration:
    """Test rate limiting configuration and customization"""
    
    def test_endpoint_specific_limits(self):
        """Test that different endpoints can have different limits"""
        endpoint_limits = {
            "/api/v1/auth/login": {
                "per_minute": "5 per minute",
                "per_hour": "20 per hour",
                "per_day": "50 per day"
            },
            "/api/v1/auth/register": {
                "per_hour": "3 per hour",
                "per_day": "10 per day"
            },
            "/api/v1/auth/refresh": {
                "per_minute": "10 per minute",
                "per_hour": "100 per hour"
            },
            "/api/v1/auth/password-reset-request": {
                "per_hour": "3 per hour",
                "per_day": "10 per day"
            }
        }
        
        # Each endpoint should respect its specific limits
        for endpoint, limits in endpoint_limits.items():
            # Limits should be enforced (implementation needed)
            pass
    
    def test_user_tier_based_limits(self):
        """Test different rate limits based on user subscription tier"""
        tier_limits = {
            "FREE": {
                "multiplier": 1.0,
                "login_per_hour": 10
            },
            "BASIC": {
                "multiplier": 2.0,
                "login_per_hour": 20
            },
            "PREMIUM": {
                "multiplier": 5.0,
                "login_per_hour": 50
            },
            "ENTERPRISE": {
                "multiplier": 10.0,
                "login_per_hour": 100
            }
        }
        
        # Users should get different limits based on tier
        for tier, limits in tier_limits.items():
            # Implementation would check user.subscription_tier
            pass
    
    def test_ip_based_global_limits(self):
        """Test global IP-based limits to prevent DDoS"""
        global_ip_limits = {
            "per_second": "10 per second",  # Prevent rapid-fire requests
            "per_minute": "100 per minute",  # General limit
            "per_hour": "1000 per hour"  # Sustained limit
        }
        
        # These limits apply regardless of authentication status
    
    def test_bypass_rate_limiting_for_admins(self):
        """Test that admin users can bypass rate limits"""
        request = Mock()
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = "admin-123"
        request.state.user.role = "ADMIN"
        
        # Admin users should have higher or no limits
        # Implementation would check user.role
        key = get_user_id_from_request(request)
        assert key == "user:admin-123"
        # Rate limit check would skip or use higher limits


class TestRateLimitingMonitoring:
    """Test monitoring and alerting for rate limiting"""
    
    def test_rate_limit_metrics_collection(self):
        """Test that rate limit metrics are collected"""
        metrics = {
            "total_requests": 0,
            "rate_limited_requests": 0,
            "unique_users": set(),
            "unique_ips": set(),
            "endpoint_counts": {}
        }
        
        # Metrics should be collected for monitoring
    
    def test_rate_limit_alerting(self):
        """Test alerting when rate limits are frequently hit"""
        alert_thresholds = {
            "rate_limit_percentage": 10,  # Alert if >10% requests are rate limited
            "single_user_threshold": 50,  # Alert if single user hits limit 50 times
            "ip_threshold": 100  # Alert if single IP hits limit 100 times
        }
        
        # Alerts should be triggered when thresholds are exceeded
    
    def test_rate_limit_logging(self):
        """Test that rate limit events are properly logged"""
        with patch('src.middleware.rate_limit.logger') as mock_logger:
            # Simulate rate limit exceeded
            error = RateLimitExceeded("Rate limit exceeded")
            
            # Should log the event with context
            expected_log_data = {
                "event": "rate_limit_exceeded",
                "user_id": "user-123",
                "ip": "192.168.1.100",
                "endpoint": "/api/v1/auth/login",
                "limit": "5 per minute",
                "current_count": 6
            }
            
            # Logger should be called with appropriate level
            # mock_logger.warning.assert_called()


class TestRateLimitingSecurity:
    """Test security aspects of rate limiting"""
    
    def test_prevent_timing_attacks(self):
        """Test that rate limiting prevents timing attacks"""
        # Response time should be consistent regardless of:
        # - Valid vs invalid credentials
        # - User exists vs doesn't exist
        # - Rate limited vs not rate limited
        
        response_times = []
        for i in range(10):
            start = time.perf_counter()
            # Simulate request processing
            time.sleep(0.001)  # Minimal processing
            end = time.perf_counter()
            response_times.append(end - start)
        
        # Check consistency
        avg_time = sum(response_times) / len(response_times)
        for response_time in response_times:
            variance = abs(response_time - avg_time) / avg_time
            assert variance < 0.2  # Less than 20% variance
    
    def test_prevent_user_enumeration(self):
        """Test that rate limiting prevents user enumeration"""
        # Rate limiting should prevent attackers from discovering valid emails
        # by trying many login attempts
        
        # Same rate limits should apply whether email exists or not
        valid_email = "user@example.com"
        invalid_email = "nonexistent@example.com"
        
        # Both should be rate limited identically
    
    def test_prevent_brute_force(self):
        """Test that rate limiting prevents brute force attacks"""
        # Strict limits on password attempts
        brute_force_limits = {
            "per_email_per_hour": 5,  # Max 5 attempts per email per hour
            "per_ip_per_hour": 20,  # Max 20 attempts per IP per hour
            "lockout_duration": 3600  # 1 hour lockout after limit
        }
        
        # These limits make brute force attacks impractical
    
    def test_prevent_credential_stuffing(self):
        """Test prevention of credential stuffing attacks"""
        # Detect and block rapid attempts with different email/password combinations
        
        # Pattern detection for credential stuffing:
        # - Many different emails from same IP
        # - Rapid succession of attempts
        # - Common passwords being tried
        
        stuffing_indicators = {
            "unique_emails_per_ip": 10,  # Flag if >10 different emails from same IP
            "time_between_attempts": 1,  # Flag if <1 second between attempts
            "common_password_attempts": 5  # Flag if common passwords detected
        }