"""Authentication middleware and dependencies."""

from functools import wraps
from typing import Callable, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.models.user import User, UserRole
from src.services.auth_service import AuthService
from src.repositories.user_repository import UserRepository

security = HTTPBearer()
auth_service = AuthService()
user_repository = UserRepository()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Validate access token
        payload = auth_service.validate_access_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # Get user from database
        user = await user_repository.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current active authenticated user.
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """
    Role-based access control decorator for FastAPI endpoints.
    
    Args:
        allowed_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        Decorator function that checks user role
        
    Example:
        @require_role([UserRole.ADMIN, UserRole.PROJECT_OWNER])
        async def admin_endpoint(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (should be injected by get_current_user dependency)
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break
            
            # Check in kwargs if not found in args
            if not user:
                for key, value in kwargs.items():
                    if isinstance(value, User):
                        user = value
                        break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication required"
                )
            
            # Check if user role is in allowed roles
            user_role = UserRole(user.role) if isinstance(user.role, str) else user.role
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {[role.value for role in allowed_roles]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require ADMIN role for endpoint access.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that requires ADMIN role
    """
    return require_role([UserRole.ADMIN])(func)


def require_project_owner_or_admin(func: Callable) -> Callable:
    """
    Decorator to require PROJECT_OWNER or ADMIN role for endpoint access.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that requires PROJECT_OWNER or ADMIN role
    """
    return require_role([UserRole.PROJECT_OWNER, UserRole.ADMIN])(func)


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current user with ADMIN role verification.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if they have ADMIN role
        
    Raises:
        HTTPException: If user doesn't have ADMIN role
    """
    if UserRole(current_user.role) != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_project_owner_or_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current user with PROJECT_OWNER or ADMIN role verification.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if they have PROJECT_OWNER or ADMIN role
        
    Raises:
        HTTPException: If user doesn't have required role
    """
    user_role = UserRole(current_user.role)
    if user_role not in [UserRole.PROJECT_OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project owner or admin access required"
        )
    return current_user


async def get_current_user_ws(token: str) -> User:
    """
    WebSocket-specific authentication function.
    
    Args:
        token: JWT token passed as query parameter or in initial message
        
    Returns:
        Authenticated user if token is valid
        
    Raises:
        Exception: If token is invalid or user not found
    """
    try:
        # Validate access token
        payload = auth_service.validate_access_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise Exception("Invalid token: missing user ID")
        
        # Get user from database
        user = await user_repository.get_by_id(UUID(user_id))
        if not user:
            raise Exception("User not found")
        
        if not user.is_active:
            raise Exception("User account is disabled")
        
        return user
        
    except Exception as e:
        raise Exception(f"WebSocket authentication failed: {str(e)}")