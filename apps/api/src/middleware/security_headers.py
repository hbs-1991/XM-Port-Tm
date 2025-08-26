"""
Security headers middleware to ensure all responses include required security headers
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next):
        # Process the request
        response = await call_next(request)
        
        # Add security headers to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add cache control based on endpoint
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            response.headers["Cache-Control"] = "public, max-age=300"
        
        # Ensure CORS headers are present (backup to CORS middleware)
        if "Access-Control-Allow-Origin" not in response.headers:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        if "Access-Control-Allow-Methods" not in response.headers:
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
        
        if "Access-Control-Allow-Headers" not in response.headers:
            response.headers["Access-Control-Allow-Headers"] = "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-Content-Type-Options, Cache-Control"
        
        # Handle preflight requests specifically
        if request.method == "OPTIONS":
            response.headers["Access-Control-Max-Age"] = "86400"
        
        logger.debug(f"Added security headers to {request.method} {request.url.path}")
        
        return response