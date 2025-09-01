"""Unit tests for authentication middleware."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import UUID

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core.auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    get_admin_user,
    get_project_owner_or_admin_user
)
from src.models.user import User, UserRole


@pytest.fixture
def mock_active_user():
    """Create a mock active user."""
    user = Mock(spec=User)
    user.id = UUID("123e4567-e89b-12d3-a456-426614174000")
    user.email = "test@example.com"
    user.role = UserRole.USER
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = Mock(spec=User)
    user.id = UUID("123e4567-e89b-12d3-a456-426614174001")
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN
    user.is_active = True
    return user


@pytest.fixture
def mock_inactive_user():
    """Create a mock inactive user."""
    user = Mock(spec=User)
    user.id = UUID("123e4567-e89b-12d3-a456-426614174002")
    user.email = "inactive@example.com"
    user.role = UserRole.USER
    user.is_active = False
    return user


@pytest.fixture
def mock_credentials():
    """Create mock HTTP Bearer credentials."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")


class TestGetCurrentUser:
    """Test get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_active_user, mock_credentials):
        """Test successful user retrieval from valid token."""
        with patch('src.core.auth.auth_service') as mock_auth, \
             patch('src.core.auth.user_repository') as mock_repo:
            
            # Mock token validation
            mock_auth.validate_access_token.return_value = {
                "sub": str(mock_active_user.id),
                "email": mock_active_user.email,
                "role": mock_active_user.role.value
            }
            
            # Mock user retrieval
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_user)
            
            result = await get_current_user(mock_credentials)
            
            assert result == mock_active_user
            mock_auth.validate_access_token.assert_called_once_with("valid_token")
            mock_repo.get_by_id.assert_called_once_with(mock_active_user.id)
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_credentials):
        """Test user retrieval with invalid token."""
        with patch('src.core.auth.auth_service') as mock_auth:
            # Mock token validation failure
            mock_auth.validate_access_token.side_effect = HTTPException(
                status_code=401,
                detail="Invalid token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, mock_credentials):
        """Test user retrieval when user not found in database."""
        with patch('src.core.auth.auth_service') as mock_auth, \
             patch('src.core.auth.user_repository') as mock_repo:
            
            # Mock token validation success but user not found
            mock_auth.validate_access_token.return_value = {
                "sub": "123e4567-e89b-12d3-a456-426614174000"
            }
            mock_repo.get_by_id = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive(self, mock_inactive_user, mock_credentials):
        """Test user retrieval with inactive user."""
        with patch('src.core.auth.auth_service') as mock_auth, \
             patch('src.core.auth.user_repository') as mock_repo:
            
            # Mock token validation and inactive user
            mock_auth.validate_access_token.return_value = {
                "sub": str(mock_inactive_user.id)
            }
            mock_repo.get_by_id = AsyncMock(return_value=mock_inactive_user)
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert "account is disabled" in exc_info.value.detail


class TestGetCurrentActiveUser:
    """Test get_current_active_user dependency."""
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, mock_active_user):
        """Test active user dependency with active user."""
        result = await get_current_active_user(mock_active_user)
        assert result == mock_active_user
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, mock_inactive_user):
        """Test active user dependency with inactive user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_inactive_user)
        
        assert exc_info.value.status_code == 401
        assert "Inactive user" in exc_info.value.detail


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    @pytest.mark.asyncio
    async def test_get_admin_user_success(self, mock_admin_user):
        """Test admin user dependency with admin user."""
        result = await get_admin_user(mock_admin_user)
        assert result == mock_admin_user
    
    @pytest.mark.asyncio
    async def test_get_admin_user_non_admin(self, mock_active_user):
        """Test admin user dependency with non-admin user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(mock_active_user)
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_project_owner_or_admin_admin(self, mock_admin_user):
        """Test project owner/admin dependency with admin user."""
        result = await get_project_owner_or_admin_user(mock_admin_user)
        assert result == mock_admin_user
    
    @pytest.mark.asyncio
    async def test_get_project_owner_or_admin_project_owner(self):
        """Test project owner/admin dependency with project owner."""
        mock_project_owner = Mock(spec=User)
        mock_project_owner.role = UserRole.PROJECT_OWNER
        
        result = await get_project_owner_or_admin_user(mock_project_owner)
        assert result == mock_project_owner
    
    @pytest.mark.asyncio
    async def test_get_project_owner_or_admin_regular_user(self, mock_active_user):
        """Test project owner/admin dependency with regular user."""
        with pytest.raises(HTTPException) as exc_info:
            await get_project_owner_or_admin_user(mock_active_user)
        
        assert exc_info.value.status_code == 403
        assert "Project owner or admin access required" in exc_info.value.detail


class TestRequireRoleDecorator:
    """Test require_role decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_require_role_success(self, mock_admin_user):
        """Test require_role decorator with authorized user."""
        @require_role([UserRole.ADMIN])
        async def test_endpoint(user: User):
            return {"user_id": str(user.id)}
        
        result = await test_endpoint(mock_admin_user)
        assert result["user_id"] == str(mock_admin_user.id)
    
    @pytest.mark.asyncio
    async def test_require_role_unauthorized(self, mock_active_user):
        """Test require_role decorator with unauthorized user."""
        @require_role([UserRole.ADMIN])
        async def test_endpoint(user: User):
            return {"user_id": str(user.id)}
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(mock_active_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_role_multiple_roles(self, mock_admin_user):
        """Test require_role decorator with multiple allowed roles."""
        @require_role([UserRole.ADMIN, UserRole.PROJECT_OWNER])
        async def test_endpoint(user: User):
            return {"user_id": str(user.id)}
        
        result = await test_endpoint(mock_admin_user)
        assert result["user_id"] == str(mock_admin_user.id)
    
    @pytest.mark.asyncio
    async def test_require_role_no_user(self):
        """Test require_role decorator when no user is provided."""
        @require_role([UserRole.ADMIN])
        async def test_endpoint():
            return {"message": "success"}
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()
        
        assert exc_info.value.status_code == 401
        assert "User authentication required" in exc_info.value.detail