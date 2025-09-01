"""
Unit tests for user analytics service
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.services.user_analytics import UserAnalyticsService
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus


class TestUserAnalyticsService:
    """Test cases for UserAnalyticsService"""

    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance"""
        return UserAnalyticsService()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = User(
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
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        return user

    @pytest.fixture
    def mock_processing_jobs(self):
        """Create mock processing jobs"""
        base_job = {
            'user_id': uuid4(),
            'status': ProcessingStatus.COMPLETED,
            'input_file_name': 'test.xlsx',
            'input_file_url': 'https://s3.example.com/test.xlsx',
            'input_file_size': 1024,
            'credits_used': 15,
            'total_products': 100,
            'successful_matches': 95,
            'average_confidence': 0.89,
            'country_schema': 'US',
            'created_at': datetime.now(timezone.utc),
            'processing_time_ms': 4500
        }
        return [base_job] * 10

    @pytest.mark.asyncio
    async def test_get_user_statistics_success(self, analytics_service, mock_user):
        """Test successful retrieval of user statistics"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            
            # Mock user retrieval
            mock_session.get.return_value = mock_user
            
            # Mock query results for statistics
            mock_session.execute = AsyncMock()
            
            # Mock total jobs query
            mock_session.execute.side_effect = [
                # Total jobs
                MagicMock(scalar=MagicMock(return_value=127)),
                # Completed jobs  
                MagicMock(scalar=MagicMock(return_value=121)),
                # Failed jobs
                MagicMock(scalar=MagicMock(return_value=6)),
                # Products query (returns tuple)
                MagicMock(first=MagicMock(return_value=[3420, 3268])),
                # Average confidence
                MagicMock(scalar=MagicMock(return_value=0.892)),
                # Monthly credits
                MagicMock(scalar=MagicMock(return_value=450)),
                # Monthly jobs
                MagicMock(scalar=MagicMock(return_value=28)),
                # Monthly processing time
                MagicMock(scalar=MagicMock(return_value=4200))
            ]
            
            result = await analytics_service.get_user_statistics(mock_user.id)
            
            # Verify result structure
            assert "totalJobs" in result
            assert "successRate" in result
            assert "averageConfidence" in result
            assert "monthlyUsage" in result
            assert "creditBalance" in result
            assert "processingStats" in result
            
            # Verify calculated values
            assert result["totalJobs"] == 127
            assert result["successRate"] == pytest.approx(95.28, rel=1e-2)  # 121/127 * 100
            assert result["averageConfidence"] == pytest.approx(89.2, rel=1e-2)  # 0.892 * 100
            
            # Verify monthly usage
            monthly_usage = result["monthlyUsage"]
            assert monthly_usage["creditsUsed"] == 450
            assert monthly_usage["jobsCompleted"] == 28
            assert monthly_usage["averageProcessingTime"] == 4200
            assert monthly_usage["month"] in ["January", "February", "March", "April", "May", "June",
                                             "July", "August", "September", "October", "November", "December"]
            
            # Verify credit balance
            credit_balance = result["creditBalance"]
            assert credit_balance["remaining"] == 2500
            assert credit_balance["usedThisMonth"] == 500
            assert credit_balance["subscriptionTier"] == "PREMIUM"

    @pytest.mark.asyncio
    async def test_get_user_statistics_user_not_found(self, analytics_service):
        """Test error when user is not found"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # User not found
            
            with pytest.raises(ValueError, match="User not found"):
                await analytics_service.get_user_statistics(uuid4())

    @pytest.mark.asyncio
    async def test_calculate_processing_stats_zero_jobs(self, analytics_service):
        """Test processing stats calculation with zero jobs"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            
            # Mock all queries to return zero
            mock_session.execute = AsyncMock()
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # total_jobs
                MagicMock(scalar=MagicMock(return_value=0)),  # completed_jobs
                MagicMock(scalar=MagicMock(return_value=0)),  # failed_jobs
                MagicMock(first=MagicMock(return_value=[0, 0])),  # products
                MagicMock(scalar=MagicMock(return_value=None))  # confidence
            ]
            
            result = await analytics_service._calculate_processing_stats(mock_session, uuid4())
            
            assert result["total_jobs"] == 0
            assert result["completed_jobs"] == 0
            assert result["failed_jobs"] == 0
            assert result["success_rate"] == 0.0
            assert result["total_products"] == 0
            assert result["successful_matches"] == 0
            assert result["average_confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_monthly_usage(self, analytics_service):
        """Test monthly usage calculation"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            
            mock_session.execute = AsyncMock()
            mock_session.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=450)),  # credits_used
                MagicMock(scalar=MagicMock(return_value=28)),   # jobs_completed
                MagicMock(scalar=MagicMock(return_value=4200))  # avg_processing_time
            ]
            
            result = await analytics_service._calculate_monthly_usage(
                mock_session, uuid4(), 8, 2025
            )
            
            assert result["creditsUsed"] == 450
            assert result["jobsCompleted"] == 28
            assert result["filesProcessed"] == 28  # Same as jobs for now
            assert result["averageProcessingTime"] == 4200
            assert result["month"] == "August"
            assert result["year"] == 2025

    def test_calculate_credit_balance(self, analytics_service, mock_user):
        """Test credit balance calculation"""
        result = analytics_service._calculate_credit_balance(mock_user)
        
        expected_total = 2500 + 500  # remaining + used this month
        expected_percentage = (500 / expected_total) * 100
        
        assert result["remaining"] == 2500
        assert result["total"] == expected_total
        assert result["usedThisMonth"] == 500
        assert result["percentageUsed"] == pytest.approx(expected_percentage, rel=1e-2)
        assert result["subscriptionTier"] == "PREMIUM"

    def test_calculate_credit_balance_zero_total(self, analytics_service):
        """Test credit balance calculation with zero total credits"""
        user = User(
            credits_remaining=0,
            credits_used_this_month=0,
            subscription_tier=SubscriptionTier.FREE
        )
        
        result = analytics_service._calculate_credit_balance(user)
        
        assert result["remaining"] == 0
        assert result["total"] == 0
        assert result["percentageUsed"] == 0

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, analytics_service, mock_user):
        """Test successful user profile retrieval"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_user
            
            result = await analytics_service.get_user_profile(mock_user.id)
            
            assert result is not None
            assert result["email"] == "test@example.com"
            assert result["firstName"] == "Test"
            assert result["lastName"] == "User"
            assert result["subscriptionTier"] == "PREMIUM"
            assert result["creditsRemaining"] == 2500
            assert result["isActive"] is True

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, analytics_service):
        """Test user profile retrieval when user not found"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None
            
            result = await analytics_service.get_user_profile(uuid4())
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, analytics_service, mock_user):
        """Test successful user profile update"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_user
            
            # Mock the get_user_profile call that happens after update
            with patch.object(analytics_service, 'get_user_profile') as mock_get_profile:
                mock_get_profile.return_value = {"id": str(mock_user.id), "firstName": "Updated"}
                
                update_data = {
                    "firstName": "Updated",
                    "lastName": "Name",
                    "companyName": "Test Company"
                }
                
                result = await analytics_service.update_user_profile(mock_user.id, update_data)
                
                # Verify user was updated
                assert mock_user.first_name == "Updated"
                assert mock_user.last_name == "Name"
                assert mock_user.company_name == "Test Company"
                
                # Verify session operations
                mock_session.commit.assert_called_once()
                mock_session.refresh.assert_called_once_with(mock_user)
                
                assert result["firstName"] == "Updated"

    @pytest.mark.asyncio
    async def test_update_user_profile_user_not_found(self, analytics_service):
        """Test user profile update when user not found"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None
            
            result = await analytics_service.update_user_profile(uuid4(), {})
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_user_profile_ignores_invalid_fields(self, analytics_service, mock_user):
        """Test that profile update ignores invalid fields"""
        with patch('src.services.user_analytics.get_db') as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = mock_user
            
            with patch.object(analytics_service, 'get_user_profile') as mock_get_profile:
                mock_get_profile.return_value = {"id": str(mock_user.id)}
                
                # Include invalid fields that should be ignored
                update_data = {
                    "firstName": "Updated",
                    "email": "hacker@evil.com",  # Should be ignored
                    "credits": 999999,  # Should be ignored
                    "invalidField": "value"  # Should be ignored
                }
                
                original_email = mock_user.email
                await analytics_service.update_user_profile(mock_user.id, update_data)
                
                # Valid field should be updated
                assert mock_user.first_name == "Updated"
                # Invalid fields should be ignored
                assert mock_user.email == original_email