"""Authentication service for user authentication and token management."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import HTTPException, status

from src.core.config import settings
from src.models.user import User
from src.repositories.user_repository import UserRepository


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self):
        self.user_repository = UserRepository()
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = 15
        self.refresh_token_expire_days = 7
        self.bcrypt_salt_rounds = 12
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with configured salt rounds.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self.bcrypt_salt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """
        Create a JWT access token with 15-minute expiry.
        
        Args:
            user_id: User's unique identifier
            email: User's email address
            role: User's role (USER, ADMIN, PROJECT_OWNER)
            
        Returns:
            JWT access token string
        """
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a JWT refresh token with 7-day expiry.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            JWT refresh token string
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32)  # Unique token ID for revocation
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def decode_token(self, token: str) -> dict:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string to decode
            
        Returns:
            Decoded token payload dictionary
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def validate_access_token(self, token: str) -> dict:
        """
        Validate an access token and return its payload.
        
        Args:
            token: JWT access token to validate
            
        Returns:
            Token payload if valid
            
        Raises:
            HTTPException: If token is invalid or not an access token
        """
        payload = self.decode_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    
    def validate_refresh_token(self, token: str) -> dict:
        """
        Validate a refresh token and return its payload.
        
        Args:
            token: JWT refresh token to validate
            
        Returns:
            Token payload if valid
            
        Raises:
            HTTPException: If token is invalid or not a refresh token
        """
        payload = self.decode_token(token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: User's plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.user_repository.get_by_email(email)
        
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def generate_token_pair(self, user: User) -> Tuple[str, str]:
        """
        Generate both access and refresh tokens for a user.
        
        Args:
            user: User object to generate tokens for
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        refresh_token = self.create_refresh_token(user_id=str(user.id))
        
        return access_token, refresh_token
    
    def create_password_reset_token(self, user_id: str) -> str:
        """
        Create a password reset token with 1-hour expiry.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            JWT password reset token string
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        payload = {
            "sub": user_id,
            "type": "password_reset",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32)  # Unique token ID for revocation
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def validate_password_reset_token(self, token: str) -> dict:
        """
        Validate a password reset token and return its payload.
        
        Args:
            token: JWT password reset token to validate
            
        Returns:
            Token payload if valid
            
        Raises:
            HTTPException: If token is invalid or not a password reset token
        """
        payload = self.decode_token(token)
        
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload