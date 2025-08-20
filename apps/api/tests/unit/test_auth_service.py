"""Unit tests for authentication service."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
import jwt
import bcrypt

from src.services.auth_service import AuthService
from src.models.user import User


@pytest.fixture
def auth_service():
    """Create an auth service instance for testing."""
    return AuthService()


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "123e4567-e89b-12d3-a456-426614174000"
    user.email = "test@example.com"
    user.role = "USER"
    user.hashed_password = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode('utf-8')
    return user


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self, auth_service):
        """Test password hashing creates valid bcrypt hash."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length
    
    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password("WrongPassword", hashed) is False
    
    def test_hash_password_different_salts(self, auth_service):
        """Test that same password generates different hashes."""
        password = "SecurePassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)
        
        assert hash1 != hash2
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True


class TestTokenGeneration:
    """Test JWT token generation and validation."""
    
    def test_create_access_token(self, auth_service):
        """Test access token creation with correct claims."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "USER"
        
        token = auth_service.create_access_token(user_id, email, role)
        
        # Decode token to verify claims
        payload = jwt.decode(
            token,
            auth_service.jwt_secret,
            algorithms=[auth_service.jwt_algorithm]
        )
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["role"] == role
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        
        # Verify expiration is 15 minutes
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        assert (exp_time - iat_time).total_seconds() == pytest.approx(900, abs=5)
    
    def test_create_refresh_token(self, auth_service):
        """Test refresh token creation with correct claims."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        token = auth_service.create_refresh_token(user_id)
        
        # Decode token to verify claims
        payload = jwt.decode(
            token,
            auth_service.jwt_secret,
            algorithms=[auth_service.jwt_algorithm]
        )
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload  # Unique token ID
        
        # Verify expiration is 7 days
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        assert (exp_time - iat_time).days == 7
    
    def test_decode_valid_token(self, auth_service):
        """Test decoding a valid token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "USER"
        
        token = auth_service.create_access_token(user_id, email, role)
        payload = auth_service.decode_token(token)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["role"] == role
    
    def test_decode_expired_token(self, auth_service):
        """Test decoding an expired token raises exception."""
        # Create token with past expiration
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "user123",
            "type": "access",
            "exp": past_time,
            "iat": past_time - timedelta(minutes=15)
        }
        
        expired_token = jwt.encode(
            payload,
            auth_service.jwt_secret,
            algorithm=auth_service.jwt_algorithm
        )
        
        with pytest.raises(Exception) as exc_info:
            auth_service.decode_token(expired_token)
        
        assert "expired" in str(exc_info.value).lower()
    
    def test_decode_invalid_token(self, auth_service):
        """Test decoding an invalid token raises exception."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception) as exc_info:
            auth_service.decode_token(invalid_token)
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_validate_access_token_valid(self, auth_service):
        """Test validating a valid access token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "USER"
        
        token = auth_service.create_access_token(user_id, email, role)
        payload = auth_service.validate_access_token(token)
        
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
    
    def test_validate_access_token_wrong_type(self, auth_service):
        """Test validating a refresh token as access token fails."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        refresh_token = auth_service.create_refresh_token(user_id)
        
        with pytest.raises(Exception) as exc_info:
            auth_service.validate_access_token(refresh_token)
        
        assert "Invalid token type" in str(exc_info.value)
    
    def test_validate_refresh_token_valid(self, auth_service):
        """Test validating a valid refresh token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        
        token = auth_service.create_refresh_token(user_id)
        payload = auth_service.validate_refresh_token(token)
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
    
    def test_validate_refresh_token_wrong_type(self, auth_service):
        """Test validating an access token as refresh token fails."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "USER"
        
        access_token = auth_service.create_access_token(user_id, email, role)
        
        with pytest.raises(Exception) as exc_info:
            auth_service.validate_refresh_token(access_token)
        
        assert "Invalid token type" in str(exc_info.value)


class TestUserAuthentication:
    """Test user authentication methods."""
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_user):
        """Test successful user authentication."""
        with patch.object(auth_service.user_repository, 'get_by_email', 
                         new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            result = await auth_service.authenticate_user("test@example.com", "password123")
            
            assert result == mock_user
            mock_get.assert_called_once_with("test@example.com")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service):
        """Test authentication with non-existent user."""
        with patch.object(auth_service.user_repository, 'get_by_email',
                         new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            result = await auth_service.authenticate_user("notfound@example.com", "password123")
            
            assert result is None
            mock_get.assert_called_once_with("notfound@example.com")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_user):
        """Test authentication with wrong password."""
        with patch.object(auth_service.user_repository, 'get_by_email',
                         new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            result = await auth_service.authenticate_user("test@example.com", "wrongpassword")
            
            assert result is None
            mock_get.assert_called_once_with("test@example.com")
    
    def test_generate_token_pair(self, auth_service, mock_user):
        """Test generating both access and refresh tokens."""
        access_token, refresh_token = auth_service.generate_token_pair(mock_user)
        
        # Verify access token
        access_payload = jwt.decode(
            access_token,
            auth_service.jwt_secret,
            algorithms=[auth_service.jwt_algorithm]
        )
        assert access_payload["sub"] == str(mock_user.id)
        assert access_payload["email"] == mock_user.email
        assert access_payload["role"] == mock_user.role
        assert access_payload["type"] == "access"
        
        # Verify refresh token
        refresh_payload = jwt.decode(
            refresh_token,
            auth_service.jwt_secret,
            algorithms=[auth_service.jwt_algorithm]
        )
        assert refresh_payload["sub"] == str(mock_user.id)
        assert refresh_payload["type"] == "refresh"