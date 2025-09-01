"""Integration tests for authentication API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
import jwt

from src.main import app
from src.services.auth_service import AuthService


@pytest.fixture
def auth_service():
    """Create auth service instance."""
    return AuthService()


@pytest_asyncio.fixture
async def test_client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def valid_user_data():
    """Valid user registration data."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Test Company"
    }


@pytest.fixture
def valid_login_data():
    """Valid login credentials."""
    return {
        "email": "test@example.com",
        "password": "SecurePass123!"
    }


class TestRegistrationEndpoint:
    """Test user registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, test_client, valid_user_data):
        """Test successful user registration."""
        with patch('src.api.v1.auth.user_repository') as mock_repo, \
             patch('src.api.v1.auth.session_service') as mock_session:
            
            # Mock user not exists
            mock_repo.get_by_email.return_value = None
            
            # Mock user creation
            mock_user = AsyncMock()
            mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_user.email = valid_user_data["email"]
            mock_user.first_name = valid_user_data["first_name"]
            mock_user.last_name = valid_user_data["last_name"]
            mock_user.role = "USER"
            mock_user.company_name = valid_user_data["company_name"]
            mock_user.is_active = True
            
            mock_repo.create.return_value = mock_user
            mock_session.store_refresh_token.return_value = None
            
            response = await test_client.post("/api/v1/auth/register", json=valid_user_data)
            
            assert response.status_code == 201
            data = response.json()
            assert "user" in data
            assert "tokens" in data
            assert data["user"]["email"] == valid_user_data["email"]
            assert "access_token" in data["tokens"]
            assert "refresh_token" in data["tokens"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client, valid_user_data):
        """Test registration with existing email."""
        with patch('src.api.v1.auth.user_repository') as mock_repo:
            # Mock user already exists
            mock_repo.get_by_email.return_value = AsyncMock()
            
            response = await test_client.post("/api/v1/auth/register", json=valid_user_data)
            
            assert response.status_code == 400
            assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, test_client, valid_user_data):
        """Test registration with invalid email."""
        invalid_data = valid_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = await test_client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, test_client, valid_user_data):
        """Test registration with weak password."""
        invalid_data = valid_user_data.copy()
        invalid_data["password"] = "weak"
        
        response = await test_client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422


class TestLoginEndpoint:
    """Test user login endpoint."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, test_client, valid_login_data):
        """Test successful user login."""
        with patch('src.api.v1.auth.auth_service') as mock_auth, \
             patch('src.api.v1.auth.session_service') as mock_session, \
             patch('src.api.v1.auth.user_repository') as mock_repo:
            
            # Mock successful authentication
            mock_user = AsyncMock()
            mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_user.email = valid_login_data["email"]
            mock_user.role = "USER"
            mock_user.is_active = True
            
            mock_auth.authenticate_user.return_value = mock_user
            mock_auth.generate_token_pair.return_value = ("access_token", "refresh_token")
            mock_session.store_refresh_token.return_value = None
            mock_repo.update_last_login.return_value = None
            
            response = await test_client.post("/api/v1/auth/login", json=valid_login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "user" in data
            assert "tokens" in data
            assert data["user"]["email"] == valid_login_data["email"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, test_client, valid_login_data):
        """Test login with invalid credentials."""
        with patch('src.api.v1.auth.auth_service') as mock_auth:
            # Mock failed authentication
            mock_auth.authenticate_user.return_value = None
            
            response = await test_client.post("/api/v1/auth/login", json=valid_login_data)
            
            assert response.status_code == 401
            assert "Invalid email or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, test_client, valid_login_data):
        """Test login with inactive user account."""
        with patch('src.api.v1.auth.auth_service') as mock_auth:
            # Mock inactive user
            mock_user = AsyncMock()
            mock_user.is_active = False
            mock_auth.authenticate_user.return_value = mock_user
            
            response = await test_client.post("/api/v1/auth/login", json=valid_login_data)
            
            assert response.status_code == 401
            assert "Account is disabled" in response.json()["detail"]


class TestLogoutEndpoint:
    """Test user logout endpoint."""
    
    @pytest.mark.asyncio
    async def test_logout_success(self, test_client, auth_service):
        """Test successful logout."""
        # Create a valid access token
        access_token = auth_service.create_access_token(
            "123e4567-e89b-12d3-a456-426614174000",
            "test@example.com",
            "USER"
        )
        
        with patch('src.api.v1.auth.session_service') as mock_session:
            mock_session.invalidate_user_sessions.return_value = None
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await test_client.post("/api/v1/auth/logout", headers=headers)
            
            assert response.status_code == 200
            assert "Successfully logged out" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, test_client):
        """Test logout with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await test_client.post("/api/v1/auth/logout", headers=headers)
        
        # Should still return success for security
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]


class TestRefreshTokenEndpoint:
    """Test token refresh endpoint."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, test_client, auth_service):
        """Test successful token refresh."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        refresh_token = auth_service.create_refresh_token(user_id)
        
        with patch('src.api.v1.auth.session_service') as mock_session, \
             patch('src.api.v1.auth.user_repository') as mock_repo, \
             patch('src.api.v1.auth.auth_service') as mock_auth:
            
            # Mock valid refresh token
            mock_session.validate_refresh_token.return_value = True
            mock_session.invalidate_refresh_token.return_value = None
            mock_session.store_refresh_token.return_value = None
            
            # Mock user retrieval
            mock_user = AsyncMock()
            mock_user.id = user_id
            mock_user.is_active = True
            mock_repo.get_by_id.return_value = mock_user
            
            # Mock token generation
            mock_auth.validate_refresh_token.return_value = {"sub": user_id, "type": "refresh"}
            mock_auth.generate_token_pair.return_value = ("new_access", "new_refresh")
            
            response = await test_client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, test_client):
        """Test refresh with invalid token."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        
        assert response.status_code == 401


