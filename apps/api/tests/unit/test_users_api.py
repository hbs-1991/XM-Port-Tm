"""
Unit tests for users API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.main import app
from src.models.user import User, SubscriptionTier


class TestUsersAPI:
    """Test cases for users API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        return User(
            id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            hashed_password="hashed_pass",
            role="USER",
            subscription_tier=SubscriptionTier.PREMIUM,
            credits_remaining=2500,
            credits_used_this_month=500,
            country="US",
            is_active=True
        )

    @pytest.fixture
    def mock_statistics(self):
        """Create mock user statistics"""
        return {
            "totalJobs": 127,
            "successRate": 95.5,
            "averageConfidence": 89.2,
            "monthlyUsage": {
                "creditsUsed": 450,
                "jobsCompleted": 28,
                "filesProcessed": 28,
                "averageProcessingTime": 4200,
                "month": "August",
                "year": 2025
            },
            "creditBalance": {
                "remaining": 2500,
                "total": 3000,
                "usedThisMonth": 500,
                "percentageUsed": 16.67,
                "subscriptionTier": "PREMIUM"
            },
            "processingStats": {
                "total_jobs": 127,
                "completed_jobs": 121,
                "failed_jobs": 6,
                "success_rate": 95.5,
                "total_products": 3420,
                "successful_matches": 3268,
                "average_confidence": 89.2
            }
        }

    def test_get_user_profile_success(self, client, mock_user):
        """Test successful user profile retrieval"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_profile') as mock_get_profile:
                mock_profile = {
                    "id": str(mock_user.id),
                    "email": "test@example.com",
                    "firstName": "Test",
                    "lastName": "User",
                    "subscriptionTier": "PREMIUM",
                    "creditsRemaining": 2500,
                    "creditsUsedThisMonth": 500,
                    "isActive": True,
                    "createdAt": "2025-01-01T00:00:00",
                    "lastLoginAt": None
                }
                mock_get_profile.return_value = mock_profile
                
                response = client.get("/api/v1/users/profile")
                
                assert response.status_code == 200
                data = response.json()
                assert data["email"] == "test@example.com"
                assert data["firstName"] == "Test"
                assert data["lastName"] == "User"
                assert data["subscriptionTier"] == "PREMIUM"
                assert data["creditsRemaining"] == 2500

    def test_get_user_profile_not_found(self, client, mock_user):
        """Test user profile retrieval when profile not found"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_profile') as mock_get_profile:
                mock_get_profile.return_value = None
                
                response = client.get("/api/v1/users/profile")
                
                assert response.status_code == 404
                assert "User profile not found" in response.json()["detail"]

    def test_get_user_profile_server_error(self, client, mock_user):
        """Test user profile retrieval server error handling"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_profile') as mock_get_profile:
                mock_get_profile.side_effect = Exception("Database error")
                
                response = client.get("/api/v1/users/profile")
                
                assert response.status_code == 500
                assert "Error fetching user profile" in response.json()["detail"]

    def test_update_user_profile_success(self, client, mock_user):
        """Test successful user profile update"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.update_user_profile') as mock_update:
                updated_profile = {
                    "id": str(mock_user.id),
                    "email": "test@example.com",
                    "firstName": "Updated",
                    "lastName": "Name",
                    "companyName": "Test Company",
                    "country": "CA",
                    "subscriptionTier": "PREMIUM",
                    "creditsRemaining": 2500,
                    "creditsUsedThisMonth": 500,
                    "isActive": True,
                    "createdAt": "2025-01-01T00:00:00",
                    "lastLoginAt": None
                }
                mock_update.return_value = updated_profile
                
                update_data = {
                    "firstName": "Updated",
                    "lastName": "Name",
                    "companyName": "Test Company",
                    "country": "CA"
                }
                
                response = client.put("/api/v1/users/profile", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["firstName"] == "Updated"
                assert data["lastName"] == "Name"
                assert data["companyName"] == "Test Company"
                assert data["country"] == "CA"
                
                # Verify service was called with correct data
                mock_update.assert_called_once()
                call_args = mock_update.call_args
                assert call_args[0][0] == mock_user.id
                assert call_args[0][1] == update_data

    def test_update_user_profile_partial_update(self, client, mock_user):
        """Test partial profile update with only some fields"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.update_user_profile') as mock_update:
                updated_profile = {
                    "id": str(mock_user.id),
                    "firstName": "Updated",
                    "lastName": "User"
                }
                mock_update.return_value = updated_profile
                
                update_data = {"firstName": "Updated"}
                
                response = client.put("/api/v1/users/profile", json=update_data)
                
                assert response.status_code == 200
                
                # Verify only non-None values were passed to service
                call_args = mock_update.call_args[0][1]
                assert "firstName" in call_args
                assert call_args["firstName"] == "Updated"
                assert "lastName" not in call_args  # Should not be present since it was None

    def test_update_user_profile_user_not_found(self, client, mock_user):
        """Test profile update when user not found"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.update_user_profile') as mock_update:
                mock_update.return_value = None
                
                update_data = {"firstName": "Updated"}
                
                response = client.put("/api/v1/users/profile", json=update_data)
                
                assert response.status_code == 404
                assert "User not found" in response.json()["detail"]

    def test_update_user_profile_server_error(self, client, mock_user):
        """Test profile update server error handling"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.update_user_profile') as mock_update:
                mock_update.side_effect = Exception("Database error")
                
                update_data = {"firstName": "Updated"}
                
                response = client.put("/api/v1/users/profile", json=update_data)
                
                assert response.status_code == 500
                assert "Error updating user profile" in response.json()["detail"]

    def test_get_user_statistics_success(self, client, mock_user, mock_statistics):
        """Test successful user statistics retrieval"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_statistics') as mock_get_stats:
                mock_get_stats.return_value = mock_statistics
                
                response = client.get("/api/v1/users/statistics")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify structure
                assert "totalJobs" in data
                assert "successRate" in data
                assert "averageConfidence" in data
                assert "monthlyUsage" in data
                assert "creditBalance" in data
                assert "processingStats" in data
                
                # Verify values
                assert data["totalJobs"] == 127
                assert data["successRate"] == 95.5
                assert data["averageConfidence"] == 89.2
                
                # Verify nested structures
                monthly_usage = data["monthlyUsage"]
                assert monthly_usage["creditsUsed"] == 450
                assert monthly_usage["jobsCompleted"] == 28
                assert monthly_usage["month"] == "August"
                assert monthly_usage["year"] == 2025
                
                credit_balance = data["creditBalance"]
                assert credit_balance["remaining"] == 2500
                assert credit_balance["total"] == 3000
                assert credit_balance["subscriptionTier"] == "PREMIUM"
                
                processing_stats = data["processingStats"]
                assert processing_stats["total_jobs"] == 127
                assert processing_stats["success_rate"] == 95.5

    def test_get_user_statistics_user_not_found(self, client, mock_user):
        """Test statistics retrieval when user not found"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_statistics') as mock_get_stats:
                mock_get_stats.side_effect = ValueError("User not found")
                
                response = client.get("/api/v1/users/statistics")
                
                assert response.status_code == 404
                assert "User not found" in response.json()["detail"]

    def test_get_user_statistics_server_error(self, client, mock_user):
        """Test statistics retrieval server error handling"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            with patch('src.api.v1.users.user_analytics_service.get_user_statistics') as mock_get_stats:
                mock_get_stats.side_effect = Exception("Database error")
                
                response = client.get("/api/v1/users/statistics")
                
                assert response.status_code == 500
                assert "Error fetching user statistics" in response.json()["detail"]

    def test_authentication_required(self, client):
        """Test that all endpoints require authentication"""
        # Test without authentication (should be handled by dependency injection)
        with patch('src.api.v1.users.get_current_user') as mock_auth:
            mock_auth.side_effect = Exception("Authentication required")
            
            # Test all endpoints
            endpoints = [
                ("GET", "/api/v1/users/profile"),
                ("PUT", "/api/v1/users/profile"),
                ("GET", "/api/v1/users/statistics")
            ]
            
            for method, endpoint in endpoints:
                response = getattr(client, method.lower())(
                    endpoint,
                    json={} if method == "PUT" else None
                )
                # The exact status code depends on how authentication is handled
                # but it should not be 200
                assert response.status_code != 200

    def test_profile_update_request_validation(self, client, mock_user):
        """Test profile update request validation"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            # Test with invalid JSON structure
            response = client.put("/api/v1/users/profile", json="invalid")
            assert response.status_code == 422

    def test_response_models_structure(self, client, mock_user):
        """Test that responses match expected Pydantic models"""
        with patch('src.api.v1.users.get_current_user', return_value=mock_user):
            # Test profile response structure
            with patch('src.api.v1.users.user_analytics_service.get_user_profile') as mock_get_profile:
                mock_profile = {
                    "id": str(mock_user.id),
                    "email": "test@example.com",
                    "firstName": "Test",
                    "lastName": "User",
                    "companyName": None,
                    "country": "US",
                    "subscriptionTier": "PREMIUM",
                    "creditsRemaining": 2500,
                    "creditsUsedThisMonth": 500,
                    "isActive": True,
                    "createdAt": "2025-01-01T00:00:00",
                    "lastLoginAt": None
                }
                mock_get_profile.return_value = mock_profile
                
                response = client.get("/api/v1/users/profile")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify all required fields are present
                required_fields = [
                    "id", "email", "firstName", "lastName", "country",
                    "subscriptionTier", "creditsRemaining", "creditsUsedThisMonth",
                    "isActive", "createdAt"
                ]
                for field in required_fields:
                    assert field in data, f"Missing required field: {field}"