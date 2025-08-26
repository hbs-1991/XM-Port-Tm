"""Authentication schemas for request/response validation."""

from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, model_serializer
from uuid import UUID


class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    company_name: Optional[str] = Field(None, max_length=100, description="Company name")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character'
            )
        
        return v


class UserLoginRequest(BaseModel):
    """Schema for user login request."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="JWT refresh token")


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, one digit, and one special character'
            )
        
        return v


class UserResponse(BaseModel):
    """Schema for user data response."""
    id: Any = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: str = Field(..., description="User's last name")
    role: Any = Field(..., description="User's role")
    company_name: Optional[str] = Field(None, description="Company name")
    is_active: bool = Field(..., description="User's active status")
    
    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """Custom serialization to handle UUID and enum conversion."""
        return {
            'id': str(self.id) if hasattr(self.id, '__str__') else self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value if hasattr(self.role, 'value') else str(self.role),
            'company_name': self.company_name,
            'is_active': self.is_active
        }
    
    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Schema for authentication response."""
    user: UserResponse = Field(..., description="User information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    message: str = Field(default="Successfully logged out")


class PasswordResetResponse(BaseModel):
    """Schema for password reset response."""
    message: str = Field(..., description="Password reset status message")