class TestPasswordResetEndpoints:
    """Test password reset endpoints."""
    
    @pytest.mark.asyncio
    async def test_password_reset_request_existing_user(self, test_client):
        """Test password reset request for existing user."""
        with patch('src.api.v1.auth.user_repository') as mock_repo, \
             patch('src.api.v1.auth.session_service') as mock_session, \
             patch('src.api.v1.auth.auth_service') as mock_auth:
            
            # Mock user exists
            mock_repo.get_by_email.return_value = AsyncMock()
            mock_auth.create_password_reset_token.return_value = "reset_token"
            mock_session.store_password_reset_token.return_value = None
            
            response = await test_client.post(
                "/api/v1/auth/password-reset-request",
                json={"email": "test@example.com"}
            )
            
            assert response.status_code == 200
            assert "password reset link has been sent" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_request_nonexistent_user(self, test_client):
        """Test password reset request for non-existent user."""
        with patch('src.api.v1.auth.user_repository') as mock_repo:
            # Mock user doesn't exist
            mock_repo.get_by_email.return_value = None
            
            response = await test_client.post(
                "/api/v1/auth/password-reset-request",
                json={"email": "nonexistent@example.com"}
            )
            
            # Should still return success to prevent email enumeration
            assert response.status_code == 200
            assert "password reset link has been sent" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_confirm_success(self, test_client):
        """Test successful password reset confirmation."""
        with patch('src.api.v1.auth.auth_service') as mock_auth, \
             patch('src.api.v1.auth.session_service') as mock_session, \
             patch('src.api.v1.auth.user_repository') as mock_repo:
            
            user_id = "123e4567-e89b-12d3-a456-426614174000"
            
            # Mock valid reset token
            mock_auth.validate_password_reset_token.return_value = {"sub": user_id, "type": "password_reset"}
            mock_session.validate_password_reset_token.return_value = True
            
            # Mock user retrieval and update
            mock_user = AsyncMock()
            mock_user.id = user_id
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.update.return_value = mock_user
            
            # Mock cleanup
            mock_session.invalidate_password_reset_token.return_value = None
            mock_session.invalidate_user_sessions.return_value = None
            mock_auth.hash_password.return_value = "hashed_new_password"
            
            response = await test_client.post(
                "/api/v1/auth/password-reset-confirm",
                json={
                    "token": "valid_reset_token",
                    "new_password": "NewSecurePass123!"
                }
            )
            
            assert response.status_code == 200
            assert "successfully reset" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_confirm_invalid_token(self, test_client):
        """Test password reset confirmation with invalid token."""
        response = await test_client.post(
            "/api/v1/auth/password-reset-confirm",
            json={
                "token": "invalid_token",
                "new_password": "NewSecurePass123!"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]