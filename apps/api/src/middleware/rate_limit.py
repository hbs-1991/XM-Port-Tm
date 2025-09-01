"""
Rate limiting middleware for file upload endpoints
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Redis connection for rate limiting storage
redis_client: Optional[redis.Redis] = None

def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for rate limiting storage"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed for rate limiting: {e}")
            redis_client = None
    return redis_client

def get_user_id_from_request(request: Request) -> str:
    """
    Extract user identifier for rate limiting
    Fallback to IP address if user is not authenticated
    """
    # Try to get authenticated user ID from request state
    if hasattr(request.state, 'user') and request.state.user:
        return f"user:{request.state.user.id}"
    
    # Fallback to IP address for non-authenticated requests
    return f"ip:{get_remote_address(request)}"

# Create limiter instance
limiter = Limiter(
    key_func=get_user_id_from_request,
    storage_uri="redis://localhost:6379",
    default_limits=["1000 per hour"]  # Default rate limit for all endpoints
)

# File upload specific rate limits
UPLOAD_RATE_LIMITS = {
    "per_minute": "10 per minute",  # Max 10 file uploads per minute per user
    "per_hour": "50 per hour",      # Max 50 file uploads per hour per user
    "per_day": "200 per day"        # Max 200 file uploads per day per user
}

def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI application"""
    try:
        # Add rate limiting middleware
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting middleware configured successfully")
    except Exception as e:
        logger.error(f"Failed to setup rate limiting: {e}")
        # Continue without rate limiting if Redis is unavailable
        pass