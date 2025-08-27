"""Session management service using Redis."""

import redis.asyncio as redis
from typing import Optional

from src.core.config import settings


class SessionService:
    """Service for managing user sessions in Redis."""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.refresh_token_prefix = "refresh_token:"
        self.password_reset_prefix = "password_reset:"
        self.refresh_token_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 7 days in seconds
        self.password_reset_ttl = 3600  # 1 hour in seconds
    
    async def store_refresh_token(self, user_id: str, refresh_token: str) -> None:
        """
        Store a refresh token in Redis with TTL.
        
        Args:
            user_id: User's unique identifier
            refresh_token: JWT refresh token to store
        """
        key = f"{self.refresh_token_prefix}{user_id}:{refresh_token}"
        await self.redis_client.setex(key, self.refresh_token_ttl, "valid")
    
    async def validate_refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """
        Validate a refresh token exists in Redis.
        
        Args:
            user_id: User's unique identifier
            refresh_token: JWT refresh token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        key = f"{self.refresh_token_prefix}{user_id}:{refresh_token}"
        value = await self.redis_client.get(key)
        return value is not None
    
    async def invalidate_refresh_token(self, user_id: str, refresh_token: str) -> None:
        """
        Invalidate a specific refresh token.
        
        Args:
            user_id: User's unique identifier
            refresh_token: JWT refresh token to invalidate
        """
        key = f"{self.refresh_token_prefix}{user_id}:{refresh_token}"
        await self.redis_client.delete(key)
    
    async def invalidate_user_sessions(self, user_id: str) -> None:
        """
        Invalidate all refresh tokens for a user.
        
        Args:
            user_id: User's unique identifier
        """
        pattern = f"{self.refresh_token_prefix}{user_id}:*"
        keys = []
        async for key in self.redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await self.redis_client.delete(*keys)
    
    async def store_password_reset_token(self, user_id: str, reset_token: str) -> None:
        """
        Store a password reset token in Redis with TTL.
        
        Args:
            user_id: User's unique identifier
            reset_token: JWT password reset token to store
        """
        key = f"{self.password_reset_prefix}{user_id}:{reset_token}"
        await self.redis_client.setex(key, self.password_reset_ttl, "valid")
    
    async def validate_password_reset_token(self, user_id: str, reset_token: str) -> bool:
        """
        Validate a password reset token exists in Redis.
        
        Args:
            user_id: User's unique identifier
            reset_token: JWT password reset token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        key = f"{self.password_reset_prefix}{user_id}:{reset_token}"
        value = await self.redis_client.get(key)
        return value is not None
    
    async def invalidate_password_reset_token(self, user_id: str, reset_token: str) -> None:
        """
        Invalidate a password reset token.
        
        Args:
            user_id: User's unique identifier
            reset_token: JWT password reset token to invalidate
        """
        key = f"{self.password_reset_prefix}{user_id}:{reset_token}"
        await self.redis_client.delete(key)
    
    async def cleanup_user_data(self, user_id: str) -> None:
        """
        Clean up all user-related data from Redis when user is deleted.
        
        Args:
            user_id: User's unique identifier
        """
        # Invalidate all refresh tokens
        await self.invalidate_user_sessions(user_id)
        
        # Invalidate all password reset tokens  
        reset_pattern = f"{self.password_reset_prefix}{user_id}:*"
        reset_keys = []
        async for key in self.redis_client.scan_iter(match=reset_pattern):
            reset_keys.append(key)
        
        if reset_keys:
            await self.redis_client.delete(*reset_keys)
    
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis_client.close()