"""
Authentication API endpoints
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer
from sqlalchemy.exc import IntegrityError

from src.models.user import User, UserRole
from src.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    AuthResponse,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse,
    LogoutResponse,
    UserResponse
)
from src.services.auth_service import AuthService
from src.services.session_service import SessionService
from src.repositories.user_repository import UserRepository

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()
session_service = SessionService()
user_repository = UserRepository()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegisterRequest):
    """
    User registration endpoint with email/password validation.
    
    Args:
        user_data: User registration data
        
    Returns:
        User data and authentication tokens
        
    Raises:
        HTTPException: If email already exists or validation fails
    """
    try:
        # Check if user already exists
        existing_user = await user_repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and create user
        hashed_password = auth_service.hash_password(user_data.password)
        
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            company_name=user_data.company_name,
            country="USA",  # Default country, can be updated later
            role=UserRole.USER
        )
        
        # Save user to database
        created_user = await user_repository.create(new_user)
        
        # Generate tokens
        access_token, refresh_token = auth_service.generate_token_pair(created_user)
        
        # Store refresh token in Redis
        await session_service.store_refresh_token(str(created_user.id), refresh_token)
        
        return AuthResponse(
            user=UserResponse.from_orm(created_user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=auth_service.access_token_expire_minutes * 60
            )
        )
        
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLoginRequest):
    """
    User login endpoint with JWT token generation.
    
    Args:
        credentials: User login credentials
        
    Returns:
        User data and authentication tokens
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Authenticate user
    user = await auth_service.authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Generate tokens
    access_token, refresh_token = auth_service.generate_token_pair(user)
    
    # Store refresh token in Redis
    await session_service.store_refresh_token(str(user.id), refresh_token)
    
    # Update last login time
    await user_repository.update_last_login(user.id)
    
    return AuthResponse(
        user=UserResponse.from_orm(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60
        )
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(token: str = Depends(security)):
    """
    User logout endpoint that clears session and invalidates tokens.
    
    Args:
        token: Bearer token from Authorization header
        
    Returns:
        Logout confirmation message
    """
    try:
        # Decode token to get user ID
        payload = auth_service.decode_token(token.credentials)
        user_id = payload.get("sub")
        
        if user_id:
            # Invalidate all refresh tokens for the user
            await session_service.invalidate_user_sessions(user_id)
        
        return LogoutResponse()
        
    except Exception:
        # Even if token is invalid, return success for security
        return LogoutResponse()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Token refresh endpoint using refresh token.
    
    Args:
        refresh_data: Refresh token data
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    try:
        # Validate refresh token
        payload = auth_service.validate_refresh_token(refresh_data.refresh_token)
        user_id = payload.get("sub")
        
        # Check if refresh token exists in Redis
        is_valid = await session_service.validate_refresh_token(user_id, refresh_data.refresh_token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user from database
        user = await user_repository.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or disabled"
            )
        
        # Generate new token pair
        new_access_token, new_refresh_token = auth_service.generate_token_pair(user)
        
        # Invalidate old refresh token and store new one
        await session_service.invalidate_refresh_token(user_id, refresh_data.refresh_token)
        await session_service.store_refresh_token(user_id, new_refresh_token)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/password-reset-request", response_model=PasswordResetResponse)
async def password_reset_request(reset_request: PasswordResetRequest):
    """
    Initiate password reset flow with secure token generation.
    
    Args:
        reset_request: Password reset request data
        
    Returns:
        Password reset confirmation message
    """
    # Check if user exists
    user = await user_repository.get_by_email(reset_request.email)
    
    if user:
        # Generate password reset token (short-lived, 1 hour)
        reset_token = auth_service.create_password_reset_token(str(user.id))
        
        # Store reset token in Redis with 1-hour expiry
        await session_service.store_password_reset_token(str(user.id), reset_token)
        
        # In production, send email with reset token
        # For now, just return success
    
    # Always return success to prevent email enumeration
    return PasswordResetResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post("/password-reset-confirm", response_model=PasswordResetResponse)
async def password_reset_confirm(reset_data: PasswordResetConfirm):
    """
    Complete password reset with token validation.
    
    Args:
        reset_data: Password reset confirmation data
        
    Returns:
        Password reset confirmation message
        
    Raises:
        HTTPException: If reset token is invalid or expired
    """
    try:
        # Validate reset token
        payload = auth_service.validate_password_reset_token(reset_data.token)
        user_id = payload.get("sub")
        
        # Verify token exists in Redis
        is_valid = await session_service.validate_password_reset_token(user_id, reset_data.token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Get user and update password
        user = await user_repository.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        # Hash new password and update user
        new_hashed_password = auth_service.hash_password(reset_data.new_password)
        user.hashed_password = new_hashed_password
        await user_repository.update(user)
        
        # Invalidate reset token and all user sessions
        await session_service.invalidate_password_reset_token(user_id, reset_data.token)
        await session_service.invalidate_user_sessions(user_id)
        
        return PasswordResetResponse(
            message="Password has been successfully reset. Please log in with your new password."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )